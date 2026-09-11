from django import forms
from .models import Saving, Member, Loan, LoanRepayment

class SavingForm(forms.ModelForm):
    member = forms.ModelChoiceField(
        queryset=Member.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Saving
        fields = ['member', 'amount']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
        }

class LoanRepaymentForm(forms.ModelForm):
    loan = forms.ModelChoiceField(
        queryset=Loan.objects.filter(status='approved'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = LoanRepayment
        fields = ['loan', 'amount']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
        }
