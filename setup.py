#!/usr/bin/env python3
"""
Setup script for Django Subscription Project
This script helps set up the project environment and run necessary commands.
"""

import os
import sys
import subprocess
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def main():
    """Main setup function"""
    print("🚀 Setting up Django Subscription Project...")
    
    # Check if we're in the right directory
    if not Path("manage.py").exists():
        print("❌ Error: manage.py not found. Please run this script from the project root directory.")
        sys.exit(1)
    
    # Create .env file if it doesn't exist
    if not Path(".env").exists():
        print("\n📝 Creating .env file...")
        env_content = """# Django Settings
SECRET_KEY=django-insecure-change-me-in-production-12345
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Stripe Configuration
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here

# Database (Optional - defaults to SQLite)
# DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Redis (Optional - for Celery)
REDIS_URL=redis://localhost:6379/0
"""
        with open(".env", "w") as f:
            f.write(env_content)
        print("✅ .env file created")
    else:
        print("✅ .env file already exists")
    
    # Install dependencies
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        print("❌ Failed to install dependencies. Please check your Python environment.")
        return False
    
    # Run migrations
    if not run_command("python manage.py migrate", "Running database migrations"):
        print("❌ Failed to run migrations. Please check your database configuration.")
        return False
    
    # Create superuser (optional)
    print("\n👤 Creating superuser (optional)...")
    print("You can skip this by pressing Ctrl+C")
    try:
        subprocess.run("python manage.py createsuperuser", shell=True, check=True)
        print("✅ Superuser created successfully")
    except (subprocess.CalledProcessError, KeyboardInterrupt):
        print("ℹ️ Superuser creation skipped")
    
    # Seed subscription plans
    if not run_command("python manage.py seed_subscription_plans", "Seeding subscription plans"):
        print("⚠️ Failed to seed subscription plans. You can run this manually later.")
    
    print("\n🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Update your .env file with actual Stripe keys")
    print("2. Run: python manage.py runserver")
    print("3. Visit: http://127.0.0.1:8000")
    print("\n🔧 If you encounter import errors:")
    print("- Make sure you're using the correct Python environment")
    print("- Try: pip install -r requirements.txt")
    print("- Restart your IDE/editor")

if __name__ == "__main__":
    main()