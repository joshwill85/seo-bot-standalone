"""Flask API backend for Central Florida SEO Services platform using Supabase."""

import os
import json
import logging
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, List, Optional

from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    get_jwt_identity, verify_jwt_in_request
)
import stripe
import asyncio

from supabase_client import db_ops

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

# Stripe configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')

# Initialize extensions
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


# Helper Functions
def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        verify_jwt_in_request()
        current_user_id = get_jwt_identity()
        
        # Run async function in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            user = loop.run_until_complete(db_ops.get_user_by_id(current_user_id))
        finally:
            loop.close()
        
        if not user or user.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function


async def log_seo_action_async(business_id: int, action_type: str, description: str, 
                              tool_name: str = None, old_data: str = None, new_data: str = None):
    """Log SEO action for audit trail."""
    try:
        current_user_id = get_jwt_identity() if request else None
        
        log_data = {
            'business_id': business_id,
            'action_type': action_type,
            'action_description': description,
            'tool_name': tool_name,
            'old_data': old_data,
            'new_data': new_data,
            'user_id': current_user_id,
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.headers.get('User-Agent') if request else None
        }
        
        await db_ops.create_seo_log(log_data)
        
    except Exception as e:
        logger.error(f"Failed to log SEO action: {e}")


def log_seo_action(business_id: int, action_type: str, description: str, 
                   tool_name: str = None, old_data: str = None, new_data: str = None):
    """Sync wrapper for logging SEO actions."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(log_seo_action_async(business_id, action_type, description, tool_name, old_data, new_data))
    finally:
        loop.close()


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
        
        # Run async operations in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Check if user already exists
            existing_user = loop.run_until_complete(db_ops.get_user_by_email(data['email'].lower()))
            if existing_user:
                return jsonify({'error': 'Email already registered'}), 400
            
            # Create new user
            user_data = {
                'email': data['email'].lower(),
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'phone': data.get('phone'),
                'role': 'business_owner',
                'password_hash': bcrypt.generate_password_hash(data['password']).decode('utf-8')
            }
            
            user = loop.run_until_complete(db_ops.create_user(user_data))
            
            # Create access token
            access_token = create_access_token(identity=user['id'])
            
            return jsonify({
                'message': 'User registered successfully',
                'access_token': access_token,
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'role': user['role']
                }
            }), 201
            
        finally:
            loop.close()
        
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
        
        # Run async operations in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            user = loop.run_until_complete(db_ops.get_user_by_email(data['email'].lower()))
            
            if not user or not bcrypt.check_password_hash(user['password_hash'], data['password']):
                return jsonify({'error': 'Invalid email or password'}), 401
            
            if not user.get('is_active', True):
                return jsonify({'error': 'Account is deactivated'}), 401
            
            # Update last login
            loop.run_until_complete(db_ops.update_user_login(user['id']))
            
            # Create access token
            access_token = create_access_token(identity=user['id'])
            
            return jsonify({
                'message': 'Login successful',
                'access_token': access_token,
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'role': user['role']
                }
            }), 200
            
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500


@app.route('/api/auth/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile."""
    try:
        current_user_id = get_jwt_identity()
        
        # Run async operations in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            user = loop.run_until_complete(db_ops.get_user_by_id(current_user_id))
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            return jsonify({
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'phone': user.get('phone'),
                    'role': user['role'],
                    'is_active': user.get('is_active', True),
                    'email_verified': user.get('email_verified', False),
                    'created_at': user.get('created_at'),
                    'last_login': user.get('last_login')
                }
            }), 200
            
        finally:
            loop.close()
        
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
        
        # Run async operations in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Create business
            business_data = {
                'user_id': current_user_id,
                'business_name': data['business_name'],
                'website_url': data.get('website_url'),
                'industry': data.get('industry'),
                'business_type': data.get('business_type', 'local'),
                'address': data.get('address'),
                'city': data['city'],
                'state': data.get('state', 'Florida'),
                'zip_code': data.get('zip_code'),
                'phone': data.get('phone'),
                'target_keywords': json.dumps(data.get('target_keywords', [])) if data.get('target_keywords') else None,
                'competitors': json.dumps(data.get('competitors', [])) if data.get('competitors') else None,
                'plan_tier': data['plan_tier'],
                'trial_ends_at': (datetime.utcnow() + timedelta(days=14)).isoformat()  # 14-day trial
            }
            
            business = loop.run_until_complete(db_ops.create_business(business_data))
            
            # Log business creation
            log_seo_action(
                business['id'],
                'business_created',
                f'Business profile created: {business["business_name"]}',
                new_data=json.dumps(business)
            )
            
            return jsonify({
                'message': 'Business created successfully',
                'business': business
            }), 201
            
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Business creation error: {e}")
        return jsonify({'error': 'Failed to create business'}), 500


@app.route('/api/businesses', methods=['GET'])
@jwt_required()
def get_businesses():
    """Get businesses for current user."""
    try:
        current_user_id = get_jwt_identity()
        
        # Run async operations in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            user = loop.run_until_complete(db_ops.get_user_by_id(current_user_id))
            
            if user.get('role') == 'admin':
                # Admin can see all businesses
                businesses = loop.run_until_complete(db_ops.get_all_businesses())
            else:
                # Business owners see only their businesses
                businesses = loop.run_until_complete(db_ops.get_businesses_by_user(current_user_id))
            
            return jsonify({
                'businesses': businesses
            }), 200
            
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Get businesses error: {e}")
        return jsonify({'error': 'Failed to get businesses'}), 500


@app.route('/api/businesses/<int:business_id>', methods=['GET'])
@jwt_required()
def get_business(business_id):
    """Get specific business details."""
    try:
        current_user_id = get_jwt_identity()
        
        # Run async operations in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            user = loop.run_until_complete(db_ops.get_user_by_id(current_user_id))
            business = loop.run_until_complete(db_ops.get_business_by_id(business_id))
            
            if not business:
                return jsonify({'error': 'Business not found'}), 404
            
            # Check permissions
            if user.get('role') != 'admin' and business['user_id'] != current_user_id:
                return jsonify({'error': 'Access denied'}), 403
            
            return jsonify({'business': business}), 200
            
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Get business error: {e}")
        return jsonify({'error': 'Failed to get business'}), 500


@app.route('/api/businesses/<int:business_id>/analytics', methods=['GET'])
@jwt_required()
def get_business_analytics(business_id):
    """Get business analytics and insights."""
    try:
        current_user_id = get_jwt_identity()
        
        # Run async operations in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            user = loop.run_until_complete(db_ops.get_user_by_id(current_user_id))
            business = loop.run_until_complete(db_ops.get_business_by_id(business_id))
            
            if not business:
                return jsonify({'error': 'Business not found'}), 404
            
            # Check permissions
            if user.get('role') != 'admin' and business['user_id'] != current_user_id:
                return jsonify({'error': 'Access denied'}), 403
            
            # Get analytics
            analytics = loop.run_until_complete(db_ops.get_business_analytics(business_id))
            
            return jsonify({
                'business_id': business_id,
                'analytics': analytics
            }), 200
            
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Get business analytics error: {e}")
        return jsonify({'error': 'Failed to get business analytics'}), 500


# Admin Routes
@app.route('/api/admin/dashboard', methods=['GET'])
@jwt_required()
@admin_required
def admin_dashboard():
    """Get admin dashboard data."""
    try:
        # Run async operations in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Get all businesses with analytics
            all_businesses = loop.run_until_complete(db_ops.get_all_businesses())
            
            dashboard_data = {
                'total_businesses': len(all_businesses),
                'businesses_by_plan': {},
                'businesses_by_status': {},
                'recent_signups': [],
                'revenue_summary': {
                    'monthly_recurring': 0,
                    'trial_businesses': 0,
                    'active_subscriptions': 0
                }
            }
            
            # Process business data
            for business in all_businesses:
                # Count by plan
                plan = business.get('plan_tier', 'unknown')
                dashboard_data['businesses_by_plan'][plan] = dashboard_data['businesses_by_plan'].get(plan, 0) + 1
                
                # Count by status
                status = business.get('subscription_status', 'unknown')
                dashboard_data['businesses_by_status'][status] = dashboard_data['businesses_by_status'].get(status, 0) + 1
                
                # Recent signups (last 30 days)
                created_at = datetime.fromisoformat(business['created_at'].replace('Z', '+00:00'))
                if created_at >= datetime.utcnow() - timedelta(days=30):
                    dashboard_data['recent_signups'].append({
                        'business_name': business['business_name'],
                        'plan_tier': business['plan_tier'],
                        'created_at': business['created_at']
                    })
                
                # Revenue calculations
                if status == 'trial':
                    dashboard_data['revenue_summary']['trial_businesses'] += 1
                elif status == 'active':
                    dashboard_data['revenue_summary']['active_subscriptions'] += 1
                    
                    # Estimate monthly revenue
                    plan_prices = {'starter': 64, 'professional': 240, 'enterprise': 480}
                    price = plan_prices.get(plan, 0)
                    dashboard_data['revenue_summary']['monthly_recurring'] += price
            
            return jsonify({
                'dashboard': dashboard_data
            }), 200
            
        finally:
            loop.close()
        
    except Exception as e:
        logger.error(f"Admin dashboard error: {e}")
        return jsonify({'error': 'Failed to get dashboard data'}), 500


# Health check
@app.route('/api/health', methods=['GET'])
def health_check():
    """API health check."""
    try:
        # Test Supabase connection
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Simple query to test connection
            loop.run_until_complete(db_ops.client.client.table('users').select('id').limit(1).execute())
            
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.utcnow().isoformat(),
                'version': '1.0.0',
                'database': 'supabase_connected'
            }), 200
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'database': 'supabase_error'
        }), 500


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500


# Register blueprints
from seo_tools_supabase import seo_tools
from payments_supabase import payments

app.register_blueprint(seo_tools)
app.register_blueprint(payments)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)