# Stripe Configuration Setup

## The Error You're Seeing

The error `'NoneType' object has no attribute 'Secret'` occurs because your Stripe secret key is not properly configured. The system is trying to access Stripe's API but can't find the secret key.

## How to Fix This

### Step 1: Create Environment File

Create a `.env` file in your project root with the following content:

```bash
# Django Settings
SECRET_KEY=django-insecure-development-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Stripe Configuration - REPLACE WITH YOUR ACTUAL STRIPE KEYS
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key_here
STRIPE_SECRET_KEY=sk_test_your_secret_key_here
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret_here

# Database (Optional - defaults to SQLite)
# DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# Redis (Optional - for Celery)
REDIS_URL=redis://localhost:6379/0
```

### Step 2: Get Your Stripe Keys

1. Go to [Stripe Dashboard](https://dashboard.stripe.com/apikeys)
2. Copy your **Publishable key** (starts with `pk_test_`)
3. Copy your **Secret key** (starts with `sk_test_`)
4. Replace the placeholder values in your `.env` file

### Step 3: Set Up Webhooks (Optional for Testing)

1. Go to [Stripe Webhooks](https://dashboard.stripe.com/webhooks)
2. Create a new webhook endpoint pointing to: `http://your-domain.com/api/subscriptions/webhook/`
3. Select these events:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`
4. Copy the webhook secret (starts with `whsec_`)
5. Replace the placeholder in your `.env` file

### Step 4: Update Your Environment File

Replace the placeholder values in your `.env` file:

```bash
STRIPE_PUBLISHABLE_KEY=pk_test_51ABC123...your_actual_key
STRIPE_SECRET_KEY=sk_test_51ABC123...your_actual_key
STRIPE_WEBHOOK_SECRET=whsec_ABC123...your_actual_secret
```

### Step 5: Run Database Migrations

```bash
python manage.py migrate
python manage.py seed_subscription_plans
```

### Step 6: Test the Application

```bash
python manage.py runserver
```

## What Was Fixed

1. **Syntax Errors**: Fixed missing parentheses and incorrect string formatting in the code
2. **Stripe Configuration**: Added proper error handling for missing Stripe keys
3. **Error Messages**: Improved error messages to be more user-friendly
4. **Setup Script**: Created a setup script to help configure Stripe keys

## The Code Issues That Were Fixed

The original code had several syntax errors:

```python
# WRONG (missing parentheses)
plan = SubscriptionPlan.objects.get
    lookup_key=serializer.validated_data'plan_lookup_key',
    is_active=True

# CORRECT
plan = SubscriptionPlan.objects.get(
    lookup_key=serializer.validated_data['plan_lookup_key'],
    is_active=True
)
```

```python
# WRONG (missing parentheses and incorrect string formatting)
customer = StripeService.create_customerrequest.user

# CORRECT
customer = StripeService.create_customer(request.user)
```

## Testing the Fix

After setting up your Stripe keys:

1. Go to `http://localhost:8000/subscriptions/plans/`
2. Click on any plan button
3. You should be redirected to Stripe checkout instead of getting an error

## Troubleshooting

If you still get errors:

1. **Check your `.env` file exists** and has the correct Stripe keys
2. **Restart your Django server** after updating the `.env` file
3. **Check the Django logs** for more specific error messages
4. **Verify your Stripe keys** are from the correct environment (test vs live)

## Security Note

- Never commit your `.env` file to version control
- Use test keys for development
- Use live keys only in production with proper security measures