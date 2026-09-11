from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db.models import Sum

# A singleton model to hold global SACCO settings
class SaccoConfiguration(models.Model):
    annual_savings_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=5.00)

    def __str__(self):
        return "SACCO Configuration"

    def save(self, *args, **kwargs):
        # Enforce that only one instance of this model can exist
        if not self.pk and SaccoConfiguration.objects.exists():
            raise ValidationError('There can be only one SaccoConfiguration instance')
        return super(SaccoConfiguration, self).save(*args, **kwargs)

class Member(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15)
    date_of_birth = models.DateField()
    staff_id = models.CharField(max_length=20, unique=True)
    account_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_approved = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

class Saving(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"{self.member.user.username} - {self.amount}"

@receiver(post_save, sender=Saving)
def update_member_balance_on_saving(sender, instance, created, **kwargs):
    if created:
        instance.member.account_balance += instance.amount
        instance.member.save()

class SavingsInterestPayout(models.Model):
    member = models.ForeignKey(Member, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Interest for {self.member.user.username} - {self.amount}"

class Loan(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('paid', 'Paid'),
    ]
    member = models.ForeignKey(Member, on_delete=models.CASCADE, related_name='loans')
    amount = models.DecimalField(max_digits=10, decimal_places=2) # Principal amount
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00) # Outstanding balance including interest
    reason = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    date_applied = models.DateField(auto_now_add=True)
    date_approved = models.DateField(null=True, blank=True)

    interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=10.00) # Annual interest rate in %
    repayment_period = models.IntegerField() # In months
    monthly_installment = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_interest = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_repayable = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    @property
    def total_paid(self):
        # Calculate the total amount paid for this loan from its repayments
        return self.repayments.aggregate(Sum('amount'))['amount__sum'] or Decimal(0)

    def __str__(self):
        return f"Loan for {self.member.user.username} of {self.amount}"

    def calculate_and_set_installments(self):
        if self.status == 'approved':
            self.total_interest = self.amount * (self.interest_rate / Decimal(100)) * (Decimal(self.repayment_period) / Decimal(12))
            self.total_repayable = self.amount + self.total_interest
            
            # Set the initial balance to the total repayable amount
            self.balance = self.total_repayable - self.total_paid
            self.monthly_installment = self.total_repayable / Decimal(self.repayment_period)
            self.save()

    def update_balance(self):
        # Recalculate balance based on total repayable and total paid
        self.balance = self.total_repayable - self.total_paid
        if self.balance <= 0:
            self.status = 'paid'
            self.balance = 0
        self.save()

class LoanRepayment(models.Model):
    loan = models.ForeignKey(Loan, on_delete=models.CASCADE, related_name='repayments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(auto_now_add=True)

    def __str__(self):
        return f"Repayment for {self.loan.id} - {self.amount}"

@receiver(post_save, sender=LoanRepayment)
def update_loan_balance_on_repayment(sender, instance, created, **kwargs):
    if created:
        instance.loan.update_balance()
