from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


class SubscriptionPlan(models.Model):
    """Model representing subscription plans"""
    
    PLAN_TYPES = [
        ('basic', 'Basic'),
        ('pro', 'Pro'),
    ]
    
    BILLING_PERIODS = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    
    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES)
    billing_period = models.CharField(max_length=20, choices=BILLING_PERIODS)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stripe_price_id = models.CharField(max_length=100, unique=True)
    lookup_key = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['plan_type', 'billing_period']
        ordering = ['plan_type', 'billing_period']
    
    def __str__(self):
        return f"{self.name} ({self.billing_period})"


class UserSubscription(models.Model):
    """Model representing user subscriptions"""
    
    STATUS_CHOICES = [
        ('trial', 'Trial'),
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('canceled', 'Canceled'),
        ('unpaid', 'Unpaid'),
        ('paused', 'Paused'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial')
    stripe_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    stripe_customer_id = models.CharField(max_length=100, blank=True, null=True)
    
    # Trial management
    trial_start_date = models.DateTimeField(auto_now_add=True)
    trial_end_date = models.DateTimeField()
    
    # Subscription dates
    current_period_start = models.DateTimeField(blank=True, null=True)
    current_period_end = models.DateTimeField(blank=True, null=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    canceled_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"
    
    def save(self, *args, **kwargs):
        if not self.trial_end_date:
            self.trial_end_date = self.trial_start_date + timedelta(days=14)
        super().save(*args, **kwargs)
    
    @property
    def is_trial_active(self):
        """Check if the trial period is still active"""
        return self.status == 'trial' and timezone.now() < self.trial_end_date
    
    @property
    def is_subscription_active(self):
        """Check if the subscription is active (trial or paid)"""
        return self.status in ['trial', 'active'] and (
            self.is_trial_active or 
            (self.current_period_end and timezone.now() < self.current_period_end)
        )
    
    @property
    def days_remaining_in_trial(self):
        """Get remaining days in trial"""
        if not self.is_trial_active:
            return 0
        remaining = self.trial_end_date - timezone.now()
        return max(0, remaining.days)


class SubscriptionHistory(models.Model):
    """Model to track subscription changes and events"""
    
    EVENT_TYPES = [
        ('created', 'Created'),
        ('trial_started', 'Trial Started'),
        ('trial_ended', 'Trial Ended'),
        ('trial_will_end', 'Trial Will End'),
        ('activated', 'Activated'),
        ('renewed', 'Renewed'),
        ('canceled', 'Canceled'),
        ('paused', 'Paused'),
        ('payment_failed', 'Payment Failed'),
        ('plan_changed', 'Plan Changed'),
        ('status_changed', 'Status Changed'),
        ('checkout_completed', 'Checkout Completed'),
        ('customer_deleted', 'Customer Deleted'),
        ('invoice_created', 'Invoice Created'),
        ('invoice_paid', 'Invoice Paid'),
        ('payment_method_attached', 'Payment Method Attached'),
    ]
    
    subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE, related_name='history')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.subscription.user.username} - {self.event_type}"


class StripeWebhookEvent(models.Model):
    """Model to track Stripe webhook events"""
    
    stripe_event_id = models.CharField(max_length=100, unique=True)
    event_type = models.CharField(max_length=100)
    processed = models.BooleanField(default=False)
    data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.event_type} - {self.stripe_event_id}"