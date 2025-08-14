"""Payment processing and subscription management using Stripe."""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional

import stripe
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity

from app import db, User, Business, log_seo_action

logger = logging.getLogger(__name__)

# Create blueprint
payments = Blueprint('payments', __name__, url_prefix='/api/payments')

# Pricing configuration (20% below market rates)
PRICING_PLANS = {
    'starter': {
        'name': 'Starter Plan',
        'monthly_price': 6400,  # $64.00 in cents
        'yearly_price': 68800,  # $688.00 in cents (10 months price)
        'features': [
            'Basic SEO Audit',
            'Keyword Research (50 keywords)',
            'Monthly Reporting',
            'Basic Local SEO',
            'Google My Business Optimization'
        ],
        'limits': {
            'reports_per_month': 5,
            'keywords_per_research': 50,
            'businesses': 1
        }
    },
    'professional': {
        'name': 'Professional Plan',
        'monthly_price': 24000,  # $240.00 in cents
        'yearly_price': 259200,  # $2,592.00 in cents (10.8 months price)
        'features': [
            'Comprehensive SEO Audit',
            'Advanced Keyword Research (500 keywords)',
            'Weekly Reporting',
            'Local SEO + Citations',
            'Competitor Analysis',
            'Content Optimization',
            'Performance Monitoring',
            'Priority Support'
        ],
        'limits': {
            'reports_per_month': 20,
            'keywords_per_research': 500,
            'businesses': 3
        }
    },
    'enterprise': {
        'name': 'Enterprise Plan',
        'monthly_price': 48000,  # $480.00 in cents
        'yearly_price': 518400,  # $5,184.00 in cents (10.8 months price)
        'features': [
            'Full SEO Suite',
            'Unlimited Keyword Research',
            'Daily Reporting',
            'Advanced Local SEO',
            'Multi-location Management',
            'White-label Reports',
            'API Access',
            'Dedicated Account Manager',
            'Custom Integrations'
        ],
        'limits': {
            'reports_per_month': 100,
            'keywords_per_research': 'unlimited',
            'businesses': 10
        }
    }
}


def create_stripe_customer(user: User) -> str:
    """Create Stripe customer for user."""
    try:
        customer = stripe.Customer.create(
            email=user.email,
            name=f"{user.first_name} {user.last_name}",
            phone=user.phone,
            metadata={
                'user_id': user.id,
                'created_via': 'central_florida_seo'
            }
        )
        return customer.id
    except stripe.error.StripeError as e:
        logger.error(f"Failed to create Stripe customer: {e}")
        raise


def create_stripe_subscription(customer_id: str, plan_tier: str, billing_cycle: str) -> Dict:
    """Create Stripe subscription for customer."""
    try:
        # Get price based on plan and billing cycle
        plan = PRICING_PLANS.get(plan_tier)
        if not plan:
            raise ValueError(f"Invalid plan tier: {plan_tier}")
        
        price = plan['yearly_price'] if billing_cycle == 'yearly' else plan['monthly_price']
        
        # Create price object
        price_obj = stripe.Price.create(
            unit_amount=price,
            currency='usd',
            recurring={
                'interval': 'year' if billing_cycle == 'yearly' else 'month'
            },
            product_data={
                'name': f"{plan['name']} - {billing_cycle.capitalize()}",
                'metadata': {
                    'plan_tier': plan_tier,
                    'billing_cycle': billing_cycle
                }
            }
        )
        
        # Create subscription with 14-day trial
        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{'price': price_obj.id}],
            trial_period_days=14,
            metadata={
                'plan_tier': plan_tier,
                'billing_cycle': billing_cycle
            }
        )
        
        return {
            'subscription_id': subscription.id,
            'price_id': price_obj.id,
            'status': subscription.status,
            'trial_end': subscription.trial_end,
            'current_period_end': subscription.current_period_end
        }
        
    except stripe.error.StripeError as e:
        logger.error(f"Failed to create Stripe subscription: {e}")
        raise


@payments.route('/plans', methods=['GET'])
def get_pricing_plans():
    """Get available pricing plans."""
    return jsonify({
        'plans': PRICING_PLANS,
        'currency': 'USD',
        'trial_days': 14
    }), 200


@payments.route('/create-payment-intent', methods=['POST'])
@jwt_required()
def create_payment_intent():
    """Create payment intent for subscription."""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        plan_tier = data.get('plan_tier')
        billing_cycle = data.get('billing_cycle', 'monthly')
        
        if plan_tier not in PRICING_PLANS:
            return jsonify({'error': 'Invalid plan tier'}), 400
        
        if billing_cycle not in ['monthly', 'yearly']:
            return jsonify({'error': 'Invalid billing cycle'}), 400
        
        plan = PRICING_PLANS[plan_tier]
        amount = plan['yearly_price'] if billing_cycle == 'yearly' else plan['monthly_price']
        
        # Create payment intent
        intent = stripe.PaymentIntent.create(
            amount=amount,
            currency='usd',
            customer=user.stripe_customer_id if hasattr(user, 'stripe_customer_id') else None,
            metadata={
                'user_id': user.id,
                'plan_tier': plan_tier,
                'billing_cycle': billing_cycle
            }
        )
        
        return jsonify({
            'client_secret': intent.client_secret,
            'amount': amount,
            'currency': 'usd',
            'plan': {
                'tier': plan_tier,
                'name': plan['name'],
                'billing_cycle': billing_cycle,
                'features': plan['features']
            }
        }), 200
        
    except stripe.error.StripeError as e:
        logger.error(f"Payment intent creation failed: {e}")
        return jsonify({'error': 'Payment processing error'}), 500
    except Exception as e:
        logger.error(f"Payment intent creation failed: {e}")
        return jsonify({'error': 'Failed to create payment intent'}), 500


@payments.route('/subscribe', methods=['POST'])
@jwt_required()
def create_subscription():
    """Create subscription for business."""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        business_id = data.get('business_id')
        plan_tier = data.get('plan_tier')
        billing_cycle = data.get('billing_cycle', 'monthly')
        payment_method_id = data.get('payment_method_id')
        
        business = Business.query.get(business_id)
        if not business or business.user_id != current_user_id:
            return jsonify({'error': 'Business not found or access denied'}), 404
        
        if plan_tier not in PRICING_PLANS:
            return jsonify({'error': 'Invalid plan tier'}), 400
        
        # Create Stripe customer if not exists
        if not business.stripe_customer_id:
            customer_id = create_stripe_customer(user)
            business.stripe_customer_id = customer_id
        else:
            customer_id = business.stripe_customer_id
        
        # Attach payment method to customer
        if payment_method_id:
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer_id
            )
            
            # Set as default payment method
            stripe.Customer.modify(
                customer_id,
                invoice_settings={'default_payment_method': payment_method_id}
            )
        
        # Create subscription
        subscription_data = create_stripe_subscription(customer_id, plan_tier, billing_cycle)
        
        # Update business record
        business.plan_tier = plan_tier
        business.billing_cycle = billing_cycle
        business.subscription_status = 'trial'  # Starts as trial
        business.stripe_subscription_id = subscription_data['subscription_id']
        business.trial_ends_at = datetime.fromtimestamp(subscription_data['trial_end'])
        
        db.session.commit()
        
        # Log subscription creation
        log_seo_action(
            business.id,
            'subscription_created',
            f'Subscribed to {plan_tier} plan ({billing_cycle})',
            'subscription',
            new_data=json.dumps({
                'plan_tier': plan_tier,
                'billing_cycle': billing_cycle,
                'trial_ends_at': business.trial_ends_at.isoformat()
            })
        )
        
        return jsonify({
            'message': 'Subscription created successfully',
            'subscription': {
                'id': subscription_data['subscription_id'],
                'plan_tier': plan_tier,
                'billing_cycle': billing_cycle,
                'status': 'trial',
                'trial_ends_at': business.trial_ends_at.isoformat()
            }
        }), 201
        
    except stripe.error.StripeError as e:
        logger.error(f"Subscription creation failed: {e}")
        return jsonify({'error': f'Subscription error: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Subscription creation failed: {e}")
        return jsonify({'error': 'Failed to create subscription'}), 500


@payments.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhooks."""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = current_app.config.get('STRIPE_WEBHOOK_SECRET')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        logger.error("Invalid payload in Stripe webhook")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        logger.error("Invalid signature in Stripe webhook")
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    if event['type'] == 'invoice.payment_succeeded':
        handle_payment_succeeded(event['data']['object'])
    elif event['type'] == 'invoice.payment_failed':
        handle_payment_failed(event['data']['object'])
    elif event['type'] == 'customer.subscription.updated':
        handle_subscription_updated(event['data']['object'])
    elif event['type'] == 'customer.subscription.deleted':
        handle_subscription_deleted(event['data']['object'])
    else:
        logger.info(f"Unhandled Stripe event type: {event['type']}")
    
    return jsonify({'status': 'success'}), 200


def handle_payment_succeeded(invoice):
    """Handle successful payment."""
    try:
        subscription_id = invoice.get('subscription')
        if not subscription_id:
            return
        
        business = Business.query.filter_by(stripe_subscription_id=subscription_id).first()
        if not business:
            logger.error(f"Business not found for subscription {subscription_id}")
            return
        
        # Update subscription status
        business.subscription_status = 'active'
        db.session.commit()
        
        # Log payment success
        log_seo_action(
            business.id,
            'payment_succeeded',
            f'Payment succeeded for {business.plan_tier} plan',
            'payment',
            new_data=json.dumps({
                'amount': invoice.get('amount_paid'),
                'invoice_id': invoice.get('id')
            })
        )
        
        logger.info(f"Payment succeeded for business {business.id}")
        
    except Exception as e:
        logger.error(f"Error handling payment success: {e}")


def handle_payment_failed(invoice):
    """Handle failed payment."""
    try:
        subscription_id = invoice.get('subscription')
        if not subscription_id:
            return
        
        business = Business.query.filter_by(stripe_subscription_id=subscription_id).first()
        if not business:
            logger.error(f"Business not found for subscription {subscription_id}")
            return
        
        # Update subscription status
        business.subscription_status = 'past_due'
        db.session.commit()
        
        # Log payment failure
        log_seo_action(
            business.id,
            'payment_failed',
            f'Payment failed for {business.plan_tier} plan',
            'payment',
            new_data=json.dumps({
                'invoice_id': invoice.get('id'),
                'attempt_count': invoice.get('attempt_count')
            })
        )
        
        logger.warning(f"Payment failed for business {business.id}")
        
    except Exception as e:
        logger.error(f"Error handling payment failure: {e}")


def handle_subscription_updated(subscription):
    """Handle subscription updates."""
    try:
        subscription_id = subscription.get('id')
        business = Business.query.filter_by(stripe_subscription_id=subscription_id).first()
        
        if not business:
            logger.error(f"Business not found for subscription {subscription_id}")
            return
        
        # Update subscription status
        status_mapping = {
            'active': 'active',
            'past_due': 'past_due',
            'canceled': 'cancelled',
            'unpaid': 'suspended',
            'incomplete': 'incomplete',
            'trialing': 'trial'
        }
        
        new_status = status_mapping.get(subscription.get('status'), 'unknown')
        old_status = business.subscription_status
        
        business.subscription_status = new_status
        db.session.commit()
        
        # Log subscription update
        log_seo_action(
            business.id,
            'subscription_updated',
            f'Subscription status changed from {old_status} to {new_status}',
            'subscription',
            old_data=json.dumps({'status': old_status}),
            new_data=json.dumps({'status': new_status})
        )
        
        logger.info(f"Subscription updated for business {business.id}: {old_status} -> {new_status}")
        
    except Exception as e:
        logger.error(f"Error handling subscription update: {e}")


def handle_subscription_deleted(subscription):
    """Handle subscription cancellation."""
    try:
        subscription_id = subscription.get('id')
        business = Business.query.filter_by(stripe_subscription_id=subscription_id).first()
        
        if not business:
            logger.error(f"Business not found for subscription {subscription_id}")
            return
        
        # Update subscription status
        old_status = business.subscription_status
        business.subscription_status = 'cancelled'
        business.stripe_subscription_id = None
        db.session.commit()
        
        # Log subscription cancellation
        log_seo_action(
            business.id,
            'subscription_cancelled',
            f'Subscription cancelled',
            'subscription',
            old_data=json.dumps({'status': old_status, 'subscription_id': subscription_id}),
            new_data=json.dumps({'status': 'cancelled'})
        )
        
        logger.info(f"Subscription cancelled for business {business.id}")
        
    except Exception as e:
        logger.error(f"Error handling subscription deletion: {e}")


@payments.route('/subscription/<int:business_id>', methods=['GET'])
@jwt_required()
def get_subscription_status(business_id):
    """Get subscription status for business."""
    try:
        current_user_id = get_jwt_identity()
        business = Business.query.get(business_id)
        
        if not business:
            return jsonify({'error': 'Business not found'}), 404
        
        # Check permissions
        user = User.query.get(current_user_id)
        if user.role != 'admin' and business.user_id != current_user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        subscription_info = {
            'business_id': business.id,
            'plan_tier': business.plan_tier,
            'billing_cycle': business.billing_cycle,
            'subscription_status': business.subscription_status,
            'trial_ends_at': business.trial_ends_at.isoformat() if business.trial_ends_at else None,
            'plan_details': PRICING_PLANS.get(business.plan_tier, {}),
            'is_trial': business.subscription_status == 'trial',
            'is_active': business.subscription_status in ['active', 'trial']
        }
        
        # Get Stripe subscription details if available
        if business.stripe_subscription_id:
            try:
                stripe_subscription = stripe.Subscription.retrieve(business.stripe_subscription_id)
                subscription_info.update({
                    'current_period_start': stripe_subscription.current_period_start,
                    'current_period_end': stripe_subscription.current_period_end,
                    'cancel_at_period_end': stripe_subscription.cancel_at_period_end
                })
            except stripe.error.StripeError as e:
                logger.error(f"Failed to retrieve Stripe subscription: {e}")
        
        return jsonify({'subscription': subscription_info}), 200
        
    except Exception as e:
        logger.error(f"Get subscription status failed: {e}")
        return jsonify({'error': 'Failed to get subscription status'}), 500


@payments.route('/cancel-subscription/<int:business_id>', methods=['POST'])
@jwt_required()
def cancel_subscription(business_id):
    """Cancel subscription for business."""
    try:
        current_user_id = get_jwt_identity()
        business = Business.query.get(business_id)
        
        if not business:
            return jsonify({'error': 'Business not found'}), 404
        
        # Check permissions
        if business.user_id != current_user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        if not business.stripe_subscription_id:
            return jsonify({'error': 'No active subscription found'}), 400
        
        # Cancel Stripe subscription at period end
        stripe.Subscription.modify(
            business.stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        # Log cancellation request
        log_seo_action(
            business.id,
            'subscription_cancel_requested',
            f'Subscription cancellation requested for {business.plan_tier} plan',
            'subscription'
        )
        
        return jsonify({
            'message': 'Subscription will be cancelled at the end of the current billing period'
        }), 200
        
    except stripe.error.StripeError as e:
        logger.error(f"Subscription cancellation failed: {e}")
        return jsonify({'error': f'Cancellation error: {str(e)}'}), 500
    except Exception as e:
        logger.error(f"Subscription cancellation failed: {e}")
        return jsonify({'error': 'Failed to cancel subscription'}), 500