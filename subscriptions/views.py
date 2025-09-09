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
    
    logger.info(f"Received Stripe webhook with signature: {sig_header[:20]}...")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        logger.info(f"Successfully verified webhook event: {event['type']} (ID: {event['id']})")
    except ValueError as e:
        logger.error(f"Invalid payload in webhook: {str(e)}")
        return JsonResponse({'error': 'Invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature in webhook: {str(e)}")
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
        logger.info(f"Webhook event {event['id']} already processed, skipping")
        return JsonResponse({'status': 'already_processed'})
    
    # Process the event
    try:
        # Balance events
        if event['type'] == 'balance.available':
            handle_balance_available(event['data']['object'])
        
        # Checkout events
        elif event['type'] == 'checkout.session.async_payment_failed':
            handle_checkout_async_payment_failed(event['data']['object'])
        elif event['type'] == 'checkout.session.async_payment_succeeded':
            handle_checkout_async_payment_succeeded(event['data']['object'])
        elif event['type'] == 'checkout.session.completed':
            handle_checkout_session_completed(event['data']['object'])
        elif event['type'] == 'checkout.session.expired':
            handle_checkout_session_expired(event['data']['object'])
        
        # Customer events
        elif event['type'] == 'customer.created':
            handle_customer_created(event['data']['object'])
        elif event['type'] == 'customer.deleted':
            handle_customer_deleted(event['data']['object'])
        elif event['type'] == 'customer.updated':
            handle_customer_updated(event['data']['object'])
        
        # Subscription events
        elif event['type'] == 'customer.subscription.created':
            handle_subscription_created(event['data']['object'])
        elif event['type'] == 'customer.subscription.updated':
            handle_subscription_updated(event['data']['object'])
        elif event['type'] == 'customer.subscription.deleted':
            handle_subscription_deleted(event['data']['object'])
        elif event['type'] == 'customer.subscription.paused':
            handle_subscription_paused(event['data']['object'])
        elif event['type'] == 'customer.subscription.trial_will_end':
            handle_subscription_trial_will_end(event['data']['object'])
        
        # Invoice events
        elif event['type'] == 'invoice.created':
            handle_invoice_created(event['data']['object'])
        elif event['type'] == 'invoice.paid':
            handle_invoice_paid(event['data']['object'])
        elif event['type'] == 'invoice.payment_succeeded':
            handle_payment_succeeded(event['data']['object'])
        elif event['type'] == 'invoice.payment_failed':
            handle_payment_failed(event['data']['object'])
        
        # Invoice Payment events
        elif event['type'] == 'invoice_payment.paid':
            handle_invoice_payment_paid(event['data']['object'])
        
        # Payment Method events
        elif event['type'] == 'payment_method.attached':
            handle_payment_method_attached(event['data']['object'])
        
        # Log unhandled events
        else:
            logger.info(f"Unhandled webhook event type: {event['type']}")
        
        webhook_event.processed = True
        webhook_event.save()
        
        logger.info(f"Successfully processed webhook event: {event['type']} (ID: {event['id']})")
        
    except Exception as e:
        logger.error(f"Error processing webhook event {event['type']} (ID: {event['id']}): {str(e)}")
        webhook_event.processed = False
        webhook_event.save()
        return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'status': 'success', 'event_id': event['id'], 'event_type': event['type']})


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


# Balance Events
def handle_balance_available(balance):
    """Handle balance.available webhook - when Stripe balance is updated"""
    try:
        logger.info(f"Stripe balance updated: {balance['available'][0]['amount']} {balance['available'][0]['currency']}")
        # You can add custom logic here for balance notifications
        # For example, send notifications to admin users about new funds
    except Exception as e:
        logger.error(f"Error handling balance available webhook: {str(e)}")


# Checkout Events
def handle_checkout_async_payment_failed(checkout_session):
    """Handle checkout.session.async_payment_failed webhook"""
    try:
        logger.info(f"Checkout session async payment failed: {checkout_session['id']}")
        # You can add logic to notify users about failed payments
        # or update user subscription status
    except Exception as e:
        logger.error(f"Error handling checkout async payment failed webhook: {str(e)}")


def handle_checkout_async_payment_succeeded(checkout_session):
    """Handle checkout.session.async_payment_succeeded webhook"""
    try:
        logger.info(f"Checkout session async payment succeeded: {checkout_session['id']}")
        # You can add logic to notify users about successful payments
    except Exception as e:
        logger.error(f"Error handling checkout async payment succeeded webhook: {str(e)}")


def handle_checkout_session_completed(checkout_session):
    """Handle checkout.session.completed webhook"""
    try:
        logger.info(f"Checkout session completed: {checkout_session['id']}")
        
        # If this is a subscription checkout, handle it
        if checkout_session.get('mode') == 'subscription':
            subscription_id = checkout_session.get('subscription')
            if subscription_id:
                # Sync the subscription data
                SubscriptionService.sync_stripe_subscription(subscription_id)
                
                # Log the event
                try:
                    user_subscription = UserSubscription.objects.get(
                        stripe_subscription_id=subscription_id
                    )
                    SubscriptionHistory.objects.create(
                        subscription=user_subscription,
                        event_type='checkout_completed',
                        description="Checkout session completed",
                        metadata={'checkout_session_id': checkout_session['id']}
                    )
                except UserSubscription.DoesNotExist:
                    pass
                    
    except Exception as e:
        logger.error(f"Error handling checkout session completed webhook: {str(e)}")


def handle_checkout_session_expired(checkout_session):
    """Handle checkout.session.expired webhook"""
    try:
        logger.info(f"Checkout session expired: {checkout_session['id']}")
        # You can add logic to notify users about expired checkout sessions
        # or clean up any temporary data
    except Exception as e:
        logger.error(f"Error handling checkout session expired webhook: {str(e)}")


# Customer Events
def handle_customer_created(customer):
    """Handle customer.created webhook"""
    try:
        logger.info(f"Stripe customer created: {customer['id']}")
        # You can add logic to sync customer data or send welcome emails
    except Exception as e:
        logger.error(f"Error handling customer created webhook: {str(e)}")


def handle_customer_deleted(customer):
    """Handle customer.deleted webhook"""
    try:
        logger.info(f"Stripe customer deleted: {customer['id']}")
        
        # Update any local customer references
        try:
            user_subscription = UserSubscription.objects.get(
                stripe_customer_id=customer['id']
            )
            # Mark subscription as canceled if customer is deleted
            user_subscription.status = 'canceled'
            user_subscription.canceled_at = datetime.now()
            user_subscription.save()
            
            # Log the event
            SubscriptionHistory.objects.create(
                subscription=user_subscription,
                event_type='customer_deleted',
                description="Customer deleted in Stripe",
                metadata={'stripe_customer_id': customer['id']}
            )
        except UserSubscription.DoesNotExist:
            pass
            
    except Exception as e:
        logger.error(f"Error handling customer deleted webhook: {str(e)}")


def handle_customer_updated(customer):
    """Handle customer.updated webhook"""
    try:
        logger.info(f"Stripe customer updated: {customer['id']}")
        # You can add logic to sync customer data changes
    except Exception as e:
        logger.error(f"Error handling customer updated webhook: {str(e)}")


# Additional Subscription Events
def handle_subscription_paused(stripe_subscription):
    """Handle customer.subscription.paused webhook"""
    try:
        user_subscription = UserSubscription.objects.get(
            stripe_subscription_id=stripe_subscription['id']
        )
        user_subscription.status = 'paused'
        user_subscription.save()
        
        # Log the event
        SubscriptionHistory.objects.create(
            subscription=user_subscription,
            event_type='paused',
            description="Subscription paused",
            metadata={'stripe_subscription_id': stripe_subscription['id']}
        )
        
    except UserSubscription.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error handling subscription paused webhook: {str(e)}")


def handle_subscription_trial_will_end(stripe_subscription):
    """Handle customer.subscription.trial_will_end webhook"""
    try:
        user_subscription = UserSubscription.objects.get(
            stripe_subscription_id=stripe_subscription['id']
        )
        
        # Log the event
        SubscriptionHistory.objects.create(
            subscription=user_subscription,
            event_type='trial_will_end',
            description="Trial period will end soon",
            metadata={'stripe_subscription_id': stripe_subscription['id']}
        )
        
        # You can add logic here to send trial ending notifications
        # For example, send email reminders to users
        
    except UserSubscription.DoesNotExist:
        pass
    except Exception as e:
        logger.error(f"Error handling subscription trial will end webhook: {str(e)}")


# Invoice Events
def handle_invoice_created(invoice):
    """Handle invoice.created webhook"""
    try:
        logger.info(f"Invoice created: {invoice['id']}")
        
        # If this is for a subscription, log it
        subscription_id = invoice.get('subscription')
        if subscription_id:
            try:
                user_subscription = UserSubscription.objects.get(
                    stripe_subscription_id=subscription_id
                )
                SubscriptionHistory.objects.create(
                    subscription=user_subscription,
                    event_type='invoice_created',
                    description="Invoice created",
                    metadata={'invoice_id': invoice['id']}
                )
            except UserSubscription.DoesNotExist:
                pass
                
    except Exception as e:
        logger.error(f"Error handling invoice created webhook: {str(e)}")


def handle_invoice_paid(invoice):
    """Handle invoice.paid webhook"""
    try:
        logger.info(f"Invoice paid: {invoice['id']}")
        
        subscription_id = invoice.get('subscription')
        if subscription_id:
            try:
                user_subscription = UserSubscription.objects.get(
                    stripe_subscription_id=subscription_id
                )
                
                # Update subscription status to active if it was past_due
                if user_subscription.status == 'past_due':
                    user_subscription.status = 'active'
                    user_subscription.save()
                
                # Log the event
                SubscriptionHistory.objects.create(
                    subscription=user_subscription,
                    event_type='invoice_paid',
                    description="Invoice paid",
                    metadata={'invoice_id': invoice['id']}
                )
            except UserSubscription.DoesNotExist:
                pass
                
    except Exception as e:
        logger.error(f"Error handling invoice paid webhook: {str(e)}")


# Invoice Payment Events
def handle_invoice_payment_paid(invoice_payment):
    """Handle invoice_payment.paid webhook"""
    try:
        logger.info(f"Invoice payment paid: {invoice_payment['id']}")
        
        # This is similar to invoice.paid but provides more detailed payment info
        invoice_id = invoice_payment.get('invoice')
        if invoice_id:
            # You can retrieve the invoice and handle accordingly
            pass
            
    except Exception as e:
        logger.error(f"Error handling invoice payment paid webhook: {str(e)}")


# Payment Method Events
def handle_payment_method_attached(payment_method):
    """Handle payment_method.attached webhook"""
    try:
        logger.info(f"Payment method attached: {payment_method['id']}")
        
        customer_id = payment_method.get('customer')
        if customer_id:
            try:
                user_subscription = UserSubscription.objects.get(
                    stripe_customer_id=customer_id
                )
                
                # Log the event
                SubscriptionHistory.objects.create(
                    subscription=user_subscription,
                    event_type='payment_method_attached',
                    description="Payment method attached",
                    metadata={
                        'payment_method_id': payment_method['id'],
                        'payment_method_type': payment_method.get('type', 'unknown')
                    }
                )
            except UserSubscription.DoesNotExist:
                pass
                
    except Exception as e:
        logger.error(f"Error handling payment method attached webhook: {str(e)}")