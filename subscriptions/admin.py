from django.contrib import admin
from .models import SubscriptionPlan, UserSubscription, SubscriptionHistory, StripeWebhookEvent


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'plan_type', 'billing_period', 'price', 'lookup_key', 'is_active']
    list_filter = ['plan_type', 'billing_period', 'is_active']
    search_fields = ['name', 'lookup_key', 'stripe_price_id']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(UserSubscription)
class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'plan', 'status', 'trial_start_date', 'trial_end_date', 
        'current_period_end', 'is_trial_active', 'is_subscription_active'
    ]
    list_filter = ['status', 'plan__plan_type', 'plan__billing_period']
    search_fields = ['user__username', 'user__email', 'stripe_subscription_id', 'stripe_customer_id']
    readonly_fields = [
        'trial_start_date', 'trial_end_date', 'created_at', 'updated_at',
        'is_trial_active', 'is_subscription_active', 'days_remaining_in_trial'
    ]
    raw_id_fields = ['user']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'plan', 'status')
        }),
        ('Stripe Information', {
            'fields': ('stripe_subscription_id', 'stripe_customer_id')
        }),
        ('Trial Information', {
            'fields': ('trial_start_date', 'trial_end_date', 'is_trial_active', 'days_remaining_in_trial')
        }),
        ('Subscription Period', {
            'fields': ('current_period_start', 'current_period_end', 'is_subscription_active')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'canceled_at')
        }),
    )


@admin.register(SubscriptionHistory)
class SubscriptionHistoryAdmin(admin.ModelAdmin):
    list_display = ['subscription', 'event_type', 'description', 'created_at']
    list_filter = ['event_type', 'created_at']
    search_fields = ['subscription__user__username', 'description']
    readonly_fields = ['created_at']
    raw_id_fields = ['subscription']


@admin.register(StripeWebhookEvent)
class StripeWebhookEventAdmin(admin.ModelAdmin):
    list_display = ['stripe_event_id', 'event_type', 'processed', 'created_at']
    list_filter = ['event_type', 'processed', 'created_at']
    search_fields = ['stripe_event_id', 'event_type']
    readonly_fields = ['created_at']