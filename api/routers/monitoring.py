"""
Monitoring Router - Health, Metrics, System Status

Endpoints:
- GET /monitoring/health      - Simple health check
- GET /monitoring/ready       - Readiness probe
- GET /monitoring/metrics     - Prometheus metrics
- GET /monitoring/system      - System resource usage
- GET /monitoring/prediction-stats - Prediction statistics
- DELETE /monitoring/cache    - Clear feature cache
"""

from fastapi import APIRouter, Response, HTTPException, status
from datetime import datetime
import psutil
import time
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from api.schemas import SystemHealth, APIMetrics, PredictionStats
from shared.logging import setup_logging
from shared.config import UPTIME_MOCK_SECONDS
from shared.metrics import get_registry
from shared.feature_store import update_cache_hit_rate, clear_cache

logger = setup_logging("monitoring_router")
router = APIRouter(tags=["Monitoring"])


# Metrics collector for API metrics
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
        uptime_seconds = UPTIME_MOCK_SECONDS
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
_metrics_cache = {"data": None, "timestamp": 0}


@router.get(
    "/health",
    summary="Health Check",
    description="Simple health check endpoint for load balancers."
)
async def health_check():
    """
    Simple health check.
    
    Example curl:
    ```bash
    curl -X GET "http://localhost:8080/api/monitoring/health"
    ```
    """
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@router.get(
    "/ready",
    summary="Readiness Probe",
    description="Readiness check for Kubernetes/Docker orchestration."
)
async def readiness_check():
    """
    Readiness probe.
    
    Example curl:
    ```bash
    curl -X GET "http://localhost:8080/api/monitoring/ready"
    ```
    """
    # Check dependencies
    import mlflow
    from shared.config import REDIS_URL, MLFLOW_TRACKING_URI, get_redis_client
    
    status = {"ready": True, "checks": {}}
    
    try:
        r = get_redis_client()
        r.ping()
        status["checks"]["redis"] = "ok"
    except Exception as e:
        status["checks"]["redis"] = str(e)
        status["ready"] = False
    
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.search_experiments(max_results=1)
        status["checks"]["mlflow"] = "ok"
    except Exception as e:
        status["checks"]["mlflow"] = str(e)
        status["ready"] = False
    
    return status


@router.get(
    "/metrics",
    summary="Prometheus Metrics",
    description="Prometheus metrics endpoint for scraping."
)
async def prometheus_metrics():
    """
    Prometheus metrics endpoint.
    
    Example curl:
    ```bash
    curl -X GET "http://localhost:8080/api/monitoring/metrics"
    ```
    """
    now = time.time()
    if now - _metrics_cache["timestamp"] < 5:
        return Response(content=_metrics_cache["data"], media_type=CONTENT_TYPE_LATEST)
    
    update_cache_hit_rate()
    metrics_data = generate_latest(get_registry())
    _metrics_cache["data"] = metrics_data
    _metrics_cache["timestamp"] = now
    
    return Response(content=metrics_data, media_type=CONTENT_TYPE_LATEST)


@router.get(
    "/system",
    response_model=SystemHealth,
    summary="System Health",
    description="Get detailed system health including resource usage and dependency status."
)
async def get_system_health() -> SystemHealth:
    """
    Get system health.
    
    Example curl:
    ```bash
    curl -X GET "http://localhost:8080/api/monitoring/system" \\
         -H "X-API-Key: user-secret-key-change-in-production"
    ```
    """
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    # Check dependencies
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
            host=POSTGRES_HOST, port=POSTGRES_PORT,
            user=POSTGRES_USER, password=POSTGRES_PASSWORD,
            database=POSTGRES_DB, connect_timeout=5
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
    
    # Determine overall status
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


@router.get(
    "/prediction-stats",
    response_model=PredictionStats,
    summary="Prediction Statistics",
    description="Get aggregated prediction statistics."
)
async def get_prediction_stats() -> PredictionStats:
    """
    Get prediction statistics.
    
    Example curl:
    ```bash
    curl -X GET "http://localhost:8080/api/monitoring/prediction-stats" \\
         -H "X-API-Key: user-secret-key-change-in-production"
    ```
    """
    try:
        import redis
        from shared.config import REDIS_URL
        
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        
        total_predictions = int(redis_client.get("total_predictions") or 0)
        avg_confidence = float(redis_client.get("avg_confidence") or 0)
        churn_rate = float(redis_client.get("churn_rate") or 0)
        
        return PredictionStats(
            total_predictions=total_predictions,
            average_confidence=avg_confidence,
            churn_rate=churn_rate,
            last_updated=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Failed to get prediction stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete(
    "/cache",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear Feature Cache",
    description="Clear the feature cache to force fresh feature computation."
)
async def clear_feature_cache():
    """
    Clear feature cache.
    
    Example curl:
    ```bash
    curl -X DELETE "http://localhost:8080/api/monitoring/cache" \\
         -H "X-API-Key: admin-secret-key-change-in-production"
    ```
    """
    try:
        clear_cache()
        logger.info("Feature cache cleared")
        return None
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear cache"
        )