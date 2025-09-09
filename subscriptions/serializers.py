from rest_framework import serializers
from django.contrib.auth.models import User
from .models import SubscriptionPlan, UserSubscription, SubscriptionHistory


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """Serializer for subscription plans"""
    
    class Meta:
        model = SubscriptionPlan
        fields = [
            'id', 'name', 'plan_type', 'billing_period', 'price', 
            'lookup_key', 'is_active', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class UserSubscriptionSerializer(serializers.ModelSerializer):
    """Serializer for user subscriptions"""
    plan = SubscriptionPlanSerializer(read_only=True)
    plan_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = UserSubscription
        fields = [
            'id', 'plan', 'plan_id', 'status', 'trial_start_date', 'trial_end_date',
            'current_period_start', 'current_period_end', 'is_trial_active',
            'is_subscription_active', 'days_remaining_in_trial', 'created_at',
            'canceled_at'
        ]
        read_only_fields = [
            'id', 'status', 'trial_start_date', 'trial_end_date',
            'current_period_start', 'current_period_end', 'is_trial_active',
            'is_subscription_active', 'days_remaining_in_trial', 'created_at',
            'canceled_at'
        ]


class SubscriptionHistorySerializer(serializers.ModelSerializer):
    """Serializer for subscription history"""
    
    class Meta:
        model = SubscriptionHistory
        fields = [
            'id', 'event_type', 'description', 'metadata', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class CreateSubscriptionSerializer(serializers.Serializer):
    """Serializer for creating a new subscription"""
    plan_lookup_key = serializers.CharField(max_length=100)
    
    def validate_plan_lookup_key(self, value):
        """Validate that the plan exists and is active"""
        try:
            plan = SubscriptionPlan.objects.get(lookup_key=value, is_active=True)
            return value
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive plan")


class ChangePlanSerializer(serializers.Serializer):
    """Serializer for changing subscription plan"""
    new_plan_lookup_key = serializers.CharField(max_length=100)
    
    def validate_new_plan_lookup_key(self, value):
        """Validate that the new plan exists and is active"""
        try:
            plan = SubscriptionPlan.objects.get(lookup_key=value, is_active=True)
            return value
        except SubscriptionPlan.DoesNotExist:
            raise serializers.ValidationError("Invalid or inactive plan")


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user information"""
    subscription = UserSubscriptionSerializer(read_only=True)
    
    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 
            'date_joined', 'subscription'
        ]
        read_only_fields = ['id', 'date_joined']