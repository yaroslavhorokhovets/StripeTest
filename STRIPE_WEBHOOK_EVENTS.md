# Stripe Webhook Events Implementation

This document outlines all the Stripe webhook events that have been implemented in the Django subscription system.

## Implemented Webhook Events

### 1. Balance Events

#### `balance.available`
- **Description**: Occurs whenever your Stripe balance has been updated (e.g., when a charge is available to be paid out)
- **Handler**: `handle_balance_available()`
- **Action**: Logs balance updates for admin monitoring
- **Use Case**: Track when funds become available for payout

### 2. Checkout Events

#### `checkout.session.async_payment_failed`
- **Description**: Occurs when a payment intent using a delayed payment method fails
- **Handler**: `handle_checkout_async_payment_failed()`
- **Action**: Logs failed async payments
- **Use Case**: Handle delayed payment failures

#### `checkout.session.async_payment_succeeded`
- **Description**: Occurs when a payment intent using a delayed payment method finally succeeds
- **Handler**: `handle_checkout_async_payment_succeeded()`
- **Action**: Logs successful async payments
- **Use Case**: Handle delayed payment successes

#### `checkout.session.completed`
- **Description**: Occurs when a Checkout Session has been successfully completed
- **Handler**: `handle_checkout_session_completed()`
- **Action**: 
  - Syncs subscription data if it's a subscription checkout
  - Creates subscription history entry
- **Use Case**: Handle successful checkout completions

#### `checkout.session.expired`
- **Description**: Occurs when a Checkout Session is expired
- **Handler**: `handle_checkout_session_expired()`
- **Action**: Logs expired checkout sessions
- **Use Case**: Handle expired checkout sessions

### 3. Customer Events

#### `customer.created`
- **Description**: Occurs whenever a new customer is created
- **Handler**: `handle_customer_created()`
- **Action**: Logs customer creation
- **Use Case**: Track new customer registrations

#### `customer.deleted`
- **Description**: Occurs whenever a customer is deleted
- **Handler**: `handle_customer_deleted()`
- **Action**: 
  - Marks associated subscriptions as canceled
  - Creates subscription history entry
- **Use Case**: Handle customer account deletions

#### `customer.updated`
- **Description**: Occurs whenever any property of a customer changes
- **Handler**: `handle_customer_updated()`
- **Action**: Logs customer updates
- **Use Case**: Track customer data changes

### 4. Subscription Events

#### `customer.subscription.created`
- **Description**: Occurs whenever a customer is signed up for a new plan
- **Handler**: `handle_subscription_created()`
- **Action**: 
  - Creates or updates UserSubscription
  - Sets trial status
  - Creates subscription history entry
- **Use Case**: Handle new subscription creation

#### `customer.subscription.updated`
- **Description**: Occurs whenever a subscription changes (e.g., switching from one plan to another, or changing the status from trial to active)
- **Handler**: `handle_subscription_updated()`
- **Action**: Syncs subscription data with Stripe
- **Use Case**: Handle subscription changes

#### `customer.subscription.deleted`
- **Description**: Occurs whenever a customer's subscription ends
- **Handler**: `handle_subscription_deleted()`
- **Action**: 
  - Marks subscription as canceled
  - Creates subscription history entry
- **Use Case**: Handle subscription cancellations

#### `customer.subscription.paused`
- **Description**: Occurs whenever a customer's subscription is paused
- **Handler**: `handle_subscription_paused()`
- **Action**: 
  - Updates subscription status to 'paused'
  - Creates subscription history entry
- **Use Case**: Handle subscription pauses

#### `customer.subscription.trial_will_end`
- **Description**: Occurs three days before a subscription's trial period is scheduled to end
- **Handler**: `handle_subscription_trial_will_end()`
- **Action**: 
  - Creates subscription history entry
  - Can be extended to send trial ending notifications
- **Use Case**: Send trial ending reminders

### 5. Invoice Events

#### `invoice.created`
- **Description**: Occurs whenever a new invoice is created
- **Handler**: `handle_invoice_created()`
- **Action**: 
  - Logs invoice creation
  - Creates subscription history entry if for a subscription
- **Use Case**: Track invoice generation

#### `invoice.paid`
- **Description**: Occurs when an invoice is successfully paid
- **Handler**: `handle_invoice_paid()`
- **Action**: 
  - Updates subscription status to 'active' if it was 'past_due'
  - Creates subscription history entry
- **Use Case**: Handle successful invoice payments

#### `invoice.payment_succeeded`
- **Description**: Occurs whenever an invoice payment attempt succeeds
- **Handler**: `handle_payment_succeeded()`
- **Action**: 
  - Activates subscription if it was in trial
  - Creates renewal history entry
- **Use Case**: Handle successful payments

#### `invoice.payment_failed`
- **Description**: Occurs whenever an invoice payment attempt fails
- **Handler**: `handle_payment_failed()`
- **Action**: 
  - Updates subscription status to 'past_due'
  - Creates subscription history entry
- **Use Case**: Handle failed payments

### 6. Invoice Payment Events

#### `invoice_payment.paid`
- **Description**: Occurs when an InvoicePayment is successfully paid
- **Handler**: `handle_invoice_payment_paid()`
- **Action**: Logs detailed payment information
- **Use Case**: Handle detailed payment confirmations

### 7. Payment Method Events

#### `payment_method.attached`
- **Description**: Occurs whenever a new payment method is attached to a customer
- **Handler**: `handle_payment_method_attached()`
- **Action**: 
  - Logs payment method attachment
  - Creates subscription history entry
- **Use Case**: Track payment method additions

## Webhook Security

- All webhooks are verified using Stripe's signature verification
- Duplicate event processing is prevented by checking `StripeWebhookEvent` model
- Comprehensive error handling and logging for debugging

## Database Changes

### New SubscriptionHistory Event Types
- `trial_will_end`: Trial Will End
- `paused`: Paused
- `status_changed`: Status Changed
- `checkout_completed`: Checkout Completed
- `customer_deleted`: Customer Deleted
- `invoice_created`: Invoice Created
- `invoice_paid`: Invoice Paid
- `payment_method_attached`: Payment Method Attached

### New UserSubscription Status
- `paused`: Paused subscription status

## Usage

To use these webhook handlers:

1. Configure your Stripe webhook endpoint to point to: `https://yourdomain.com/api/subscriptions/webhook/`
2. Select the events you want to receive in your Stripe dashboard
3. The system will automatically process and log all received events
4. Check the `StripeWebhookEvent` model for processing status
5. Check the `SubscriptionHistory` model for subscription-related events

## Error Handling

- All webhook handlers include comprehensive error handling
- Failed events are logged with detailed error messages
- Webhook events are marked as processed only after successful handling
- Unhandled event types are logged for monitoring

## Logging

Enhanced logging includes:
- Webhook signature verification status
- Event processing success/failure
- Detailed error messages for debugging
- Event ID and type tracking