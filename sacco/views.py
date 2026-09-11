from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from .models import Member, Saving, Loan, LoanRepayment, SavingsInterestPayout
from .forms import SavingForm, LoanRepaymentForm
from decimal import Decimal
from django.db.models import Sum, Q
from django.utils import timezone
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist

# Create your views here.
def home(request):
    return render(request, 'sacco/home.html')

def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            try:
                if user.is_superuser or (hasattr(user, 'member') and user.member.is_approved):
                    login(request, user)
                    if user.is_superuser:
                        return redirect('admin_dashboard')
                    return redirect('dashboard')
                else:
                    messages.error(request, 'Your account has not been approved by an administrator yet.')
            except ObjectDoesNotExist:
                messages.error(request, 'Your member profile is not set up correctly. Please contact support.')
        else:
            messages.error(request, 'Invalid credentials')
    return render(request, 'sacco/login.html')

def logout_view(request):
    logout(request)
    return redirect('home')

def register_view(request):
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        date_of_birth = request.POST.get('date_of_birth')
        staff_id = request.POST.get('staff_id')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')

        if password != password_confirm:
            messages.error(request, 'Passwords do not match')
            return redirect('register')

        try:
            user = User.objects.create_user(username=username, email=email, password=password)
            Member.objects.create(
                user=user,
                phone_number=phone_number,
                date_of_birth=date_of_birth,
                staff_id=staff_id,
                is_approved=False
            )
            messages.success(request, 'Registration successful! An administrator will review your application shortly.')
            return redirect('login')
        except Exception as e:
            messages.error(request, f'Registration failed: {e}')
            return redirect('register')

    return render(request, 'sacco/register.html')

@login_required
def dashboard_view(request):
    # Superusers should not access the member dashboard.
    if request.user.is_superuser:
        return redirect('admin_dashboard')
    
    try:
        member = request.user.member
        savings = Saving.objects.filter(member=member).order_by('-date')
        loans = Loan.objects.filter(member=member).order_by('-date_applied')
        interest_payouts = SavingsInterestPayout.objects.filter(member=member).order_by('-date')
        context = {
            'member': member,
            'savings': savings,
            'loans': loans,
            'interest_payouts': interest_payouts,
        }
        return render(request, 'sacco/dashboard.html', context)
    except ObjectDoesNotExist:
        messages.error(request, "Your member profile is not set up correctly. Please contact support.")
        logout(request)
        return redirect('login')

@login_required
def profile_view(request):
    # Superusers should not access the member profile page.
    if request.user.is_superuser:
        messages.info(request, "Superuser profile is managed via the main Django Admin panel.")
        return redirect('admin_dashboard')

    try:
        if request.method == 'POST':
            form_type = request.POST.get('form_type')
            user = request.user
            
            if form_type == 'update_details':
                user.email = request.POST.get('email')
                user.member.phone_number = request.POST.get('phone_number')
                user.save()
                user.member.save()
                messages.success(request, 'Your details have been updated successfully.')

            elif form_type == 'change_password':
                current_password = request.POST.get('current_password')
                new_password = request.POST.get('new_password')
                confirm_new_password = request.POST.get('confirm_new_password')

                if user.check_password(current_password):
                    if new_password == confirm_new_password:
                        user.set_password(new_password)
                        user.save()
                        update_session_auth_hash(request, user)  # Important!
                        messages.success(request, 'Your password has been changed successfully.')
                    else:
                        messages.error(request, 'New passwords do not match.')
                else:
                    messages.error(request, 'Incorrect current password.')
            
            return redirect('profile')

        return render(request, 'sacco/profile.html')
    except ObjectDoesNotExist:
        messages.error(request, "Your member profile is not set up correctly. Please contact support.")
        logout(request)
        return redirect('login')

@login_required
def apply_for_loan(request):
    if request.method == 'POST':
        amount = Decimal(request.POST.get('amount'))
        reason = request.POST.get('reason')
        repayment_period = int(request.POST.get('repayment_period'))
        member = request.user.member
        Loan.objects.create(
            member=member, 
            amount=amount, 
            reason=reason,
            repayment_period=repayment_period
        )
    return redirect('dashboard')

def is_superuser(user):
    return user.is_superuser

@user_passes_test(is_superuser)
def admin_dashboard_view(request):
    total_members = Member.objects.count()
    total_savings = Saving.objects.aggregate(Sum('amount'))['amount__sum'] or 0
    total_loans = Loan.objects.filter(status='approved').aggregate(Sum('amount'))['amount__sum'] or 0
    recent_savings = Saving.objects.order_by('-date')[:5]
    pending_loans = Loan.objects.filter(status='pending')
    pending_members = Member.objects.filter(is_approved=False)
    
    saving_form = SavingForm()
    repayment_form = LoanRepaymentForm()
    
    # Search functionality
    query = request.GET.get('q')
    search_results = None
    if query:
        search_results = Member.objects.filter(
            Q(user__username__icontains=query) | Q(staff_id__icontains=query)
        )

    context = {
        'total_members': total_members,
        'total_savings': total_savings,
        'total_loans': total_loans,
        'recent_savings': recent_savings,
        'pending_loans': pending_loans,
        'pending_members': pending_members,
        'saving_form': saving_form,
        'repayment_form': repayment_form,
        'search_results': search_results,
        'query': query,
    }
    return render(request, 'sacco/admin_dashboard.html', context)

@user_passes_test(is_superuser)
def user_loans_view(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    loans = Loan.objects.filter(member=member).order_by('-date_applied')
    context = {
        'member': member,
        'loans': loans,
    }
    return render(request, 'sacco/user_loans.html', context)

@user_passes_test(is_superuser)
def record_saving(request):
    if request.method == 'POST':
        form = SavingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Saving recorded successfully.')
        else:
            messages.error(request, 'Failed to record saving. Please check the form.')
    return redirect('admin_dashboard')

@user_passes_test(is_superuser)
def record_repayment(request):
    if request.method == 'POST':
        form = LoanRepaymentForm(request.POST)
        if form.is_valid():
            repayment = form.save(commit=False)
            loan = repayment.loan
            amount = form.cleaned_data['amount']

            if amount > 0 and amount <= loan.balance:
                repayment.save()
                loan.balance -= amount
                if loan.balance <= 0:
                    loan.status = 'paid'
                    loan.balance = 0
                loan.save()
                messages.success(request, 'Repayment recorded successfully.')
            else:
                messages.error(request, 'Invalid repayment amount.')
        else:
            # This part is tricky because form.errors is not easily serializable to a message
            messages.error(request, 'Failed to record repayment. Please check the form details.')
    return redirect('admin_dashboard')

@user_passes_test(is_superuser)
def approve_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    if request.method == 'POST':
        interest_rate = request.POST.get('interest_rate')
        if interest_rate and loan.status == 'pending':
            loan.interest_rate = Decimal(interest_rate)
            loan.status = 'approved'
            loan.date_approved = timezone.now()
            loan.calculate_and_set_installments()
            # The save is called inside calculate_and_set_installments
    return redirect('admin_dashboard')

@user_passes_test(is_superuser)
def reject_loan(request, loan_id):
    loan = get_object_or_404(Loan, id=loan_id)
    loan.status = 'rejected'
    loan.save()
    return redirect('admin_dashboard')

@user_passes_test(is_superuser)
def approve_member(request, member_id):
    member = get_object_or_404(Member, id=member_id)
    member.is_approved = True
    member.save()
    messages.success(request, f'Member {member.user.username} has been approved.')
    return redirect('admin_dashboard')
