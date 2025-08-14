"""Rate limiting middleware for API endpoints."""

import time
import json
from typing import Dict, Any, Optional, Tuple
from functools import wraps
from datetime import datetime, timedelta

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import redis

from ..config import settings


class RateLimiter:
    """Redis-based rate limiter with sliding window algorithm."""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        """Initialize rate limiter with Redis client."""
        if redis_client is None:
            redis_url = settings.redis_url if hasattr(settings, 'redis_url') else 'redis://localhost:6379/0'
            self.redis = redis.from_url(redis_url, decode_responses=True)
        else:
            self.redis = redis_client
        
        # Default rate limits per endpoint type
        self.default_limits = {
            'auth': {'requests': 5, 'window': 60},  # 5 requests per minute
            'api': {'requests': 100, 'window': 60},  # 100 requests per minute
            'public': {'requests': 1000, 'window': 60},  # 1000 requests per minute
            'health': {'requests': 10, 'window': 10},  # 10 requests per 10 seconds
        }
    
    def _get_client_id(self, request: Request) -> str:
        """Get unique client identifier from request."""
        # Check for API key first
        api_key = request.headers.get('x-api-key')
        if api_key:
            return f"api_key:{api_key}"
        
        # Check for authenticated user
        auth_header = request.headers.get('authorization')
        if auth_header and auth_header.startswith('Bearer '):
            # In production, you'd decode the JWT to get user ID
            return f"user:{auth_header[-20:]}"  # Use last 20 chars as identifier
        
        # Fall back to IP address
        forwarded_for = request.headers.get('x-forwarded-for')
        if forwarded_for:
            # Get the first IP in case of proxy chain
            client_ip = forwarded_for.split(',')[0].strip()
        else:
            client_ip = request.client.host if request.client else 'unknown'
        
        return f"ip:{client_ip}"
    
    def _get_endpoint_category(self, request: Request) -> str:
        """Determine endpoint category for rate limiting."""
        path = request.url.path
        
        if path.startswith('/api/auth/'):
            return 'auth'
        elif path.startswith('/health'):
            return 'health'
        elif path.startswith('/api/'):
            return 'api'
        else:
            return 'public'
    
    def _sliding_window_check(
        self, 
        key: str, 
        limit: int, 
        window: int,
        current_time: float
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Implement sliding window rate limiting.
        
        Returns:
            Tuple of (is_allowed, rate_info)
        """
        pipe = self.redis.pipeline()
        
        # Remove expired entries
        pipe.zremrangebyscore(key, 0, current_time - window)
        
        # Count current requests in window
        pipe.zcard(key)
        
        # Add current request
        pipe.zadd(key, {str(current_time): current_time})
        
        # Set expiration
        pipe.expire(key, window + 1)
        
        results = pipe.execute()
        current_count = results[1]
        
        # Get time until reset
        oldest_request = self.redis.zrange(key, 0, 0, withscores=True)
        if oldest_request:
            reset_time = oldest_request[0][1] + window
        else:
            reset_time = current_time + window
        
        rate_info = {
            'limit': limit,
            'remaining': max(0, limit - current_count - 1),
            'reset': reset_time,
            'retry_after': max(0, int(reset_time - current_time)) if current_count >= limit else None
        }
        
        return current_count < limit, rate_info
    
    def check_rate_limit(
        self, 
        request: Request, 
        custom_limit: Optional[Dict[str, int]] = None
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is within rate limits.
        
        Args:
            request: FastAPI request object
            custom_limit: Optional custom rate limit {'requests': int, 'window': int}
            
        Returns:
            Tuple of (is_allowed, rate_info)
        """
        client_id = self._get_client_id(request)
        endpoint_category = self._get_endpoint_category(request)
        
        # Use custom limit or default
        if custom_limit:
            limit_config = custom_limit
        else:
            limit_config = self.default_limits.get(endpoint_category, self.default_limits['api'])
        
        # Create Redis key
        key = f"rate_limit:{endpoint_category}:{client_id}"
        current_time = time.time()
        
        try:
            return self._sliding_window_check(
                key, 
                limit_config['requests'], 
                limit_config['window'],
                current_time
            )
        except redis.RedisError as e:
            # If Redis is down, allow the request but log the error
            print(f"Redis error in rate limiting: {e}")
            return True, {
                'limit': limit_config['requests'],
                'remaining': limit_config['requests'],
                'reset': current_time + limit_config['window'],
                'retry_after': None
            }
    
    def get_rate_limit_status(self, request: Request) -> Dict[str, Any]:
        """Get current rate limit status without incrementing."""
        client_id = self._get_client_id(request)
        endpoint_category = self._get_endpoint_category(request)
        limit_config = self.default_limits.get(endpoint_category, self.default_limits['api'])
        
        key = f"rate_limit:{endpoint_category}:{client_id}"
        current_time = time.time()
        window = limit_config['window']
        
        try:
            # Remove expired entries
            self.redis.zremrangebyscore(key, 0, current_time - window)
            
            # Count current requests
            current_count = self.redis.zcard(key)
            
            # Get reset time
            oldest_request = self.redis.zrange(key, 0, 0, withscores=True)
            if oldest_request:
                reset_time = oldest_request[0][1] + window
            else:
                reset_time = current_time + window
            
            return {
                'limit': limit_config['requests'],
                'remaining': max(0, limit_config['requests'] - current_count),
                'reset': reset_time,
                'window': window
            }
        except redis.RedisError:
            return {
                'limit': limit_config['requests'],
                'remaining': limit_config['requests'],
                'reset': current_time + window,
                'window': window
            }


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(
    requests: int = None,
    window: int = None,
    per_user: bool = True,
    skip_on_error: bool = True
):
    """
    Decorator for rate limiting endpoints.
    
    Args:
        requests: Number of requests allowed
        window: Time window in seconds
        per_user: If True, limit per user; if False, global limit
        skip_on_error: If True, allow requests when Redis is unavailable
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            # Prepare custom limit if specified
            custom_limit = None
            if requests is not None and window is not None:
                custom_limit = {'requests': requests, 'window': window}
            
            # Check rate limit
            is_allowed, rate_info = rate_limiter.check_rate_limit(request, custom_limit)
            
            if not is_allowed:
                headers = {
                    'X-RateLimit-Limit': str(rate_info['limit']),
                    'X-RateLimit-Remaining': str(rate_info['remaining']),
                    'X-RateLimit-Reset': str(int(rate_info['reset'])),
                }
                
                if rate_info['retry_after']:
                    headers['Retry-After'] = str(rate_info['retry_after'])
                
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        'error': 'Rate limit exceeded',
                        'message': f"Too many requests. Try again in {rate_info['retry_after']} seconds.",
                        'rate_limit': rate_info
                    },
                    headers=headers
                )
            
            # Add rate limit headers to successful responses
            response = await func(request, *args, **kwargs)
            
            if hasattr(response, 'headers'):
                response.headers['X-RateLimit-Limit'] = str(rate_info['limit'])
                response.headers['X-RateLimit-Remaining'] = str(rate_info['remaining'])
                response.headers['X-RateLimit-Reset'] = str(int(rate_info['reset']))
            
            return response
        
        return wrapper
    return decorator


class RateLimitMiddleware:
    """FastAPI middleware for automatic rate limiting."""
    
    def __init__(self, app, rate_limiter: RateLimiter):
        self.app = app
        self.rate_limiter = rate_limiter
    
    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Skip rate limiting for certain paths
        skip_paths = ['/docs', '/redoc', '/openapi.json', '/favicon.ico']
        if any(request.url.path.startswith(path) for path in skip_paths):
            await self.app(scope, receive, send)
            return
        
        # Check rate limit
        is_allowed, rate_info = self.rate_limiter.check_rate_limit(request)
        
        if not is_allowed:
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    'error': 'Rate limit exceeded',
                    'message': f"Too many requests. Try again in {rate_info['retry_after']} seconds.",
                    'rate_limit': rate_info
                },
                headers={
                    'X-RateLimit-Limit': str(rate_info['limit']),
                    'X-RateLimit-Remaining': str(rate_info['remaining']),
                    'X-RateLimit-Reset': str(int(rate_info['reset'])),
                    'Retry-After': str(rate_info['retry_after']) if rate_info['retry_after'] else '60'
                }
            )
            await response(scope, receive, send)
            return
        
        # Continue with the request
        await self.app(scope, receive, send)