"""
URL configuration for subscription_project project.
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

from subscriptions import template_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/subscriptions/', include('subscriptions.urls')),
    
    # Template views
    path('', template_views.home_view, name='home'),
    path('subscriptions/plans/', template_views.subscription_plans_view, name='subscription-plans'),
    path('dashboard/', template_views.dashboard_view, name='dashboard'),
    
    # Authentication views
    path('login/', template_views.login_view, name='login'),
    path('register/', template_views.register_view, name='register'),
    path('logout/', template_views.logout_view, name='logout'),
    
    # Checkout views
    path('checkout/success/', template_views.checkout_success_view, name='checkout-success'),
    path('checkout/canceled/', template_views.checkout_canceled_view, name='checkout-canceled'),
    
    # Template API endpoints
    path('api/template/subscriptions/create/', template_views.create_subscription_view, name='template-create-subscription'),
    path('api/template/subscriptions/cancel/', template_views.cancel_subscription_view, name='template-cancel-subscription'),
    path('api/template/subscriptions/change-plan/', template_views.change_plan_view, name='template-change-plan'),
]

# Serve static files during development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])