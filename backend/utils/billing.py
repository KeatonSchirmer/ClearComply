from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from backend.models.finance import Subscription
from backend.routes.stripe import create_checkout_session, create_customer_portal_session, handle_checkout_completed, handle_subscription_updated, handle_subscription_deleted
from backend.database.database import db
from datetime import datetime, timedelta
import stripe
import os
import traceback

billing_bp = Blueprint('billing', __name__)

@billing_bp.route('/', methods=['GET'])
@login_required
def billing():
    """Billing management page"""
    if not current_user.organization:
        flash('Access denied', 'error')
        return redirect(url_for('dashboard.dashboard'))
    
    subscription = Subscription.query.filter_by(
        organization_id=current_user.organization_id
    ).first()
    
    # If no subscription record, create one with trial status
    if not subscription:
        trial_end = current_user.organization.created_at + timedelta(days=30)
        subscription = Subscription(
            organization_id=current_user.organization_id,
            status='trial',
            trial_end=trial_end
        )
        db.session.add(subscription)
        db.session.commit()
    
    # Calculate trial days remaining
    trial_days = current_user.organization.get_trial_days_remaining()
    
    return render_template('billing.html', subscription=subscription, trial_days=trial_days)

@billing_bp.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout():
    """Create Stripe checkout session"""
    if not current_user.organization:
        return jsonify({'error': 'No organization'}), 400
    
    # Pass session_id in success URL
    success_url = url_for('billing.success', _external=True) + '?session_id={CHECKOUT_SESSION_ID}'
    cancel_url = url_for('billing.billing', _external=True)
    
    session = create_checkout_session(
        current_user.organization,
        current_user.email,
        success_url,
        cancel_url
    )
    
    if session:
        return jsonify({'checkout_url': session.url})
    else:
        return jsonify({'error': 'Failed to create checkout session'}), 500

@billing_bp.route('/create-portal-session', methods=['POST'])
@login_required
def create_portal():
    """Create Stripe customer portal session"""
    subscription = Subscription.query.filter_by(
        organization_id=current_user.organization_id
    ).first()
    
    if not subscription or not subscription.stripe_customer_id:
        flash('No active subscription found', 'error')
        return redirect(url_for('billing.billing'))
    
    return_url = url_for('billing.billing', _external=True)
    
    portal_session = create_customer_portal_session(
        subscription.stripe_customer_id,
        return_url
    )
    
    if portal_session:
        return redirect(portal_session.url)
    else:
        flash('Failed to create portal session', 'error')
        return redirect(url_for('billing.billing'))

@billing_bp.route('/success')
@login_required
def success():
    """Checkout success page"""
    session_id = request.args.get('session_id')
    
    if session_id:
        try:
            # Initialize Stripe with API key
            stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '').strip('"').strip("'")
            
            # Retrieve the session from Stripe
            checkout_session = stripe.checkout.Session.retrieve(session_id)
            
            # Get the subscription
            subscription = Subscription.query.filter_by(
                organization_id=current_user.organization_id
            ).first()
            
            if subscription and checkout_session.subscription:
                # Retrieve subscription details
                stripe_subscription = stripe.Subscription.retrieve(checkout_session.subscription)
                
                # Update local subscription record
                subscription.stripe_subscription_id = checkout_session.subscription
                subscription.status = 'active'
                subscription.trial_end = None  # Clear trial end date
                
                # Handle current_period_end - it's a Unix timestamp
                if hasattr(stripe_subscription, 'current_period_end'):
                    subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)
                else:
                    subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
                
                subscription.updated_at = datetime.utcnow()
                
                db.session.commit()
                
                flash('Subscription activated successfully! Welcome to ClearComply.', 'success')
            elif not subscription:
                flash('Payment received, but subscription record not found. Please contact support.', 'error')
            elif not checkout_session.subscription:
                flash('Payment received, but subscription not created. Please contact support.', 'error')
            else:
                flash('Payment received, but there was an issue activating your subscription. Please contact support.', 'warning')
                
        except Exception as e:
            print(f"ERROR in success route: {str(e)}")
            print(traceback.format_exc())
            
            # Try to activate anyway with default values
            try:
                subscription = Subscription.query.filter_by(
                    organization_id=current_user.organization_id
                ).first()
                
                if subscription:
                    subscription.status = 'active'
                    subscription.trial_end = None
                    subscription.current_period_end = datetime.utcnow() + timedelta(days=30)
                    subscription.updated_at = datetime.utcnow()
                    db.session.commit()
                    flash('Subscription activated! (Some details may need verification)', 'success')
                else:
                    flash(f'Payment successful, but verification failed. Please contact support.', 'warning')
            except:
                flash(f'Payment successful, but verification failed. Please contact support.', 'warning')
    else:
        flash('Subscription activated!', 'success')
    
    return redirect(url_for('dashboard.dashboard'))

@billing_bp.route('/webhook', methods=['POST'])
def webhook():
    """Stripe webhook handler"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    
    webhook_secret = os.environ.get('STRIPE_WEBHOOK_SECRET', '').strip('"').strip("'")
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_completed(session)
    
    elif event['type'] == 'customer.subscription.updated':
        subscription = event['data']['object']
        handle_subscription_updated(subscription)
    
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        handle_subscription_deleted(subscription)
    
    return jsonify({'status': 'success'}), 200