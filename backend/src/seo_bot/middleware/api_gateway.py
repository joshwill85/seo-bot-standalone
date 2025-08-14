"""API Gateway middleware for request routing, validation, and management."""

import time
import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import settings


class APIGatewayMiddleware(BaseHTTPMiddleware):
    """
    API Gateway middleware that handles:
    - Request/response logging
    - API versioning
    - Request validation
    - Response transformation
    - Security headers
    - CORS handling
    """
    
    def __init__(self, app, config: Optional[Dict[str, Any]] = None):
        super().__init__(app)
        self.config = config or {}
        self.supported_versions = ['v1', 'v2']
        self.default_version = 'v1'
        
        # API key validation patterns
        self.api_key_patterns = {
            'test': r'^test_[a-zA-Z0-9]{32}$',
            'live': r'^live_[a-zA-Z0-9]{32}$'
        }
    
    async def dispatch(self, request: Request, call_next):
        """Main middleware dispatch method."""
        start_time = time.time()
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        try:
            # Pre-process request
            await self._preprocess_request(request)
            
            # Process the request
            response = await call_next(request)
            
            # Post-process response
            response = await self._postprocess_response(request, response, start_time)
            
            return response
            
        except HTTPException as e:
            # Handle HTTP exceptions
            return await self._handle_http_exception(request, e, start_time)
        except Exception as e:
            # Handle unexpected exceptions
            return await self._handle_unexpected_exception(request, e, start_time)
    
    async def _preprocess_request(self, request: Request) -> None:
        """Preprocess incoming requests."""
        # Add request timestamp
        request.state.start_time = time.time()
        
        # Validate API version
        await self._validate_api_version(request)
        
        # Validate API key if required
        await self._validate_api_key(request)
        
        # Set request context
        await self._set_request_context(request)
        
        # Log request
        await self._log_request(request)
    
    async def _validate_api_version(self, request: Request) -> None:
        """Validate and set API version."""
        version = None
        
        # Check version in path (e.g., /api/v1/...)
        path_parts = request.url.path.split('/')
        if len(path_parts) >= 3 and path_parts[2].startswith('v'):
            version = path_parts[2]
        
        # Check version in header
        if not version:
            version = request.headers.get('API-Version', self.default_version)
        
        # Check version in query parameter
        if not version:
            version = request.query_params.get('version', self.default_version)
        
        # Validate version
        if version not in self.supported_versions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported API version: {version}. Supported versions: {', '.join(self.supported_versions)}"
            )
        
        request.state.api_version = version
    
    async def _validate_api_key(self, request: Request) -> None:
        """Validate API key for protected endpoints."""
        # Skip validation for public endpoints
        public_paths = ['/health', '/docs', '/redoc', '/openapi.json']
        if any(request.url.path.startswith(path) for path in public_paths):
            return
        
        # Skip validation for auth endpoints (they have their own validation)
        if request.url.path.startswith('/api/auth/'):
            return
        
        # Check for API key
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            # Check for Bearer token (JWT)
            auth_header = request.headers.get('Authorization')
            if auth_header and auth_header.startswith('Bearer '):
                # JWT validation would happen in auth middleware
                return
            
            # No authentication provided
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key or authentication token required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Validate API key format
        key_type = 'test' if api_key.startswith('test_') else 'live'
        if key_type not in self.api_key_patterns:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key format"
            )
        
        # Store key info in request state
        request.state.api_key = api_key
        request.state.api_key_type = key_type
    
    async def _set_request_context(self, request: Request) -> None:
        """Set request context information."""
        request.state.user_agent = request.headers.get('User-Agent', 'Unknown')
        request.state.client_ip = self._get_client_ip(request)
        request.state.request_timestamp = datetime.utcnow().isoformat()
    
    def _get_client_ip(self, request: Request) -> str:
        """Get real client IP address."""
        # Check for forwarded IP (reverse proxy)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            return forwarded_for.split(',')[0].strip()
        
        # Check for real IP header
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip
        
        # Fall back to direct client
        return request.client.host if request.client else 'unknown'
    
    async def _log_request(self, request: Request) -> None:
        """Log incoming request."""
        if not self.config.get('enable_request_logging', True):
            return
        
        log_data = {
            'request_id': request.state.request_id,
            'timestamp': request.state.request_timestamp,
            'method': request.method,
            'path': request.url.path,
            'query_params': dict(request.query_params),
            'client_ip': request.state.client_ip,
            'user_agent': request.state.user_agent,
            'api_version': getattr(request.state, 'api_version', None),
            'api_key_type': getattr(request.state, 'api_key_type', None)
        }
        
        # Log to structured logger
        print(f"[REQUEST] {json.dumps(log_data)}")
    
    async def _postprocess_response(
        self, 
        request: Request, 
        response, 
        start_time: float
    ):
        """Post-process outgoing responses."""
        # Calculate response time
        response_time = time.time() - start_time
        
        # Add custom headers
        response.headers['X-Request-ID'] = request.state.request_id
        response.headers['X-Response-Time'] = f"{response_time:.3f}s"
        response.headers['X-API-Version'] = getattr(request.state, 'api_version', self.default_version)
        
        # Add security headers
        self._add_security_headers(response)
        
        # Log response
        await self._log_response(request, response, response_time)
        
        return response
    
    def _add_security_headers(self, response) -> None:
        """Add security headers to response."""
        security_headers = {
            'X-Content-Type-Options': 'nosniff',
            'X-Frame-Options': 'DENY',
            'X-XSS-Protection': '1; mode=block',
            'Referrer-Policy': 'strict-origin-when-cross-origin',
            'Content-Security-Policy': "default-src 'self'",
        }
        
        for header, value in security_headers.items():
            if header not in response.headers:
                response.headers[header] = value
    
    async def _log_response(
        self, 
        request: Request, 
        response, 
        response_time: float
    ) -> None:
        """Log outgoing response."""
        if not self.config.get('enable_response_logging', True):
            return
        
        log_data = {
            'request_id': request.state.request_id,
            'timestamp': datetime.utcnow().isoformat(),
            'method': request.method,
            'path': request.url.path,
            'status_code': response.status_code,
            'response_time_ms': round(response_time * 1000, 2),
            'client_ip': request.state.client_ip
        }
        
        # Log to structured logger
        print(f"[RESPONSE] {json.dumps(log_data)}")
    
    async def _handle_http_exception(
        self, 
        request: Request, 
        exception: HTTPException, 
        start_time: float
    ) -> JSONResponse:
        """Handle HTTP exceptions with consistent error format."""
        response_time = time.time() - start_time
        
        error_response = {
            'error': {
                'type': 'http_error',
                'code': exception.status_code,
                'message': exception.detail,
                'request_id': request.state.request_id,
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        
        # Add debug info in development
        if settings.environment == 'development':
            error_response['debug'] = {
                'path': request.url.path,
                'method': request.method,
                'response_time_ms': round(response_time * 1000, 2)
            }
        
        headers = getattr(exception, 'headers', {})
        headers.update({
            'X-Request-ID': request.state.request_id,
            'X-Response-Time': f"{response_time:.3f}s"
        })
        
        return JSONResponse(
            status_code=exception.status_code,
            content=error_response,
            headers=headers
        )
    
    async def _handle_unexpected_exception(
        self, 
        request: Request, 
        exception: Exception, 
        start_time: float
    ) -> JSONResponse:
        """Handle unexpected exceptions."""
        response_time = time.time() - start_time
        
        # Log the exception
        error_log = {
            'request_id': request.state.request_id,
            'timestamp': datetime.utcnow().isoformat(),
            'error_type': type(exception).__name__,
            'error_message': str(exception),
            'path': request.url.path,
            'method': request.method,
            'client_ip': request.state.client_ip
        }
        print(f"[ERROR] {json.dumps(error_log)}")
        
        # Return generic error response
        error_response = {
            'error': {
                'type': 'internal_error',
                'code': 500,
                'message': 'An internal server error occurred',
                'request_id': request.state.request_id,
                'timestamp': datetime.utcnow().isoformat()
            }
        }
        
        # Add debug info in development
        if settings.environment == 'development':
            error_response['debug'] = {
                'exception_type': type(exception).__name__,
                'exception_message': str(exception),
                'path': request.url.path,
                'method': request.method,
                'response_time_ms': round(response_time * 1000, 2)
            }
        
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response,
            headers={
                'X-Request-ID': request.state.request_id,
                'X-Response-Time': f"{response_time:.3f}s"
            }
        )


class CORSMiddleware:
    """Custom CORS middleware with advanced configuration."""
    
    def __init__(
        self,
        app,
        allow_origins: List[str] = None,
        allow_credentials: bool = True,
        allow_methods: List[str] = None,
        allow_headers: List[str] = None,
        expose_headers: List[str] = None,
        max_age: int = 600
    ):
        self.app = app
        self.allow_origins = allow_origins or ['*']
        self.allow_credentials = allow_credentials
        self.allow_methods = allow_methods or ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH']
        self.allow_headers = allow_headers or [
            'Accept',
            'Accept-Language',
            'Content-Language',
            'Content-Type',
            'Authorization',
            'X-API-Key',
            'X-Request-ID',
            'API-Version'
        ]
        self.expose_headers = expose_headers or [
            'X-Request-ID',
            'X-Response-Time',
            'X-API-Version',
            'X-RateLimit-Limit',
            'X-RateLimit-Remaining',
            'X-RateLimit-Reset'
        ]
        self.max_age = max_age
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        origin = request.headers.get('origin')
        
        # Check if origin is allowed
        if origin and not self._is_allowed_origin(origin):
            # Return 403 for disallowed origins
            response = JSONResponse(
                status_code=403,
                content={'error': 'Origin not allowed'},
                headers={'Access-Control-Allow-Origin': 'null'}
            )
            await response(scope, receive, send)
            return
        
        # Handle preflight requests
        if request.method == 'OPTIONS':
            await self._handle_preflight(scope, receive, send, origin)
            return
        
        # Add CORS headers to response
        async def send_with_cors(message):
            if message['type'] == 'http.response.start':
                headers = dict(message.get('headers', []))
                
                if origin:
                    headers[b'access-control-allow-origin'] = origin.encode()
                else:
                    headers[b'access-control-allow-origin'] = b'*'
                
                if self.allow_credentials:
                    headers[b'access-control-allow-credentials'] = b'true'
                
                if self.expose_headers:
                    headers[b'access-control-expose-headers'] = ', '.join(self.expose_headers).encode()
                
                message['headers'] = [(k, v) for k, v in headers.items()]
            
            await send(message)
        
        await self.app(scope, receive, send_with_cors)
    
    def _is_allowed_origin(self, origin: str) -> bool:
        """Check if origin is in allowed list."""
        if '*' in self.allow_origins:
            return True
        return origin in self.allow_origins
    
    async def _handle_preflight(self, scope, receive, send, origin):
        """Handle CORS preflight requests."""
        headers = {
            'access-control-allow-methods': ', '.join(self.allow_methods),
            'access-control-allow-headers': ', '.join(self.allow_headers),
            'access-control-max-age': str(self.max_age)
        }
        
        if origin:
            headers['access-control-allow-origin'] = origin
        else:
            headers['access-control-allow-origin'] = '*'
        
        if self.allow_credentials:
            headers['access-control-allow-credentials'] = 'true'
        
        response = JSONResponse(
            status_code=200,
            content={},
            headers=headers
        )
        await response(scope, receive, send)