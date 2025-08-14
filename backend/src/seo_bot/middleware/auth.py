"""Authentication and authorization middleware."""

import jwt
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..config import settings


class JWTAuth:
    """JWT authentication handler."""
    
    def __init__(self, secret_key: str = None, algorithm: str = "HS256"):
        self.secret_key = secret_key or settings.jwt_secret_key
        self.algorithm = algorithm
        self.token_expiry = getattr(settings, 'jwt_access_token_expires', 24) * 3600  # Convert hours to seconds
    
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create a new access token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(seconds=self.token_expiry)
        
        to_encode.update({
            'exp': expire,
            'iat': datetime.utcnow(),
            'type': 'access'
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create a new refresh token."""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=30)  # Refresh tokens last 30 days
        
        to_encode.update({
            'exp': expire,
            'iat': datetime.utcnow(),
            'type': 'refresh'
        })
        
        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get('type') != 'access':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )
            
            # Check expiration
            if datetime.utcnow() > datetime.fromtimestamp(payload.get('exp', 0)):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has expired"
                )
            
            return payload
            
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
    
    def refresh_access_token(self, refresh_token: str) -> str:
        """Create new access token from refresh token."""
        try:
            payload = jwt.decode(refresh_token, self.secret_key, algorithms=[self.algorithm])
            
            # Check token type
            if payload.get('type') != 'refresh':
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token"
                )
            
            # Create new access token
            user_data = {
                'user_id': payload.get('user_id'),
                'email': payload.get('email'),
                'role': payload.get('role')
            }
            
            return self.create_access_token(user_data)
            
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid refresh token: {str(e)}"
            )


class APIKeyAuth:
    """API key authentication handler."""
    
    def __init__(self):
        # In production, these would be stored in database
        self.api_keys = {
            'test_key_12345': {
                'type': 'test',
                'user_id': 'test_user',
                'permissions': ['read', 'write'],
                'rate_limit': 1000,
                'created_at': datetime.utcnow(),
                'last_used': None
            }
        }
    
    def validate_api_key(self, api_key: str) -> Dict[str, Any]:
        """Validate API key and return associated data."""
        if api_key not in self.api_keys:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )
        
        key_data = self.api_keys[api_key]
        
        # Update last used timestamp
        key_data['last_used'] = datetime.utcnow()
        
        return key_data
    
    def create_api_key(self, user_id: str, key_type: str = 'live') -> str:
        """Create a new API key."""
        import secrets
        api_key = f"{key_type}_{''.join(secrets.choice('abcdefghijklmnopqrstuvwxyz0123456789') for _ in range(32))}"
        
        self.api_keys[api_key] = {
            'type': key_type,
            'user_id': user_id,
            'permissions': ['read', 'write'],
            'rate_limit': 1000,
            'created_at': datetime.utcnow(),
            'last_used': None
        }
        
        return api_key


class RolePermissions:
    """Role-based permission system."""
    
    ROLES = {
        'admin': [
            'users:read', 'users:write', 'users:delete',
            'projects:read', 'projects:write', 'projects:delete',
            'keywords:read', 'keywords:write', 'keywords:delete',
            'analytics:read', 'analytics:write',
            'system:read', 'system:write'
        ],
        'user': [
            'projects:read', 'projects:write',
            'keywords:read', 'keywords:write',
            'analytics:read'
        ],
        'viewer': [
            'projects:read',
            'keywords:read',
            'analytics:read'
        ]
    }
    
    @classmethod
    def has_permission(cls, user_role: str, required_permission: str) -> bool:
        """Check if user role has required permission."""
        user_permissions = cls.ROLES.get(user_role, [])
        return required_permission in user_permissions
    
    @classmethod
    def require_permission(cls, permission: str):
        """Decorator to require specific permission."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                # This would be used with dependency injection in FastAPI
                # The actual permission check would happen in the endpoint
                return func(*args, **kwargs)
            return wrapper
        return decorator


class AuthMiddleware:
    """Authentication middleware for FastAPI."""
    
    def __init__(self, app):
        self.app = app
        self.jwt_auth = JWTAuth()
        self.api_key_auth = APIKeyAuth()
        self.bearer_scheme = HTTPBearer(auto_error=False)
        
        # Paths that don't require authentication
        self.public_paths = [
            '/health',
            '/docs',
            '/redoc',
            '/openapi.json',
            '/api/auth/login',
            '/api/auth/register',
            '/api/auth/refresh',
            '/favicon.ico'
        ]
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Skip authentication for public paths
        if self._is_public_path(request.url.path):
            await self.app(scope, receive, send)
            return
        
        try:
            # Authenticate request
            user_info = await self._authenticate_request(request)
            request.state.user = user_info
            
            await self.app(scope, receive, send)
            
        except HTTPException as e:
            # Return authentication error
            from fastapi.responses import JSONResponse
            response = JSONResponse(
                status_code=e.status_code,
                content={
                    'error': 'Authentication failed',
                    'detail': e.detail,
                    'timestamp': datetime.utcnow().isoformat()
                }
            )
            await response(scope, receive, send)
    
    def _is_public_path(self, path: str) -> bool:
        """Check if path is public and doesn't require authentication."""
        return any(path.startswith(public_path) for public_path in self.public_paths)
    
    async def _authenticate_request(self, request: Request) -> Dict[str, Any]:
        """Authenticate request using JWT or API key."""
        # Try API key authentication first
        api_key = request.headers.get('X-API-Key')
        if api_key:
            key_data = self.api_key_auth.validate_api_key(api_key)
            return {
                'user_id': key_data['user_id'],
                'auth_type': 'api_key',
                'permissions': key_data['permissions'],
                'rate_limit': key_data['rate_limit']
            }
        
        # Try JWT authentication
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            payload = self.jwt_auth.verify_token(token)
            
            return {
                'user_id': payload.get('user_id'),
                'email': payload.get('email'),
                'role': payload.get('role', 'user'),
                'auth_type': 'jwt',
                'permissions': RolePermissions.ROLES.get(payload.get('role', 'user'), [])
            }
        
        # No authentication provided
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )


# Dependency functions for FastAPI
async def get_current_user(request: Request) -> Dict[str, Any]:
    """Get current authenticated user from request."""
    if not hasattr(request.state, 'user'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    return request.state.user


async def get_current_active_user(request: Request) -> Dict[str, Any]:
    """Get current active user (not disabled)."""
    user = await get_current_user(request)
    
    # Check if user is active (this would query database in production)
    if user.get('status') == 'disabled':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user


def require_role(required_role: str):
    """Dependency to require specific user role."""
    async def check_role(request: Request):
        user = await get_current_user(request)
        user_role = user.get('role', 'user')
        
        if user_role != required_role and user_role != 'admin':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {required_role}"
            )
        
        return user
    
    return check_role


def require_permission(required_permission: str):
    """Dependency to require specific permission."""
    async def check_permission(request: Request):
        user = await get_current_user(request)
        user_permissions = user.get('permissions', [])
        
        if required_permission not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required permission: {required_permission}"
            )
        
        return user
    
    return check_permission


# Global instances
jwt_auth = JWTAuth()
api_key_auth = APIKeyAuth()