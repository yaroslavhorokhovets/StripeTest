from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from subscriptions.models import UserSubscription, SubscriptionHistory
from subscriptions.services import SubscriptionService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Process trial expirations and update subscription statuses'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without making changes',
        )

    def handle(self, *args, **options):
        """Process trial expirations"""
        dry_run = options['dry_run']
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No changes will be made'))
        
        # Find subscriptions that have expired trials
        expired_trials = UserSubscription.objects.filter(
            status='trial',
            trial_end_date__lt=timezone.now()
        )
        
        self.stdout.write(f'Found {expired_trials.count()} expired trials')
        
        processed_count = 0
        error_count = 0
        
        for subscription in expired_trials:
            try:
                self.stdout.write(f'Processing subscription for user: {subscription.user.username}')
                
                if not dry_run:
                    # Check if subscription has been paid for
                    if subscription.stripe_subscription_id:
                        # Try to sync with Stripe to get latest status
                        try:
                            SubscriptionService.sync_stripe_subscription(subscription.stripe_subscription_id)
                            
                            # If still in trial status after sync, mark as canceled
                            subscription.refresh_from_db()
                            if subscription.status == 'trial':
                                subscription.status = 'canceled'
                                subscription.canceled_at = timezone.now()
                                subscription.save()
                                
                                # Log the event
                                SubscriptionHistory.objects.create(
                                    subscription=subscription,
                                    event_type='trial_ended',
                                    description="Trial period expired",
                                )
                        except Exception as e:
                            logger.error(f"Error syncing subscription {subscription.id}: {str(e)}")
                            subscription.status = 'canceled'
                            subscription.canceled_at = timezone.now()
                            subscription.save()
                    else:
                        # No Stripe subscription, just mark as canceled
                        subscription.status = 'canceled'
                        subscription.canceled_at = timezone.now()
                        subscription.save()
                        
                        # Log the event
                        SubscriptionHistory.objects.create(
                            subscription=subscription,
                            event_type='trial_ended',
                            description="Trial period expired",
                        )
                
                processed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Processed subscription for {subscription.user.username}')
                )
                
            except Exception as e:
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f'✗ Error processing subscription for {subscription.user.username}: {str(e)}')
                )
                logger.error(f"Error processing subscription {subscription.id}: {str(e)}")
        
        # Also check for subscriptions that should be activated (trial ended but payment succeeded)
        active_trials = UserSubscription.objects.filter(
            status='trial',
            trial_end_date__gte=timezone.now()
        )
        
        self.stdout.write(f'Found {active_trials.count()} active trials')
        
        for subscription in active_trials:
            if subscription.stripe_subscription_id and not dry_run:
                try:
                    SubscriptionService.sync_stripe_subscription(subscription.stripe_subscription_id)
                    subscription.refresh_from_db()
                    
                    if subscription.status == 'active':
                        self.stdout.write(
                            self.style.SUCCESS(f'✓ Activated subscription for {subscription.user.username}')
                        )
                        
                except Exception as e:
                    logger.error(f"Error syncing active trial {subscription.id}: {str(e)}")
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Processing complete. Processed: {processed_count}, Errors: {error_count}'
            )
        )