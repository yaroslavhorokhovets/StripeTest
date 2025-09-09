#!/usr/bin/env python3
"""
Setup script to configure Stripe keys for the subscription project.
Run this script to set up your Stripe configuration.
"""

import os
import sys
from pathlib import Path

def create_env_file():
    """Create .env file with Stripe configuration"""
    env_content = """# Django Settings
SECRET_KEY=django-insecure-development-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Stripe Configuration - REPLACE WITH YOUR ACTUAL STRIPE KEYS
# Get these from: https://dashboard.stripe.com/apikeys
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here

# Database (Optional - defaults to SQLite)
# DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Redis (Optional - for Celery)
REDIS_URL=redis://localhost:6379/0
"""
    
    env_file = Path('.env')
    if env_file.exists():
        print("⚠️  .env file already exists. Backing up to .env.backup")
        env_file.rename('.env.backup')
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ Created .env file")
    print("\n📋 Next steps:")
    print("1. Go to https://dashboard.stripe.com/apikeys")
    print("2. Copy your Publishable key and replace 'pk_test_your_publishable_key_here'")
    print("3. Copy your Secret key and replace 'sk_test_your_secret_key_here'")
    print("4. Set up webhooks at https://dashboard.stripe.com/webhooks")
    print("5. Copy the webhook secret and replace 'whsec_your_webhook_secret_here'")
    print("\n🔧 After updating the keys, run:")
    print("   python manage.py migrate")
    print("   python manage.py seed_subscription_plans")
    print("   python manage.py runserver")

def check_stripe_config():
    """Check if Stripe is properly configured"""
    try:
        from django.conf import settings
        from decouple import config
        
        # Check if keys are configured
        publishable_key = config('STRIPE_PUBLISHABLE_KEY', default='')
        secret_key = config('STRIPE_SECRET_KEY', default='')
        webhook_secret = config('STRIPE_WEBHOOK_SECRET', default='')
        
        if not publishable_key or publishable_key == 'pk_test_your_publishable_key_here':
            print("❌ STRIPE_PUBLISHABLE_KEY is not configured")
            return False
        
        if not secret_key or secret_key == 'sk_test_your_secret_key_here':
            print("❌ STRIPE_SECRET_KEY is not configured")
            return False
        
        if not webhook_secret or webhook_secret == 'whsec_your_webhook_secret_here':
            print("⚠️  STRIPE_WEBHOOK_SECRET is not configured (optional for testing)")
        
        print("✅ Stripe configuration looks good!")
        return True
        
    except Exception as e:
        print(f"❌ Error checking Stripe configuration: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Stripe Setup Script")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        check_stripe_config()
    else:
        create_env_file()