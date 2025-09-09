from django.urls import path
from . import views

urlpatterns = [
    # Subscription plans
    path('plans/', views.SubscriptionPlanListView.as_view(), name='subscription-plans'),
    
    # User subscription management
    path('my-subscription/', views.UserSubscriptionView.as_view(), name='my-subscription'),
    path('history/', views.SubscriptionHistoryView.as_view(), name='subscription-history'),
    path('create/', views.create_subscription, name='create-subscription'),
    path('cancel/', views.cancel_subscription, name='cancel-subscription'),
    path('change-plan/', views.change_plan, name='change-plan'),
    
    # User profile
    path('profile/', views.user_profile, name='user-profile'),
    
    # Stripe checkout
    path('checkout/', views.create_checkout_session, name='create-checkout'),
    
    # Webhooks
    path('webhook/', views.stripe_webhook, name='stripe-webhook'),
]