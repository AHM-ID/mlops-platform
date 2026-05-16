import os
import sys
import pytest
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.rate_limiter import RateLimiter, ROLE_RATE_LIMITS

class TestRateLimiter:

    def test_rate_limiter_allows_requests_within_limit(self):
        limiter = RateLimiter()
        identifier = "test_client_1"
        role = "user"
        limit = ROLE_RATE_LIMITS.get(role, 100)
        
        for i in range(limit):
            result = limiter.check_rate_limit(identifier, role)
            assert result["allowed"] is True

    def test_rate_limiter_blocks_exceeding_requests(self):
        limiter = RateLimiter()
        identifier = "test_client_2"
        role = "user"
        limit = ROLE_RATE_LIMITS.get(role, 100)
        
        for i in range(limit):
            limiter.check_rate_limit(identifier, role)
        
        import pytest
        with pytest.raises(Exception):
            limiter.check_rate_limit(identifier, role)

    def test_different_roles_have_different_limits(self):
        limiter = RateLimiter()
        
        admin_limit = ROLE_RATE_LIMITS.get("admin", 1000)
        user_limit = ROLE_RATE_LIMITS.get("user", 100)
        readonly_limit = ROLE_RATE_LIMITS.get("readonly", 50)
        
        assert admin_limit > user_limit
        assert user_limit > readonly_limit

    def test_rate_limiter_disabled_when_disabled(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
        
        limiter = RateLimiter()
        identifier = "test_client"
        role = "user"
        
        for i in range(200):
            result = limiter.check_rate_limit(identifier, role)
            assert result["allowed"] is True

    def test_rate_limiter_uses_identifier_isolation(self):
        limiter = RateLimiter()
        
        result1 = limiter.check_rate_limit("client_a", "user")
        result2 = limiter.check_rate_limit("client_b", "user")
        
        assert result1["remaining"] == result2["remaining"]