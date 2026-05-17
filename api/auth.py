import os
from typing import Optional
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from shared.logging import setup_logging

logger = setup_logging("auth")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

API_KEYS = {
    "admin": os.getenv("API_KEY_ADMIN", "admin-secret-key-change-in-production"),
    "user": os.getenv("API_KEY_USER", "user-secret-key-change-in-production"),
    "readonly": os.getenv("API_KEY_READONLY", "readonly-secret-key-change-in-production"),
}

ROLE_PERMISSIONS = {
    "admin": ["read", "write", "retrain", "batch", "admin"],
    "user": ["read", "write", "batch"],
    "readonly": ["read"],
}

def get_role_from_api_key(api_key: str) -> Optional[str]:
    for role, key in API_KEYS.items():
        if api_key == key:
            return role
    return None

def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    if not api_key:
        logger.warning("Missing API key in request")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Provide X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    role = get_role_from_api_key(api_key)
    if not role:
        logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    
    logger.info(f"Authenticated request with role: {role}")
    return role

def require_permission(required_permission: str):
    async def permission_checker(role: str = Security(verify_api_key)) -> str:
        permissions = ROLE_PERMISSIONS.get(role, [])
        if required_permission not in permissions:
            logger.warning(f"Permission denied: role '{role}' lacks '{required_permission}' permission")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_permission}",
            )
        return role
    return permission_checker

require_read = require_permission("read")
require_write = require_permission("write")
require_retrain = require_permission("retrain")
require_batch = require_permission("batch")
require_admin = require_permission("admin")