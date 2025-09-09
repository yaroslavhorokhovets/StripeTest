from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
import json
import stripe
import logging
from datetime import datetime
from django.conf import settings

from .models import SubscriptionPlan, UserSubscription, SubscriptionHistory, StripeWebhookEvent
from .serializers import (
    SubscriptionPlanSerializer, UserSubscriptionSerializer, 
    SubscriptionHistorySerializer, CreateSubscriptionSerializer,
    ChangePlanSerializer, UserSerializer
)
from .services import SubscriptionService, StripeService

# Initialize logger
logger = logging.getLogger(__name__)


class SubscriptionPlanListView(generics.ListAPIView):
    """View to list all active subscription plans"""
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = []


class UserSubscriptionView(generics.RetrieveAPIView):
    """View to get user's current subscription"""
    serializer_class = UserSubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        try:
            return self.request.user.subscription
        except UserSubscription.DoesNotExist:
            return None
    
    def retrieve(self, request, *args, **kwargs):
        subscription = self.get_object()
        if subscription:
            serializer = self.get_serializer(subscription)
            return Response(serializer.data)
        else:
            return Response(
                {'message': 'No subscription found'}, 
                status=status.HTTP_404_NOT_FOUND
            )


class SubscriptionHistoryView(generics.ListAPIView):
    """View to get user's subscription history"""
    serializer_class = SubscriptionHistorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        try:
            subscription = self.request.user.subscription
            return SubscriptionHistory.objects.filter(subscription=subscription)
        except UserSubscription.DoesNotExist:
            return SubscriptionHistory.objects.none()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_subscription(request):
    """Create a new subscription with trial"""
    serializer = CreateSubscriptionSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            # Check if user already has a subscription
            if hasattr(request.user, 'subscription'):
                return Response(
                    {'error': 'User already has a subscription'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create trial subscription
            subscription = SubscriptionService.create_trial_subscription(
                request.user, 
                serializer.validated_data['plan_lookup_key']
            )
            
            response_serializer = UserSubscriptionSerializer(subscription)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    """Cancel user's subscription"""
    try:
        subscription = request.user.subscription
        SubscriptionService.cancel_subscription(subscription)
        
        serializer = UserSubscriptionSerializer(subscription)
        return Response(serializer.data)
        
    except UserSubscription.DoesNotExist:
        return Response(
            {'error': 'No subscription found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_plan(request):
    """Change user's subscription plan"""
    serializer = ChangePlanSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            subscription = request.user.subscription
            SubscriptionService.change_plan(
                subscription, 
                serializer.validated_data['new_plan_lookup_key']
            )
            
            response_serializer = UserSubscriptionSerializer(subscription)
            return Response(response_serializer.data)
            
        except UserSubscription.DoesNotExist:
            return Response(
                {'error': 'No subscription found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_profile(request):
    """Get user profile with subscription information"""
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_checkout_session(request):
    """Create Stripe checkout session for subscription"""
    serializer = CreateSubscriptionSerializer(data=request.data)
    
    if serializer.is_valid():
        try:
            plan = SubscriptionPlan.objects.get(
                lookup_key=serializer.validated_data['plan_lookup_key'],
                is_active=True
            )
            
            # Get or create Stripe customer
            customer_id = None
            if hasattr(request.user, 'subscription') and request.user.subscription.stripe_customer_id:
                customer_id = request.user.subscription.stripe_customer_id
            else:
                customer = StripeService.create_customer(request.user)
                customer_id = customer.id
            
            # Create checkout session
            checkout_session = stripe.checkout.Session.create(
                customer=customer_id,
                payment_method_types=['card'],
                line_items=[{
                    'price': plan.stripe_price_id,
                    'quantity': 1,
                }],
                mode='subscription',
                success_url=f"{request.build_absolute_uri('/checkout/success/')}",
                cancel_url=f"{request.build_absolute_uri('/checkout/canceled/')}",
                trial_period_days=settings.TRIAL_PERIOD_DAYS,
                metadata={
                    'user_id': request.user.id,
                    'plan_lookup_key': plan.lookup_key,
                }
            )
            
            return Response({
                'checkout_url': checkout_session.url,
                'session_id': checkout_session.id
            })
            
        except SubscriptionPlan.DoesNotExist:
            return Response(
                {'error': 'Invalid plan'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error creating checkout session: {str(e)}")
            # Check if it's a Stripe configuration error
            if "STRIPE_SECRET_KEY is not configured" in str(e):
                return Response(
                    {'error': 'Payment system is not configured. Please contact support.'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            return Response(
                {'error': f'Error creating checkout session: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@require_POST
def stripe_webhook(request):
    """Handle Stripe webhook events"""
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError:
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    
    # Check if we've already processed this event
    webhook_event, created = StripeWebhookEvent.objects.get_or_create(
        stripe_event_id=event['id'],
        defaults={
            'event_type': event['type'],
            'data': event['data'],
        }
    )
    
    if not created:
        return JsonResponse({'status': 'already_processed'})
    
    # Process the event
    try:
        if event['type'] == 'customer.subscription.created':
            handle_subscription_created(event['data']['object'])
        elif event['type'] == 'customer.subscription.updated':
            handle_subscription_updated(event['data']['object'])
        elif event['type'] == 'customer.subscription.deleted':
            handle_subscription_deleted(event['data']['object'])
        elif event['type'] == 'invoice.payment_succeeded':
            handle_payment_succeeded(event['data']['object'])
        elif event['type'] == 'invoice.payment_failed':
            handle_payment_failed(event['data']['object'])
        
        webhook_event.processed = True
        webhook_event.save()
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'status': 'success'})


def handle_subscription_created(stripe_subscription):
    """Handle subscription created webhook"""
    try:
        user_id = stripe_subscription['metadata'].get('user_id')
        if user_id:
            user = User.objects.get(id=user_id)
            plan_lookup_key = stripe_subscription['metadata'].get('plan_lookup_key')
            
            if plan_lookup_key:
                plan = SubscriptionPlan.objects.get(lookup_key=plan_lookup_key)
                
                # Create or update user subscription
                user_subscription, created = UserSubscription.objects.get_or_create(
                    user=user,
                    defaults={
                        'plan': plan,
                        'status': 'trial',
                        'stripe_subscription_id': stripe_subscription['id'],
                        'stripe_customer_id': stripe_subscription['customer'],
                        'current_period_start': datetime.fromtimestamp(stripe_subscription['current_period_start']),
                        'current_period_end': datetime.fromtimestamp(stripe_subscription['current_period_end']),
                    }
                )
                
                if not created:
                    # Update existing subscription
                    user_subscription.stripe_subscription_id = stripe_subscription['id']
                    user_subscription.stripe_customer_id = stripe_subscription['customer']
                    user_subscription.current_period_start = datetime.fromtimestamp(stripe_subscription['current_period_start'])
                    user_subscription.current_period_end = datetime.fromtimestamp(stripe_subscription['current_period_end'])
                    user_subscription.save()
                
                # Log the event
                SubscriptionHistory.objects.create(
                    subscription=user_subscription,
                    event_type='created',
                    description=f"Subscription created via Stripe checkout",
                    metadata={'stripe_subscription_id': stripe_subscription['id']}
                )
                
    except Exception as e:
        logger.error(f"Error handling subscription created webhook: {str(e)}")


def handle_subscription_updated(stripe_subscription):
    """Handle subscription updated webhook"""
    try:
        SubscriptionService.sync_stripe_subscription(stripe_subscription['id'])
    except Exception as e:
        logger.error(f"Error handling subscription updated webhook: {str(e)}")


def handle_subscription_deleted(stripe_subscription):
    """Handle subscription deleted webhook"""
    try:
        user_subscription = UserSubscription.objects.get(
            stripe_subscription_id=stripe_subscription['id']
        )
        user_subscription.status = 'canceled'
        user_subscription.canceled_at = datetime.now()
        user_subscription.save()
        
        # Log the event
        SubscriptionHistory.objects.create(
            subscription=user_subscription,
            event_type='canceled',
            description="Subscription canceled via Stripe",
            metadata={'stripe_subscription_id': stripe_subscription['id']}
        )
        
    except UserSubscription.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error handling subscription deleted webhook: {str(e)}")


def handle_payment_succeeded(invoice):
    """Handle successful payment webhook"""
    try:
        subscription_id = invoice['subscription']
        if subscription_id:
            user_subscription = UserSubscription.objects.get(
                stripe_subscription_id=subscription_id
            )
            
            # Update subscription status to active if it was in trial
            if user_subscription.status == 'trial':
                user_subscription.status = 'active'
                user_subscription.save()
                
                # Log the event
                SubscriptionHistory.objects.create(
                    subscription=user_subscription,
                    event_type='activated',
                    description="Subscription activated after successful payment",
                )
            
            # Log renewal
            SubscriptionHistory.objects.create(
                subscription=user_subscription,
                event_type='renewed',
                description="Subscription renewed",
                metadata={'invoice_id': invoice['id']}
            )
            
    except UserSubscription.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error handling payment succeeded webhook: {str(e)}")


def handle_payment_failed(invoice):
    """Handle failed payment webhook"""
    try:
        subscription_id = invoice['subscription']
        if subscription_id:
            user_subscription = UserSubscription.objects.get(
                stripe_subscription_id=subscription_id
            )
            user_subscription.status = 'past_due'
            user_subscription.save()
            
            # Log the event
            SubscriptionHistory.objects.create(
                subscription=user_subscription,
                event_type='payment_failed',
                description="Payment failed",
                metadata={'invoice_id': invoice['id']}
            )
            
    except UserSubscription.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error handling payment failed webhook: {str(e)}")