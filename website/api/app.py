"""Flask API backend for Central Florida SEO Services platform."""

import os
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Optional

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, verify_jwt_in_request
)
from sqlalchemy import text
import stripe

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL', 
    'sqlite:///central_florida_seo.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# Stripe configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
# Enable CORS for local dev and production
CORS(
    app,
    origins=[
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "http://localhost:3000",
        "https://centralfloridaseo.com",
    ],
)

# Database Models
class User(db.Model):
    """User accounts for both business owners and admin."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.String(20), nullable=False, default='business_owner')  # admin, business_owner
    is_active = db.Column(db.Boolean, default=True)
    email_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    # Relationships
    businesses = db.relationship('Business', backref='owner', lazy=True)
    
    def set_password(self, password: str):
        """Hash and set password."""
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        """Check if provided password matches hash."""
        return bcrypt.check_password_hash(self.password_hash, password)
    
    def to_dict(self) -> Dict:
        """Convert user to dictionary."""
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'role': self.role,
            'is_active': self.is_active,
            'email_verified': self.email_verified,
            'created_at': self.created_at.isoformat(),
            'last_login': self.last_login.isoformat() if self.last_login else None
        }


class Business(db.Model):
    """Business profiles and information."""
    __tablename__ = 'businesses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Business Information
    business_name = db.Column(db.String(200), nullable=False)
    website_url = db.Column(db.String(255))
    industry = db.Column(db.String(100))
    business_type = db.Column(db.String(50))  # local, national, ecommerce
    
    # Contact Information
    address = db.Column(db.String(255))
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(50), nullable=False, default='Florida')
    zip_code = db.Column(db.String(10))
    phone = db.Column(db.String(20))
    
    # SEO Details
    target_keywords = db.Column(db.Text)  # JSON array of keywords
    competitors = db.Column(db.Text)  # JSON array of competitor URLs
    current_rankings = db.Column(db.Text)  # JSON data
    
    # Subscription
    plan_tier = db.Column(db.String(20), nullable=False)  # starter, professional, enterprise
    subscription_status = db.Column(db.String(20), default='trial')  # trial, active, suspended, cancelled
    billing_cycle = db.Column(db.String(20), default='monthly')  # monthly, yearly
    stripe_customer_id = db.Column(db.String(100))
    stripe_subscription_id = db.Column(db.String(100))
    trial_ends_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    seo_reports = db.relationship('SEOReport', backref='business', lazy=True, cascade='all, delete-orphan')
    seo_logs = db.relationship('SEOLog', backref='business', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self) -> Dict:
        """Convert business to dictionary."""
        return {
            'id': self.id,
            'business_name': self.business_name,
            'website_url': self.website_url,
            'industry': self.industry,
            'business_type': self.business_type,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'zip_code': self.zip_code,
            'phone': self.phone,
            'target_keywords': self.target_keywords,
            'competitors': self.competitors,
            'current_rankings': self.current_rankings,
            'plan_tier': self.plan_tier,
            'subscription_status': self.subscription_status,
            'billing_cycle': self.billing_cycle,
            'trial_ends_at': self.trial_ends_at.isoformat() if self.trial_ends_at else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


class SEOReport(db.Model):
    """SEO analysis reports for businesses."""
    __tablename__ = 'seo_reports'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    
    # Report Details
    report_type = db.Column(db.String(50), nullable=False)  # audit, keywords, performance, etc.
    status = db.Column(db.String(20), default='pending')  # pending, running, completed, failed
    
    # Report Data
    results = db.Column(db.Text)  # JSON results
    score = db.Column(db.Float)  # Overall score (0-100)
    issues_found = db.Column(db.Integer, default=0)
    recommendations = db.Column(db.Text)  # JSON array
    
    # Execution Details
    execution_time_ms = db.Column(db.Integer)
    tools_used = db.Column(db.Text)  # JSON array of tool names
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def to_dict(self) -> Dict:
        """Convert report to dictionary."""
        return {
            'id': self.id,
            'business_id': self.business_id,
            'report_type': self.report_type,
            'status': self.status,
            'results': self.results,
            'score': self.score,
            'issues_found': self.issues_found,
            'recommendations': self.recommendations,
            'execution_time_ms': self.execution_time_ms,
            'tools_used': self.tools_used,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }


class SEOLog(db.Model):
    """Historical log of SEO changes and actions."""
    __tablename__ = 'seo_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    business_id = db.Column(db.Integer, db.ForeignKey('businesses.id'), nullable=False)
    
    # Log Details
    action_type = db.Column(db.String(50), nullable=False)  # report_run, keyword_update, etc.
    action_description = db.Column(db.Text, nullable=False)
    tool_name = db.Column(db.String(100))
    
    # Data Changes
    old_data = db.Column(db.Text)  # JSON of previous state
    new_data = db.Column(db.Text)  # JSON of new state
    
    # Metadata
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        """Convert log to dictionary."""
        return {
            'id': self.id,
            'business_id': self.business_id,
            'action_type': self.action_type,
            'action_description': self.action_description,
            'tool_name': self.tool_name,
            'old_data': self.old_data,
            'new_data': self.new_data,
            'user_id': self.user_id,
            'ip_address': self.ip_address,
            'created_at': self.created_at.isoformat()
        }


# Helper Functions
def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        verify_jwt_in_request()
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        if not user or user.role != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


def log_seo_action(business_id: int, action_type: str, description: str, 
                   tool_name: str = None, old_data: str = None, new_data: str = None):
    """Log SEO action for audit trail."""
    try:
        current_user_id = get_jwt_identity() if jwt_required else None
        
        log_entry = SEOLog(
            business_id=business_id,
            action_type=action_type,
            action_description=description,
            tool_name=tool_name,
            old_data=old_data,
            new_data=new_data,
            user_id=current_user_id,
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent')
        )
        
        db.session.add(log_entry)
        db.session.commit()
        
    except Exception as e:
        logger.error(f"Failed to log SEO action: {e}")


# Authentication Routes
@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register new user account."""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'password', 'first_name', 'last_name']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Check if user already exists
        if User.query.filter_by(email=data['email'].lower()).first():
            return jsonify({'error': 'Email already registered'}), 400
        
        # Create new user
        user = User(
            email=data['email'].lower(),
            first_name=data['first_name'],
            last_name=data['last_name'],
            phone=data.get('phone'),
            role='business_owner'
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        # Create access token
        access_token = create_access_token(identity=user.id)
        
        return jsonify({
            'message': 'User registered successfully',
            'access_token': access_token,
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login."""
    try:
        data = request.get_json()
        
        if not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password required'}), 400
        
        user = User.query.filter_by(email=data['email'].lower()).first()
        
        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Invalid email or password'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is deactivated'}), 401
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Create access token
        access_token = create_access_token(identity=user.id)
        
        return jsonify({
            'message': 'Login successful',
            'access_token': access_token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500


@app.route('/api/auth/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile."""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({'user': user.to_dict()}), 200
        
    except Exception as e:
        logger.error(f"Profile error: {e}")
        return jsonify({'error': 'Failed to get profile'}), 500


# Business Management Routes
@app.route('/api/businesses', methods=['POST'])
@jwt_required()
def create_business():
    """Create new business profile."""
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['business_name', 'city', 'plan_tier']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Create business
        business = Business(
            user_id=current_user_id,
            business_name=data['business_name'],
            website_url=data.get('website_url'),
            industry=data.get('industry'),
            business_type=data.get('business_type', 'local'),
            address=data.get('address'),
            city=data['city'],
            state=data.get('state', 'Florida'),
            zip_code=data.get('zip_code'),
            phone=data.get('phone'),
            target_keywords=data.get('target_keywords'),
            competitors=data.get('competitors'),
            plan_tier=data['plan_tier'],
            trial_ends_at=datetime.utcnow() + timedelta(days=14)  # 14-day trial
        )
        
        db.session.add(business)
        db.session.commit()
        
        # Log business creation
        log_seo_action(
            business.id,
            'business_created',
            f'Business profile created: {business.business_name}',
            new_data=str(business.to_dict())
        )
        
        return jsonify({
            'message': 'Business created successfully',
            'business': business.to_dict()
        }), 201
        
    except Exception as e:
        logger.error(f"Business creation error: {e}")
        return jsonify({'error': 'Failed to create business'}), 500


@app.route('/api/businesses', methods=['GET'])
@jwt_required()
def get_businesses():
    """Get businesses for current user."""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if user.role == 'admin':
            # Admin can see all businesses
            businesses = Business.query.all()
        else:
            # Business owners see only their businesses
            businesses = Business.query.filter_by(user_id=current_user_id).all()
        
        return jsonify({
            'businesses': [business.to_dict() for business in businesses]
        }), 200
        
    except Exception as e:
        logger.error(f"Get businesses error: {e}")
        return jsonify({'error': 'Failed to get businesses'}), 500


@app.route('/api/businesses/<int:business_id>', methods=['GET'])
@jwt_required()
def get_business(business_id):
    """Get specific business details."""
    try:
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        business = Business.query.get(business_id)
        if not business:
            return jsonify({'error': 'Business not found'}), 404
        
        # Check permissions
        if user.role != 'admin' and business.user_id != current_user_id:
            return jsonify({'error': 'Access denied'}), 403
        
        return jsonify({'business': business.to_dict()}), 200
        
    except Exception as e:
        logger.error(f"Get business error: {e}")
        return jsonify({'error': 'Failed to get business'}), 500


# Health check
@app.route('/api/health', methods=['GET'])
def health_check():
    """API health check."""
    try:
        # Test database connection
        db.session.execute(text('SELECT 1'))
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'version': '1.0.0'
        }), 200
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# Initialize database
@app.before_first_request
def create_tables():
    """Create database tables."""
    db.create_all()
    
    # Create admin user if doesn't exist
    admin_user = User.query.filter_by(email='admin@centralfloridaseo.com').first()
    if not admin_user:
        admin_user = User(
            email='admin@centralfloridaseo.com',
            first_name='Admin',
            last_name='User',
            role='admin',
            is_active=True,
            email_verified=True
        )
        admin_user.set_password('admin123')  # Change in production
        db.session.add(admin_user)
        db.session.commit()
        logger.info("Admin user created")


# Register blueprints
from seo_tools import seo_tools
from payments import payments

app.register_blueprint(seo_tools)
app.register_blueprint(payments)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)