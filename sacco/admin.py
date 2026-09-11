from django.contrib import admin
from .models import Member, Saving, Loan, LoanRepayment, SaccoConfiguration, SavingsInterestPayout
from django.utils import timezone

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'staff_id', 'account_balance')
    search_fields = ('user__username', 'staff_id')

@admin.register(Saving)
class SavingAdmin(admin.ModelAdmin):
    list_display = ('member', 'amount', 'date')
    autocomplete_fields = ('member',) # This creates a searchable dropdown

@admin.register(Loan)
class LoanAdmin(admin.ModelAdmin):
    list_display = ('member', 'amount', 'interest_rate', 'repayment_period', 'monthly_installment', 'balance', 'status', 'date_applied')
    list_filter = ('status',)
    search_fields = ('member__user__username', 'reason')
    autocomplete_fields = ('member',)
    actions = ['approve_loans', 'reject_loans']

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.status != 'pending':
            return self.readonly_fields + ('interest_rate',)
        return self.readonly_fields

    def approve_loans(self, request, queryset):
        for loan in queryset:
            if loan.status == 'pending':
                loan.status = 'approved'
                loan.date_approved = timezone.now()
                loan.calculate_and_set_installments()
    approve_loans.short_description = "Approve selected loans"

    def reject_loans(self, request, queryset):
        queryset.update(status='rejected')
    reject_loans.short_description = "Reject selected loans"

@admin.register(LoanRepayment)
class LoanRepaymentAdmin(admin.ModelAdmin):
    list_display = ('loan', 'amount', 'date')
    autocomplete_fields = ('loan',)

@admin.register(SavingsInterestPayout)
class SavingsInterestPayoutAdmin(admin.ModelAdmin):
    list_display = ('member', 'amount', 'date')
    readonly_fields = ('member', 'amount', 'date')

admin.site.register(SaccoConfiguration)
