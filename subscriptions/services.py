import stripe
from django.conf import settings
from django.contrib.auth.models import User
from .models import SubscriptionPlan, UserSubscription, SubscriptionHistory
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

# Configure Stripe
if not settings.STRIPE_SECRET_KEY or settings.STRIPE_SECRET_KEY == 'sk_test_your_secret_key_here':
    raise ValueError("STRIPE_SECRET_KEY is not configured. Please set it in your environment variables.")
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripeService:
    """Service class for Stripe operations"""
    
    @staticmethod
    def create_customer(user):
        """Create a Stripe customer for a user"""
        try:
            # Check if Stripe is properly configured
            if not settings.STRIPE_SECRET_KEY or settings.STRIPE_SECRET_KEY == 'sk_test_your_secret_key_here':
                raise ValueError("STRIPE_SECRET_KEY is not configured. Please set it in your environment variables.")
            
            customer = stripe.Customer.create(
                email=user.email,
                name=f"{user.first_name} {user.last_name}".strip() or user.username,
                metadata={
                    'user_id': user.id,
                    'username': user.username,
                }
            )
            return customer
        except stripe.error.StripeError as e:
            logger.error(f"Error creating Stripe customer for user {user.id}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error creating Stripe customer for user {user.id}: {str(e)}")
            raise
    
    @staticmethod
    def create_subscription(customer_id, price_id, trial_period_days=14):
        """Create a Stripe subscription with trial period"""
        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{'price': price_id}],
                trial_period_days=trial_period_days,
                payment_behavior='default_incomplete',
                payment_settings={'save_default_payment_method': 'on_subscription'},
                expand=['latest_invoice.payment_intent'],
            )
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Error creating Stripe subscription: {str(e)}")
            raise
    
    @staticmethod
    def cancel_subscription(subscription_id):
        """Cancel a Stripe subscription"""
        try:
            subscription = stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True
            )
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Error canceling Stripe subscription {subscription_id}: {str(e)}")
            raise
    
    @staticmethod
    def update_subscription(subscription_id, new_price_id):
        """Update a Stripe subscription to a new plan"""
        try:
            subscription = stripe.Subscription.retrieve(subscription_id)
            stripe.Subscription.modify(
                subscription_id,
                items=[{
                    'id': subscription['items']['data'][0]['id'],
                    'price': new_price_id,
                }],
                proration_behavior='create_prorations',
            )
            return subscription
        except stripe.error.StripeError as e:
            logger.error(f"Error updating Stripe subscription {subscription_id}: {str(e)}")
            raise
    
    @staticmethod
    def get_subscription(subscription_id):
        """Retrieve a Stripe subscription"""
        try:
            return stripe.Subscription.retrieve(subscription_id)
        except stripe.error.StripeError as e:
            logger.error(f"Error retrieving Stripe subscription {subscription_id}: {str(e)}")
            raise


class SubscriptionService:
    """Service class for subscription management"""
    
    @staticmethod
    def create_trial_subscription(user, plan_lookup_key):
        """Create a trial subscription for a user"""
        try:
            # Get the subscription plan
            plan = SubscriptionPlan.objects.get(lookup_key=plan_lookup_key, is_active=True)
            
            # Check if user already has a subscription
            if hasattr(user, 'subscription'):
                raise ValueError("User already has a subscription")
            
            # Create Stripe customer if not exists
            customer_id = None
            if not user.subscription or not user.subscription.stripe_customer_id:
                customer = StripeService.create_customer(user)
                customer_id = customer.id
            
            # Create Stripe subscription with trial
            subscription = StripeService.create_subscription(
                customer_id or user.subscription.stripe_customer_id,
                plan.stripe_price_id,
                trial_period_days=14
            )
            
            # Create UserSubscription
            user_subscription = UserSubscription.objects.create(
                user=user,
                plan=plan,
                status='trial',
                stripe_subscription_id=subscription.id,
                stripe_customer_id=customer_id or user.subscription.stripe_customer_id,
                current_period_start=datetime.fromtimestamp(subscription.current_period_start),
                current_period_end=datetime.fromtimestamp(subscription.current_period_end),
            )
            
            # Log the event
            SubscriptionHistory.objects.create(
                subscription=user_subscription,
                event_type='trial_started',
                description=f"Started {plan.name} trial",
                metadata={'stripe_subscription_id': subscription.id}
            )
            
            return user_subscription
            
        except Exception as e:
            logger.error(f"Error creating trial subscription for user {user.id}: {str(e)}")
            raise
    
    @staticmethod
    def activate_subscription(user_subscription):
        """Activate a subscription after trial ends"""
        try:
            user_subscription.status = 'active'
            user_subscription.save()
            
            # Log the event
            SubscriptionHistory.objects.create(
                subscription=user_subscription,
                event_type='activated',
                description=f"Subscription activated after trial",
            )
            
            return user_subscription
            
        except Exception as e:
            logger.error(f"Error activating subscription {user_subscription.id}: {str(e)}")
            raise
    
    @staticmethod
    def cancel_subscription(user_subscription):
        """Cancel a user's subscription"""
        try:
            if user_subscription.stripe_subscription_id:
                StripeService.cancel_subscription(user_subscription.stripe_subscription_id)
            
            user_subscription.status = 'canceled'
            user_subscription.canceled_at = datetime.now()
            user_subscription.save()
            
            # Log the event
            SubscriptionHistory.objects.create(
                subscription=user_subscription,
                event_type='canceled',
                description="Subscription canceled by user",
            )
            
            return user_subscription
            
        except Exception as e:
            logger.error(f"Error canceling subscription {user_subscription.id}: {str(e)}")
            raise
    
    @staticmethod
    def change_plan(user_subscription, new_plan_lookup_key):
        """Change user's subscription plan"""
        try:
            new_plan = SubscriptionPlan.objects.get(lookup_key=new_plan_lookup_key, is_active=True)
            
            if user_subscription.stripe_subscription_id:
                StripeService.update_subscription(
                    user_subscription.stripe_subscription_id,
                    new_plan.stripe_price_id
                )
            
            old_plan = user_subscription.plan
            user_subscription.plan = new_plan
            user_subscription.save()
            
            # Log the event
            SubscriptionHistory.objects.create(
                subscription=user_subscription,
                event_type='plan_changed',
                description=f"Plan changed from {old_plan.name} to {new_plan.name}",
                metadata={
                    'old_plan': old_plan.lookup_key,
                    'new_plan': new_plan.lookup_key,
                }
            )
            
            return user_subscription
            
        except Exception as e:
            logger.error(f"Error changing plan for subscription {user_subscription.id}: {str(e)}")
            raise
    
    @staticmethod
    def sync_stripe_subscription(stripe_subscription_id):
        """Sync local subscription with Stripe data"""
        try:
            stripe_subscription = StripeService.get_subscription(stripe_subscription_id)
            user_subscription = UserSubscription.objects.get(
                stripe_subscription_id=stripe_subscription_id
            )
            
            # Update subscription status based on Stripe status
            status_mapping = {
                'trialing': 'trial',
                'active': 'active',
                'past_due': 'past_due',
                'canceled': 'canceled',
                'unpaid': 'unpaid',
            }
            
            new_status = status_mapping.get(stripe_subscription.status, 'active')
            if user_subscription.status != new_status:
                user_subscription.status = new_status
                
                # Log the status change
                SubscriptionHistory.objects.create(
                    subscription=user_subscription,
                    event_type='status_changed',
                    description=f"Status changed to {new_status}",
                    metadata={'stripe_status': stripe_subscription.status}
                )
            
            # Update period dates
            user_subscription.current_period_start = datetime.fromtimestamp(
                stripe_subscription.current_period_start
            )
            user_subscription.current_period_end = datetime.fromtimestamp(
                stripe_subscription.current_period_end
            )
            
            user_subscription.save()
            
            return user_subscription
            
        except Exception as e:
            logger.error(f"Error syncing Stripe subscription {stripe_subscription_id}: {str(e)}")
            raise