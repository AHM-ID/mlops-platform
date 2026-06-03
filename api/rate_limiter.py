import time
import os
from typing import Optional, Dict
from fastapi import HTTPException, status, Request
from redis import Redis
from shared.logging import setup_logging
from shared.config import get_redis_client, ROLE_RATE_LIMITS, RATE_LIMIT_ENABLED, RATE_LIMIT_WINDOW

logger = setup_logging("rate_limiter")

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, timeout_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"

    def record_success(self):
        if self.state == "half-open":
            self.state = "closed"
            self.failure_count = 0
            logger.info("Circuit breaker closed after successful call")

    def record_failure(self) -> bool:
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.state == "closed" and self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
            return True
        return False

    def allow_request(self) -> bool:
        if self.state == "closed":
            return True
        elif self.state == "open":
            if time.time() - self.last_failure_time >= self.timeout_seconds:
                self.state = "half-open"
                logger.info("Circuit breaker half-open, allowing test request")
                return True
            return False
        return True

    def get_state(self) -> str:
        return self.state

class RateLimiter:
    def __init__(self, redis_client: Optional[Redis] = None):
        self.redis = redis_client or get_redis_client()
        self.enabled = RATE_LIMIT_ENABLED
        self.circuit_breaker = CircuitBreaker()

    def _get_key(self, identifier: str, role: str) -> str:
        return f"rate_limit:{role}:{identifier}"

    def _fail_open_response(self, window: int) -> Dict:
        current_time = time.time()
        return {
            "allowed": True,
            "remaining": 999999,
            "reset_time": int(current_time + window),
            "limit": 999999,
            "circuit_open": True
        }

    def check_rate_limit(
        self,
        identifier: str,
        role: str = "anonymous",
        max_requests: Optional[int] = None,
        window: int = RATE_LIMIT_WINDOW
    ) -> Dict:
        if not self.enabled:
            return {
                "allowed": True,
                "remaining": 999999,
                "reset_time": int(time.time()) + window,
                "limit": 999999
            }

        if not self.circuit_breaker.allow_request():
            logger.warning(f"Rate limiter circuit open, failing open for {identifier}")
            return self._fail_open_response(window)

        if max_requests is None:
            max_requests = ROLE_RATE_LIMITS.get(role, 100)

        key = self._get_key(identifier, role)
        current_time = time.time()
        window_start = current_time - window

        try:
            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.zadd(key, {str(current_time): current_time})
            pipe.expire(key, window + 10)

            results = pipe.execute()
            request_count = results[1]

            remaining = max(0, max_requests - request_count - 1)
            reset_time = int(current_time + window)

            self.circuit_breaker.record_success()

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
            self.circuit_breaker.record_failure()
            return self._fail_open_response(window)

    def get_rate_limit_status(self, identifier: str, role: str = "anonymous") -> Dict:
        if not self.enabled:
            return {"requests": 0, "limit": 999999, "remaining": 999999, "circuit_state": self.circuit_breaker.get_state()}

        max_requests = ROLE_RATE_LIMITS.get(role, 100)
        key = self._get_key(identifier, role)
        current_time = time.time()
        window_start = current_time - RATE_LIMIT_WINDOW

        try:
            self.redis.zremrangebyscore(key, 0, window_start)
            request_count = self.redis.zcard(key)
            return {
                "requests": request_count,
                "limit": max_requests,
                "remaining": max(0, max_requests - request_count),
                "window_seconds": RATE_LIMIT_WINDOW,
                "circuit_state": self.circuit_breaker.get_state()
            }
        except Exception as e:
            logger.error(f"Error getting rate limit status: {e}")
            return {"requests": 0, "limit": max_requests, "remaining": max_requests, "circuit_state": "error"}

_rate_limiter: Optional[RateLimiter] = None

def get_rate_limiter() -> RateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter

def get_real_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    if request.client:
        return request.client.host
    return "unknown"

async def rate_limit_dependency(request: Request) -> Dict:
    limiter = get_rate_limiter()
    real_ip = get_real_client_ip(request)
    api_key = request.headers.get("X-API-Key", "")
    identifier = api_key if api_key else real_ip
    role = getattr(request.state, "role", "anonymous")
    rate_info = limiter.check_rate_limit(identifier, role)
    request.state.rate_limit_info = rate_info
    return rate_info
