"""
Monitoring Router
Provides metrics, health monitoring, and system observability endpoints
"""

from fastapi import APIRouter, HTTPException, status, Response
from datetime import datetime
import psutil
import os
from prometheus_client import (
    Counter, Histogram, Gauge, generate_latest, 
    CollectorRegistry, multiprocess
)

from api.schemas import (
    APIMetrics,
    SystemHealth,
)
from shared.logging import setup_logging

logger = setup_logging("monitoring_router")

router = APIRouter()

def get_registry():
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    return registry

REQUESTS = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('api_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
ACTIVE_REQUESTS = Gauge('api_active_requests', 'Active requests')

class MetricsCollector:
    def __init__(self):
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.total_response_time_ms = 0.0
    
    def record_request(self, success: bool, response_time_ms: float):
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        self.total_response_time_ms += response_time_ms
    
    def get_metrics(self) -> APIMetrics:
        error_rate = (self.failed_requests / self.total_requests 
                      if self.total_requests > 0 else 0)
        avg_response_time = (self.total_response_time_ms / self.total_requests 
                            if self.total_requests > 0 else 0)
        
        uptime_seconds = 3600
        rps = self.total_requests / uptime_seconds if uptime_seconds > 0 else 0
        
        return APIMetrics(
            total_requests=self.total_requests,
            successful_requests=self.successful_requests,
            failed_requests=self.failed_requests,
            error_rate=error_rate,
            average_response_time_ms=avg_response_time,
            requests_per_second=rps
        )

metrics_collector = MetricsCollector()

@router.get("/metrics/prometheus")
async def prometheus_metrics():
    return Response(content=generate_latest(), media_type="text/plain")

@router.get("/metrics", response_model=APIMetrics, status_code=status.HTTP_200_OK)
async def get_metrics() -> APIMetrics:
    logger.info("Metrics requested")
    return metrics_collector.get_metrics()

@router.get("/health/system", response_model=SystemHealth, status_code=status.HTTP_200_OK)
async def get_system_health() -> SystemHealth:
    try:
        logger.info("System health check requested")
        
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        mlflow_ok = True
        postgres_ok = True
        redis_ok = True
        
        try:
            import mlflow
            from shared.config import MLFLOW_TRACKING_URI
            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
            mlflow.search_experiments(max_results=1)
        except Exception as e:
            logger.warning(f"MLflow check failed: {e}")
            mlflow_ok = False
        
        try:
            import psycopg2
            from shared.config import POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
            conn = psycopg2.connect(
                host=POSTGRES_HOST,
                port=POSTGRES_PORT,
                user=POSTGRES_USER,
                password=POSTGRES_PASSWORD,
                database=POSTGRES_DB,
                connect_timeout=5
            )
            conn.close()
        except Exception as e:
            logger.warning(f"PostgreSQL check failed: {e}")
            postgres_ok = False
        
        try:
            import redis
            from shared.config import REDIS_URL
            r = redis.from_url(REDIS_URL, socket_connect_timeout=5)
            r.ping()
        except Exception as e:
            logger.warning(f"Redis check failed: {e}")
            redis_ok = False
        
        if cpu_percent > 80 or memory.percent > 85 or disk.percent > 90:
            overall_status = "degraded"
        elif not all([mlflow_ok, postgres_ok, redis_ok]):
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        return SystemHealth(
            status=overall_status,
            timestamp=datetime.now(),
            mlflow_connected=mlflow_ok,
            postgres_connected=postgres_ok,
            redis_connected=redis_ok,
            disk_usage_percent=disk.percent,
            memory_usage_percent=memory.percent,
            cpu_usage_percent=cpu_percent
        )
    
    except Exception as e:
        logger.error(f"System health check failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to collect system health information"
        )
    
@router.delete(
    "/cache",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear Feature Cache",
    description="Clear all cached features from Redis"
)
async def clear_feature_cache():
    try:
        from shared.feature_store import clear_cache
        clear_cache()
        logger.info("Feature cache cleared")
        return None
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )
    
@router.get(
    "/prediction-stats",
    status_code=status.HTTP_200_OK,
    summary="Prediction Statistics",
    description="Get real-time prediction statistics from Redis"
)
async def get_prediction_stats():
    try:
        import redis
        from shared.config import REDIS_URL
        
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        
        total_predictions = int(redis_client.get("total_predictions") or 0)
        avg_confidence = float(redis_client.get("avg_confidence") or 0)
        churn_rate = float(redis_client.get("churn_rate") or 0)
        
        return {
            "total_predictions": total_predictions,
            "average_confidence": avg_confidence,
            "churn_rate": churn_rate,
            "last_updated": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get prediction stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get prediction stats: {str(e)}"
        )