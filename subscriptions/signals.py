from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import UserSubscription, SubscriptionHistory
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=UserSubscription)
def log_subscription_changes(sender, instance, created, **kwargs):
    """Log subscription changes"""
    if created:
        SubscriptionHistory.objects.create(
            subscription=instance,
            event_type='created',
            description=f"Subscription created for {instance.plan.name}",
        )
    else:
        # Check if status changed
        if hasattr(instance, '_old_status') and instance._old_status != instance.status:
            SubscriptionHistory.objects.create(
                subscription=instance,
                event_type='status_changed',
                description=f"Status changed from {instance._old_status} to {instance.status}",
                metadata={
                    'old_status': instance._old_status,
                    'new_status': instance.status,
                }
            )


@receiver(pre_save, sender=UserSubscription)
def track_status_changes(sender, instance, **kwargs):
    """Track status changes for logging"""
    if instance.pk:
        try:
            old_instance = UserSubscription.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except UserSubscription.DoesNotExist:
            instance._old_status = None
    else:
        instance._old_status = None