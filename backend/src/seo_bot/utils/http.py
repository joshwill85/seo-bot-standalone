"""HTTP utilities for rate limiting and caching."""

import asyncio
import time
from typing import Dict, Optional
import hashlib


class RateLimiter:
    """Simple rate limiter for HTTP requests."""
    
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.last_request = 0.0
    
    async def wait(self):
        """Wait appropriate time before next request."""
        now = time.time()
        time_since_last = now - self.last_request
        
        if time_since_last < self.delay:
            await asyncio.sleep(self.delay - time_since_last)
        
        self.last_request = time.time()


class CacheManager:
    """Simple in-memory cache for HTTP responses."""
    
    def __init__(self, max_size: int = 1000):
        self.cache: Dict[str, tuple] = {}  # key -> (value, expiry)
        self.max_size = max_size
    
    def _generate_key(self, url: str) -> str:
        """Generate cache key from URL."""
        return hashlib.md5(url.encode()).hexdigest()
    
    def get(self, url: str) -> Optional[str]:
        """Get cached content if valid."""
        key = self._generate_key(url)
        
        if key in self.cache:
            value, expiry = self.cache[key]
            if time.time() < expiry:
                return value
            else:
                del self.cache[key]
        
        return None
    
    def set(self, url: str, content: str, ttl: int = 3600):
        """Cache content with TTL in seconds."""
        key = self._generate_key(url)
        expiry = time.time() + ttl
        
        # Simple LRU: remove oldest if at capacity
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        
        self.cache[key] = (content, expiry)
    
    def clear(self):
        """Clear all cached content."""
        self.cache.clear()