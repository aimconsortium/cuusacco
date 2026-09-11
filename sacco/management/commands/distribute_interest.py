from django.core.management.base import BaseCommand
from django.db import transaction
from sacco.models import Member, SaccoConfiguration, SavingsInterestPayout
from decimal import Decimal

class Command(BaseCommand):
    help = 'Calculates and distributes annual savings interest to all members'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Starting interest distribution...')

        try:
            config = SaccoConfiguration.objects.first()
            if not config:
                self.stdout.write(self.style.ERROR('SACCO configuration not found. Please set the interest rate in the admin panel.'))
                return
            
            interest_rate = config.annual_savings_interest_rate
            if interest_rate <= 0:
                self.stdout.write(self.style.WARNING('Interest rate is zero or negative. No interest will be distributed.'))
                return

            members = Member.objects.all()
            payouts_created = 0

            for member in members:
                if member.account_balance > 0:
                    interest_amount = member.account_balance * (interest_rate / Decimal(100))
                    
                    # Update member's balance
                    member.account_balance += interest_amount
                    member.save()
                    
                    # Create a record of the payout
                    SavingsInterestPayout.objects.create(member=member, amount=interest_amount)
                    payouts_created += 1
                    self.stdout.write(f'  - Paid {interest_amount:.2f} to {member.user.username}')

            self.stdout.write(self.style.SUCCESS(f'Successfully distributed interest to {payouts_created} members.'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred: {e}'))
            # The transaction will be rolled back automatically
            raise e
