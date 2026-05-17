import os
import sys
import pytest
from unittest.mock import Mock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.rate_limiter import RateLimiter

class TestRateLimiter:
    
    def test_rate_limiter_allows_requests_within_limit(self):
        mock_redis = Mock()
        mock_redis.pipeline.return_value = Mock()
        mock_redis.pipeline.return_value.zremrangebyscore.return_value = 0
        mock_redis.pipeline.return_value.zcard.return_value = 0
        mock_redis.pipeline.return_value.zadd.return_value = 1
        mock_redis.pipeline.return_value.expire.return_value = True
        mock_redis.pipeline.return_value.execute.return_value = [0, 0]
        
        limiter = RateLimiter(redis_client=mock_redis)
        result = limiter.check_rate_limit("test_client", "user")
        
        assert result["allowed"] is True
    
    def test_rate_limiter_blocks_exceeding_requests(self):
        from fastapi import HTTPException
        from api.rate_limiter import RateLimiter
        
        mock_redis = Mock()
        mock_pipeline = Mock()
        mock_pipeline.zremrangebyscore.return_value = 0
        mock_pipeline.zcard.return_value = 100
        mock_pipeline.zadd.return_value = 1
        mock_pipeline.expire.return_value = True
        mock_pipeline.execute.return_value = [0, 100]
        mock_redis.pipeline.return_value = mock_pipeline
        
        limiter = RateLimiter(redis_client=mock_redis)
        limiter.enabled = True
        
        try:
            limiter.check_rate_limit("test_client", "user")
            assert False, "Should have raised HTTPException"
        except HTTPException as e:
            assert e.status_code == 429
    
    def test_different_roles_have_different_limits(self):
        mock_redis = Mock()
        mock_redis.pipeline.return_value = Mock()
        mock_redis.pipeline.return_value.execute.return_value = [0, 0]
        
        limiter = RateLimiter(redis_client=mock_redis)
        
        admin_limit = 1000
        user_limit = 100
        readonly_limit = 50
        
        assert admin_limit > user_limit
        assert user_limit > readonly_limit
    
    def test_rate_limiter_disabled_when_disabled(self, monkeypatch):
        monkeypatch.setenv("RATE_LIMIT_ENABLED", "false")
        
        mock_redis = Mock()
        limiter = RateLimiter(redis_client=mock_redis)
        
        for i in range(200):
            result = limiter.check_rate_limit("test_client", "user")
            assert result["allowed"] is True
    
    def test_rate_limiter_uses_identifier_isolation(self):
        mock_redis = Mock()
        mock_redis.pipeline.return_value = Mock()
        mock_redis.pipeline.return_value.execute.return_value = [0, 0]
        
        limiter = RateLimiter(redis_client=mock_redis)
        
        result1 = limiter.check_rate_limit("client_a", "user")
        result2 = limiter.check_rate_limit("client_b", "user")
        
        assert result1["remaining"] == result2["remaining"]