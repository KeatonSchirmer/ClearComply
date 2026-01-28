import stripe
import os
from flask import url_for
from backend.models.finance import Subscription
from backend.database.database import db
from datetime import datetime

# Get and clean the Stripe key
stripe_secret = os.environ.get('STRIPE_SECRET_KEY', '').strip('"').strip("'")
stripe.api_key = stripe_secret

def create_checkout_session(organization, user_email, success_url, cancel_url):
    """
    Create a Stripe checkout session for subscription
    """
    try:
        # Check if customer already exists
        subscription = Subscription.query.filter_by(organization_id=organization.id).first()
        
        if subscription and subscription.stripe_customer_id:
            customer_id = subscription.stripe_customer_id
        else:
            # Create new Stripe customer
            customer = stripe.Customer.create(
                email=user_email,
                metadata={
                    'organization_id': organization.id,
                    'organization_name': organization.name
                }
            )
            customer_id = customer.id
            
            # Update subscription record
            if subscription:
                subscription.stripe_customer_id = customer_id
                db.session.commit()
        
        # Get price ID
        price_id = os.environ.get('STRIPE_PRICE_ID', '').strip('"').strip("'")
        
        # Create checkout session
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'organization_id': organization.id
            }
        )
        
        return session
    except Exception as e:
        print(f"Error creating checkout session: {str(e)}")
        return None

def create_customer_portal_session(customer_id, return_url):
    """
    Create a Stripe customer portal session for managing subscription
    """
    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session
    except Exception as e:
        print(f"Error creating portal session: {str(e)}")
        return None

def handle_checkout_completed(session):
    """
    Handle successful checkout completion
    """
    organization_id = session.metadata.get('organization_id')
    
    if not organization_id:
        return False
    
    subscription = Subscription.query.filter_by(organization_id=organization_id).first()
    
    if subscription:
        # Get subscription details from Stripe
        stripe_subscription = stripe.Subscription.retrieve(session.subscription)
        
        subscription.stripe_subscription_id = session.subscription
        subscription.status = 'active'
        subscription.trial_end = None
        subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)
        subscription.updated_at = datetime.utcnow()
        
        db.session.commit()
        return True
    
    return False

def handle_subscription_updated(stripe_subscription):
    """
    Handle subscription status updates
    """
    customer_id = stripe_subscription.customer
    
    subscription = Subscription.query.filter_by(stripe_customer_id=customer_id).first()
    
    if subscription:
        subscription.status = stripe_subscription.status
        subscription.current_period_end = datetime.fromtimestamp(stripe_subscription.current_period_end)
        subscription.cancel_at_period_end = stripe_subscription.cancel_at_period_end
        subscription.updated_at = datetime.utcnow()
        
        db.session.commit()
        return True
    
    return False

def handle_subscription_deleted(stripe_subscription):
    """
    Handle subscription cancellation
    """
    customer_id = stripe_subscription.customer
    
    subscription = Subscription.query.filter_by(stripe_customer_id=customer_id).first()
    
    if subscription:
        subscription.status = 'canceled'
        subscription.updated_at = datetime.utcnow()
        
        db.session.commit()
        return True
    
    return False