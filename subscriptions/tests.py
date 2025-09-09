from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from unittest.mock import patch, MagicMock
from .models import SubscriptionPlan, UserSubscription, SubscriptionHistory
from .services import SubscriptionService, StripeService


class SubscriptionPlanModelTest(TestCase):
    def setUp(self):
        self.plan = SubscriptionPlan.objects.create(
            name='Basic Monthly',
            plan_type='basic',
            billing_period='monthly',
            price=15.00,
            stripe_price_id='price_test',
            lookup_key='monthly-basic',
        )
    
    def test_plan_creation(self):
        self.assertEqual(self.plan.name, 'Basic Monthly')
        self.assertEqual(self.plan.plan_type, 'basic')
        self.assertEqual(self.plan.billing_period, 'monthly')
        self.assertEqual(self.plan.price, 15.00)
        self.assertEqual(self.plan.lookup_key, 'monthly-basic')


class UserSubscriptionModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.plan = SubscriptionPlan.objects.create(
            name='Basic Monthly',
            plan_type='basic',
            billing_period='monthly',
            price=15.00,
            stripe_price_id='price_test',
            lookup_key='monthly-basic',
        )
        self.subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            status='trial',
        )
    
    def test_subscription_creation(self):
        self.assertEqual(self.subscription.user, self.user)
        self.assertEqual(self.subscription.plan, self.plan)
        self.assertEqual(self.subscription.status, 'trial')
    
    def test_trial_end_date_auto_set(self):
        """Test that trial_end_date is automatically set to 14 days from start"""
        expected_end = self.subscription.trial_start_date + timedelta(days=14)
        self.assertEqual(self.subscription.trial_end_date, expected_end)
    
    def test_is_trial_active(self):
        """Test trial active status"""
        # Should be active initially
        self.assertTrue(self.subscription.is_trial_active)
        
        # Manually set trial end date to past
        self.subscription.trial_end_date = timezone.now() - timedelta(days=1)
        self.subscription.save()
        self.assertFalse(self.subscription.is_trial_active)
    
    def test_is_subscription_active(self):
        """Test subscription active status"""
        # Should be active during trial
        self.assertTrue(self.subscription.is_subscription_active)
        
        # Test with canceled status
        self.subscription.status = 'canceled'
        self.subscription.save()
        self.assertFalse(self.subscription.is_subscription_active)


class SubscriptionServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.plan = SubscriptionPlan.objects.create(
            name='Basic Monthly',
            plan_type='basic',
            billing_period='monthly',
            price=15.00,
            stripe_price_id='price_test',
            lookup_key='monthly-basic',
        )
    
    @patch('subscriptions.services.StripeService.create_customer')
    @patch('subscriptions.services.StripeService.create_subscription')
    def test_create_trial_subscription(self, mock_create_subscription, mock_create_customer):
        """Test creating a trial subscription"""
        # Mock Stripe responses
        mock_customer = MagicMock()
        mock_customer.id = 'cus_test123'
        mock_create_customer.return_value = mock_customer
        
        mock_subscription = MagicMock()
        mock_subscription.id = 'sub_test123'
        mock_subscription.current_period_start = 1234567890
        mock_subscription.current_period_end = 1234567890 + 30*24*60*60
        mock_create_subscription.return_value = mock_subscription
        
        # Create subscription
        subscription = SubscriptionService.create_trial_subscription(
            self.user, 'monthly-basic'
        )
        
        # Assertions
        self.assertEqual(subscription.user, self.user)
        self.assertEqual(subscription.plan, self.plan)
        self.assertEqual(subscription.status, 'trial')
        self.assertEqual(subscription.stripe_customer_id, 'cus_test123')
        self.assertEqual(subscription.stripe_subscription_id, 'sub_test123')
        
        # Check that history was created
        history = SubscriptionHistory.objects.filter(subscription=subscription)
        self.assertTrue(history.exists())
        self.assertEqual(history.first().event_type, 'trial_started')
    
    def test_create_trial_subscription_existing_user(self):
        """Test creating subscription for user who already has one"""
        # Create existing subscription
        UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            status='active',
        )
        
        # Should raise ValueError
        with self.assertRaises(ValueError):
            SubscriptionService.create_trial_subscription(self.user, 'monthly-basic')
    
    def test_cancel_subscription(self):
        """Test canceling a subscription"""
        subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            status='active',
            stripe_subscription_id='sub_test123',
        )
        
        with patch('subscriptions.services.StripeService.cancel_subscription') as mock_cancel:
            SubscriptionService.cancel_subscription(subscription)
            
            # Check subscription was canceled
            subscription.refresh_from_db()
            self.assertEqual(subscription.status, 'canceled')
            self.assertIsNotNone(subscription.canceled_at)
            
            # Check history was created
            history = SubscriptionHistory.objects.filter(subscription=subscription)
            self.assertTrue(history.exists())
            self.assertEqual(history.first().event_type, 'canceled')


class SubscriptionHistoryModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.plan = SubscriptionPlan.objects.create(
            name='Basic Monthly',
            plan_type='basic',
            billing_period='monthly',
            price=15.00,
            stripe_price_id='price_test',
            lookup_key='monthly-basic',
        )
        self.subscription = UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            status='trial',
        )
    
    def test_history_creation(self):
        """Test creating subscription history"""
        history = SubscriptionHistory.objects.create(
            subscription=self.subscription,
            event_type='created',
            description='Test event',
            metadata={'test': 'data'},
        )
        
        self.assertEqual(history.subscription, self.subscription)
        self.assertEqual(history.event_type, 'created')
        self.assertEqual(history.description, 'Test event')
        self.assertEqual(history.metadata, {'test': 'data'})