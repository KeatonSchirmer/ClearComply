from backend.database.database import db
from flask_login import UserMixin
from datetime import datetime, timedelta

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    
    # Foreign key
    organization_id = db.Column(db.Integer, db.ForeignKey('organization.id'))
    
    # Relationship
    organization = db.relationship('Organization', back_populates='users', foreign_keys=[organization_id])

class Organization(db.Model):
    __tablename__ = 'organization'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False)
    org_owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=db.func.current_timestamp())
    
    # Relationships
    owner = db.relationship('User', foreign_keys=[org_owner_id])
    users = db.relationship('User', back_populates='organization', foreign_keys='User.organization_id')
    subscription = db.relationship('Subscription', back_populates='organization', uselist=False)
    
    def get_trial_days_remaining(self):
        """Get number of trial days remaining"""
        from backend.models.finance import Subscription
        subscription = Subscription.query.filter_by(organization_id=self.id).first()
        
        if subscription:
            if subscription.status == 'trial' and subscription.trial_end:
                days_left = (subscription.trial_end - datetime.utcnow()).days
                return max(0, days_left)
        
        # Default 30 day trial from creation
        trial_end = self.created_at + timedelta(days=30)
        days_left = (trial_end - datetime.utcnow()).days
        return max(0, days_left)
    
    def is_trial_expired(self):
        """Check if trial has expired"""
        return self.get_trial_days_remaining() <= 0
    
    def has_active_subscription(self):
        """Check if organization has an active subscription or is in trial"""
        from backend.models.finance import Subscription
        subscription = Subscription.query.filter_by(organization_id=self.id).first()
        if not subscription:
            return False
        return subscription.status in ['trial', 'active'] and not self.is_trial_expired()
    
    def get_subscription_status(self):
        """Get subscription status"""
        from backend.models.finance import Subscription
        subscription = Subscription.query.filter_by(organization_id=self.id).first()
        return subscription.status if subscription else 'trial'