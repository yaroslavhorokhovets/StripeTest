from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json

from .models import SubscriptionPlan, UserSubscription
from .services import SubscriptionService


def home_view(request):
    """Home page view"""
    return render(request, 'home.html')


def subscription_plans_view(request):
    """Subscription plans page view"""
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('plan_type', 'billing_period')
    return render(request, 'subscriptions/plans.html', {'plans': plans})


@login_required
def dashboard_view(request):
    """User dashboard view"""
    try:
        subscription = request.user.subscription
        subscription_history = subscription.history.all()[:10]  # Last 10 events
    except UserSubscription.DoesNotExist:
        subscription = None
        subscription_history = []
    
    context = {
        'subscription': subscription,
        'subscription_history': subscription_history,
    }
    return render(request, 'subscriptions/dashboard.html', context)


def login_view(request):
    """Login view"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                next_url = request.GET.get('next', '/')
                return redirect(next_url)
            else:
                messages.error(request, 'Invalid username or password.')
        else:
            messages.error(request, 'Please fill in all fields.')
    
    return render(request, 'auth/login.html')


def register_view(request):
    """Registration view"""
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        
        # Basic validation
        if not all([username, email, password1, password2]):
            messages.error(request, 'Please fill in all fields.')
            return render(request, 'auth/register.html')
        
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return render(request, 'auth/register.html')
        
        if len(password1) < 8:
            messages.error(request, 'Password must be at least 8 characters long.')
            return render(request, 'auth/register.html')
        
        # Check if user already exists
        from django.contrib.auth.models import User
        if User.objects.filter(username=username).exists():
            messages.error(request, 'Username already exists.')
            return render(request, 'auth/register.html')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, 'Email already exists.')
            return render(request, 'auth/register.html')
        
        # Create user
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password1
            )
            login(request, user)
            messages.success(request, 'Account created successfully!')
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
    
    return render(request, 'auth/register.html')


def logout_view(request):
    """Logout view"""
    from django.contrib.auth import logout
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


def checkout_success_view(request):
    """Checkout success view"""
    return render(request, 'subscriptions/checkout_success.html')


def checkout_canceled_view(request):
    """Checkout canceled view"""
    return render(request, 'subscriptions/checkout_canceled.html')


@login_required
@require_POST
@csrf_exempt
def create_subscription_view(request):
    """Create subscription from template"""
    try:
        data = json.loads(request.body)
        plan_lookup_key = data.get('plan_lookup_key')
        
        if not plan_lookup_key:
            return JsonResponse({'error': 'Plan lookup key is required'}, status=400)
        
        # Check if user already has a subscription
        if hasattr(request.user, 'subscription'):
            return JsonResponse({'error': 'User already has a subscription'}, status=400)
        
        # Create trial subscription
        subscription = SubscriptionService.create_trial_subscription(
            request.user, 
            plan_lookup_key
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Subscription created successfully',
            'subscription_id': subscription.id
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
@csrf_exempt
def cancel_subscription_view(request):
    """Cancel subscription from template"""
    try:
        subscription = request.user.subscription
        SubscriptionService.cancel_subscription(subscription)
        
        return JsonResponse({
            'success': True,
            'message': 'Subscription canceled successfully'
        })
        
    except UserSubscription.DoesNotExist:
        return JsonResponse({'error': 'No subscription found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
@csrf_exempt
def change_plan_view(request):
    """Change subscription plan from template"""
    try:
        data = json.loads(request.body)
        new_plan_lookup_key = data.get('new_plan_lookup_key')
        
        if not new_plan_lookup_key:
            return JsonResponse({'error': 'New plan lookup key is required'}, status=400)
        
        subscription = request.user.subscription
        SubscriptionService.change_plan(subscription, new_plan_lookup_key)
        
        return JsonResponse({
            'success': True,
            'message': 'Plan changed successfully'
        })
        
    except UserSubscription.DoesNotExist:
        return JsonResponse({'error': 'No subscription found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)