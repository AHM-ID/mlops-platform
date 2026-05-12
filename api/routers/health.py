"""
Health Check Router
Provides endpoints for system health and readiness checks
"""

from fastapi import APIRouter, HTTPException, status
from datetime import datetime
import mlflow
import redis
import psycopg2
from typing import Dict

from api.schemas import HealthStatus
from shared.config import (
    MLFLOW_TRACKING_URI, 
    REDIS_URL, 
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_USER,
    POSTGRES_PASSWORD, 
    POSTGRES_DB
)
from shared.logging import setup_logging

logger = setup_logging("health_router")

router = APIRouter()


def check_mlflow() -> str:
    """Check MLflow connectivity"""
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        # Try to list experiments
        experiments = mlflow.search_experiments(max_results=1)
        return "connected"
    except Exception as e:
        logger.warning(f"MLflow health check failed: {e}")
        return "disconnected"


def check_redis() -> str:
    """Check Redis connectivity"""
    try:
        client = redis.from_url(REDIS_URL, socket_connect_timeout=5)
        client.ping()
        return "connected"
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        return "disconnected"


def check_postgres() -> str:
    """Check PostgreSQL connectivity"""
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB
        )
        conn.close()
        return "connected"
    except Exception as e:
        logger.warning(f"PostgreSQL health check failed: {e}")
        return "disconnected"


@router.get(
    "/health",
    response_model=HealthStatus,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Check the health of the API and its dependencies",
    responses={
        200: {
            "description": "API is healthy",
            "example": {
                "status": "healthy",
                "version": "3.0.0",
                "timestamp": "2024-01-15T10:30:00Z",
                "services": {
                    "mlflow": "connected",
                    "postgres": "connected",
                    "redis": "connected"
                }
            }
        },
        503: {
            "description": "API is degraded or unhealthy",
            "example": {
                "status": "unhealthy",
                "version": "3.0.0",
                "timestamp": "2024-01-15T10:30:00Z",
                "services": {
                    "mlflow": "disconnected",
                    "postgres": "connected",
                    "redis": "connected"
                }
            }
        }
    }
)
async def health_check() -> HealthStatus:
    """
    Perform a comprehensive health check on the API and dependencies.
    
    **Checked Components:**
    - MLflow Model Registry connectivity
    - PostgreSQL database connectivity
    - Redis cache connectivity
    
    **Returns:**
    - `healthy`: All services connected
    - `degraded`: Some services unavailable
    - `unhealthy`: Critical service down
    """
    logger.info("Health check requested")
    
    services: Dict[str, str] = {}
    
    # Check each service
    services["mlflow"] = check_mlflow()
    services["postgres"] = check_postgres()
    services["redis"] = check_redis()
    
    # Determine overall status
    disconnected_count = sum(1 for s in services.values() if s == "disconnected")
    
    if disconnected_count == 0:
        status_value = "healthy"
    elif disconnected_count < 2:
        status_value = "degraded"
    else:
        status_value = "unhealthy"
        logger.warning(f"Health check failed - unhealthy status: {services}")
    
    return HealthStatus(
        status=status_value,
        version="3.0.0",
        timestamp=datetime.now(),
        services=services
    )

