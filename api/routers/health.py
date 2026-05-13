from fastapi import APIRouter, HTTPException
from typing import Dict, Any
import logging

from .health_checks import (
    check_mlflow_health,
    check_redis_health,
    check_postgres_health,
    get_system_resources
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_health_response(
    mlflow_ok: bool,
    redis_ok: bool,
    postgres_ok: bool,
    system_resources: Dict[str, float]
) -> Dict[str, Any]:
    all_ok = mlflow_ok and redis_ok and postgres_ok
    
    return {
        "status": "healthy" if all_ok else "degraded",
        "dependencies": {
            "mlflow": "ok" if mlflow_ok else "error",
            "redis": "ok" if redis_ok else "error",
            "postgres": "ok" if postgres_ok else "error"
        },
        "system": system_resources
    }


@router.get("/health")
async def health_check():
    try:
        mlflow_ok = check_mlflow_health()
        redis_ok = check_redis_health()
        postgres_ok = check_postgres_health()
        system_resources = get_system_resources()
        
        response = _build_health_response(
            mlflow_ok, redis_ok, postgres_ok, system_resources
        )
        
        if response["status"] != "healthy":
            logger.warning(f"System degraded: {response}")
            raise HTTPException(status_code=503, detail=response)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(status_code=503, detail=str(e))
