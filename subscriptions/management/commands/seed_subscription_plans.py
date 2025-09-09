from django.core.management.base import BaseCommand
from subscriptions.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Seed subscription plans data'

    def handle(self, *args, **options):
        """Create subscription plans"""
        
        plans_data = [
            {
                'name': 'Basic Monthly',
                'plan_type': 'basic',
                'billing_period': 'monthly',
                'price': 15.00,
                'stripe_price_id': 'price_basic_monthly',  # Replace with actual Stripe price ID
                'lookup_key': 'monthly-basic',
                'is_active': True,
            },
            {
                'name': 'Basic Yearly',
                'plan_type': 'basic',
                'billing_period': 'yearly',
                'price': 150.00,
                'stripe_price_id': 'price_basic_yearly',  # Replace with actual Stripe price ID
                'lookup_key': 'yearly-basic',
                'is_active': True,
            },
            {
                'name': 'Pro Monthly',
                'plan_type': 'pro',
                'billing_period': 'monthly',
                'price': 30.00,
                'stripe_price_id': 'price_pro_monthly',  # Replace with actual Stripe price ID
                'lookup_key': 'monthly-pro',
                'is_active': True,
            },
            {
                'name': 'Pro Yearly',
                'plan_type': 'pro',
                'billing_period': 'yearly',
                'price': 300.00,
                'stripe_price_id': 'price_pro_yearly',  # Replace with actual Stripe price ID
                'lookup_key': 'yearly-pro',
                'is_active': True,
            },
        ]
        
        created_count = 0
        updated_count = 0
        
        for plan_data in plans_data:
            plan, created = SubscriptionPlan.objects.get_or_create(
                lookup_key=plan_data['lookup_key'],
                defaults=plan_data
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created plan: {plan.name}')
                )
            else:
                # Update existing plan
                for key, value in plan_data.items():
                    setattr(plan, key, value)
                plan.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated plan: {plan.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed {len(plans_data)} plans. '
                f'Created: {created_count}, Updated: {updated_count}'
            )
        )