import os
import sys
import pytest
from fastapi import HTTPException
from unittest.mock import Mock, patch, AsyncMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.auth import get_role_from_api_key, verify_api_key

class TestAuth:

    def test_get_role_from_valid_api_key(self):
        role = get_role_from_api_key("admin-secret-key-change-in-production")
        assert role == "admin"

    def test_get_role_from_invalid_api_key(self):
        role = get_role_from_api_key("invalid-key")
        assert role is None

    def test_verify_api_key_valid(self):
        role = verify_api_key("admin-secret-key-change-in-production")
        assert role == "admin"

    def test_verify_api_key_missing(self):
        with pytest.raises(HTTPException) as exc:
            verify_api_key(None)
        assert exc.value.status_code == 401

    def test_require_read_permission_admin(self):
        from api.auth import require_permission
        import asyncio
        read_checker = require_permission("read")
        async def run_check():
            return await read_checker(role="admin")
        
        result = asyncio.run(run_check())
        assert result == "admin"

    def test_require_write_permission_readonly_fails(self):
        from api.auth import require_write

        async def mock_verify_api_key():
            return "readonly"

        with patch('api.auth.verify_api_key', side_effect=mock_verify_api_key):
            import asyncio
            with pytest.raises(HTTPException) as exc:
                asyncio.run(require_write())
            assert exc.value.status_code == 403