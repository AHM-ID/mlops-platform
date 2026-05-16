"""
Rate Limiting Module
Provides Redis-backed rate limiting with sliding window algorithm
"""
import time
import os
from typing import Optional
from fastapi import HTTPException, Request, status
from redis import Redis
from shared.logging import setup_logging
from shared.config import get_redis_client

logger = setup_logging("rate_limiter")

# Rate limit configuration from environment
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # seconds

# Role-based rate limits (requests per window)
ROLE_RATE_LIMITS = {
    "admin": int(os.getenv("RATE_LIMIT_ADMIN", "1000")),
    "user": int(os.getenv("RATE_LIMIT_USER", "100")),
    "readonly": int(os.getenv("RATE_LIMIT_READONLY", "50")),
    "anonymous": int(os.getenv("RATE_LIMIT_ANONYMOUS", "10")),
}


class RateLimiter:
    """
    Redis-backed rate limiter using sliding window algorithm.
    """
    
    def __init__(self, redis_client: Optional[Redis] = None):
        """
        Initialize rate limiter.
        
        Args:
            redis_client: Redis client instance (optional, will create if not provided)
        """
        self.redis = redis_client or get_redis_client()
        self.enabled = RATE_LIMIT_ENABLED
        
    def _get_key(self, identifier: str, role: str) -> str:
        """Generate Redis key for rate limiting."""
        return f"rate_limit:{role}:{identifier}"
    
    def check_rate_limit(
        self,
        identifier: str,
        role: str = "anonymous",
        max_requests: Optional[int] = None,
        window: int = RATE_LIMIT_WINDOW
    ) -> dict:
        """
        Check if the request is within rate limits using sliding window.
        
        Args:
            identifier: Unique identifier (IP address, API key, user ID)
            role: User role for role-based limits
            max_requests: Maximum requests allowed (uses role default if None)
            window: Time window in seconds
            
        Returns:
            Dict with rate limit info: {allowed, remaining, reset_time}
            
        Raises:
            HTTPException: If rate limit exceeded
        """
        if not self.enabled:
            return {
                "allowed": True,
                "remaining": 999999,
                "reset_time": int(time.time()) + window
            }
        
        if max_requests is None:
            max_requests = ROLE_RATE_LIMITS.get(role, RATE_LIMIT_REQUESTS)
        
        key = self._get_key(identifier, role)
        current_time = time.time()
        window_start = current_time - window
        
        try:
            # Use Redis sorted set with timestamps as scores
            pipe = self.redis.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count requests in current window
            pipe.zcard(key)
            
            # Add current request
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiry on the key
            pipe.expire(key, window + 10)
            
            results = pipe.execute()
            request_count = results[1]
            
            remaining = max(0, max_requests - request_count - 1)
            reset_time = int(current_time + window)
            
            if request_count >= max_requests:
                logger.warning(
                    f"Rate limit exceeded for {role} identifier {identifier[:8]}... "
                    f"({request_count}/{max_requests} requests in {window}s window)"
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": "Rate limit exceeded",
                        "max_requests": max_requests,
                        "window_seconds": window,
                        "retry_after": window,
                        "reset_time": reset_time
                    },
                    headers={
                        "X-RateLimit-Limit": str(max_requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(reset_time),
                        "Retry-After": str(window)
                    }
                )
            
            logger.debug(
                f"Rate limit check passed for {role} identifier {identifier[:8]}... "
                f"({request_count + 1}/{max_requests})"
            )
            
            return {
                "allowed": True,
                "remaining": remaining,
                "reset_time": reset_time,
                "limit": max_requests
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Rate limiter error: {e}. Allowing request (fail-open).")
            # Fail open - allow request if Redis is down
            return {
                "allowed": True,
                "remaining": max_requests,
                "reset_time": int(current_time + window)
            }
    
    def get_rate_limit_status(self, identifier: str, role: str = "anonymous") -> dict:
        """
        Get current rate limit status without incrementing counter.
        
        Args:
            identifier: Unique identifier
            role: User role
            
        Returns:
            Dict with current status
        """
        if not self.enabled:
            return {"requests": 0, "limit": 999999, "remaining": 999999}
        
        max_requests = ROLE_RATE_LIMITS.get(role, RATE_LIMIT_REQUESTS)
        key = self._get_key(identifier, role)
        current_time = time.time()
        window_start = current_time - RATE_LIMIT_WINDOW
        
        try:
            # Remove old entries and count
            self.redis.zremrangebyscore(key, 0, window_start)
            request_count = self.redis.zcard(key)
            
            return {
                "requests": request_count,
                "limit": max_requests,
                "remaining": max(0, max_requests - request_count),
                "window_seconds": RATE_LIMIT_WINDOW
            }
        except Exception as e:
            logger.error(f"Error getting rate limit status: {e}")
            return {"requests": 0, "limit": max_requests, "remaining": max_requests}


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


async def rate_limit_dependency(request: Request) -> dict:
    """
    FastAPI dependency for rate limiting.
    Uses client IP as identifier and role from request state.
    
    Args:
        request: FastAPI request object
        
    Returns:
        Rate limit info dict
    """
    limiter = get_rate_limiter()
    
    # Get identifier (prefer API key, fallback to IP)
    api_key = request.headers.get("X-API-Key", "")
    identifier = api_key if api_key else request.client.host
    
    # Get role from request state (set by auth middleware)
    role = getattr(request.state, "role", "anonymous")
    
    # Check rate limit
    rate_info = limiter.check_rate_limit(identifier, role)
    
    # Store rate limit info in request state for response headers
    request.state.rate_limit_info = rate_info
    
    return rate_info
