from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from backend.models.auth import User, Organization
from backend.models.finance import Subscription
from backend.database.database import db
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        organization_name = request.form.get('organization')
        
        # Check if user exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('auth.register'))
        
        # Create new user
        new_user = User(
            email=email,
            password_hash=generate_password_hash(password)
        )
        db.session.add(new_user)
        db.session.flush()  # Get the user ID
        
        # Create organization
        new_org = Organization(
            name=organization_name,
            org_owner_id=new_user.id
        )
        db.session.add(new_org)
        db.session.flush()  # Get the org ID
        
        # Link user to organization
        new_user.organization_id = new_org.id
        
        # Create trial subscription (30 days)
        trial_end = datetime.utcnow() + timedelta(days=30)
        new_subscription = Subscription(
            organization_id=new_org.id,
            status='trial',
            trial_end=trial_end
        )
        db.session.add(new_subscription)
        
        db.session.commit()
        
        flash('Registration successful! Your 30-day trial has started.', 'success')
        login_user(new_user)
        return redirect(url_for('dashboard.dashboard'))
    
    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for('dashboard.dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('landing_page'))