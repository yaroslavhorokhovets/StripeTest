# Django Subscription System

A comprehensive Django-based subscription system with Stripe integration, featuring 14-day free trials and multiple subscription plans.

## Features

- **Subscription Plans**: Basic and Pro plans with monthly/yearly billing
- **Free Trials**: 14-day free trial for all plans
- **Stripe Integration**: Complete Stripe payment processing
- **Webhook Handling**: Automatic subscription status updates
- **Admin Interface**: Full Django admin integration
- **REST API**: Complete API for subscription management
- **Trial Management**: Automated trial expiration processing

## Subscription Plans

| Plan | Monthly | Yearly | Lookup Key |
|------|---------|--------|------------|
| Basic | $15/month | $150/year | `monthly-basic`, `yearly-basic` |
| Pro | $30/month | $300/year | `monthly-pro`, `yearly-pro` |

## Installation

1. **Clone and setup the project**:
   ```bash
   git clone <repository-url>
   cd subscription_project
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment setup**:
   ```bash
   cp env.example .env
   # Edit .env with your actual values
   ```

4. **Database setup**:
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. **Seed subscription plans**:
   ```bash
   python manage.py seed_subscription_plans
   ```

## Configuration

### Stripe Setup

1. Create a Stripe account and get your API keys
2. Create products and prices in Stripe dashboard
3. Update the `stripe_price_id` values in the seeded plans
4. Set up webhook endpoint: `https://yourdomain.com/api/subscriptions/webhook/`
5. Configure webhook events:
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
   - `invoice.payment_succeeded`
   - `invoice.payment_failed`

### Environment Variables

Required environment variables in `.env`:

```env
SECRET_KEY=your-django-secret-key
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
```

## API Endpoints

### Subscription Plans
- `GET /api/subscriptions/plans/` - List all active plans

### User Subscription Management
- `GET /api/subscriptions/my-subscription/` - Get current subscription
- `POST /api/subscriptions/create/` - Create new subscription
- `POST /api/subscriptions/cancel/` - Cancel subscription
- `POST /api/subscriptions/change-plan/` - Change subscription plan
- `GET /api/subscriptions/history/` - Get subscription history

### Stripe Checkout
- `POST /api/subscriptions/checkout/` - Create Stripe checkout session

### Webhooks
- `POST /api/subscriptions/webhook/` - Stripe webhook endpoint

## Usage Examples

### Create a Subscription
```python
# POST /api/subscriptions/create/
{
    "plan_lookup_key": "monthly-basic"
}
```

### Change Plan
```python
# POST /api/subscriptions/change-plan/
{
    "new_plan_lookup_key": "yearly-pro"
}
```

### Create Checkout Session
```python
# POST /api/subscriptions/checkout/
{
    "plan_lookup_key": "monthly-pro"
}
```

## Management Commands

### Seed Subscription Plans
```bash
python manage.py seed_subscription_plans
```

### Process Trial Expirations
```bash
# Process expired trials
python manage.py process_trial_expirations

# Dry run (see what would be processed)
python manage.py process_trial_expirations --dry-run
```

## Models

### SubscriptionPlan
- Defines available subscription plans
- Links to Stripe price IDs
- Supports monthly/yearly billing

### UserSubscription
- One-to-one relationship with User
- Tracks subscription status and trial information
- Links to Stripe subscription and customer IDs

### SubscriptionHistory
- Audit trail of subscription events
- Tracks all changes and important events

### StripeWebhookEvent
- Stores webhook events for debugging
- Prevents duplicate processing

## Trial Logic

- All subscriptions start with a 14-day free trial
- Trial status is automatically managed
- Trial expiration is processed via management command
- Webhook events handle automatic status updates

## Security Considerations

- Webhook signature verification
- CSRF protection on forms
- Authentication required for subscription management
- Environment variables for sensitive data

## Development

### Running the Server
```bash
python manage.py runserver
```

### Admin Interface
Access at `/admin/` with superuser credentials.

### Testing
```bash
python manage.py test
```

## Production Deployment

1. Set `DEBUG=False` in production
2. Use a production database (PostgreSQL recommended)
3. Set up proper webhook endpoints
4. Configure Redis for Celery (if using background tasks)
5. Set up SSL certificates
6. Configure proper logging

## Support

For issues or questions, please refer to the Django and Stripe documentation or create an issue in the repository.