import re
import uuid
import time
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
from shared.retrain_queue import RetrainQueueManager
from fastapi.openapi.utils import get_openapi

from api.auth import get_role_from_api_key
from api.rate_limiter import get_rate_limiter, get_real_client_ip
from api.routers import (
    health,
    predictions,
    models,
    batch_jobs,
    labeling,
    drift,
    monitoring
)
from api.routers.retrains import router as retrain_router
from api.routers.retrain_queue import router as retrain_queue_router
from api.routers.monitoring import metrics_collector
from api.schemas import ErrorResponse
from shared.logging import setup_logging
from shared.metrics import REQUESTS, REQUEST_DURATION, start_system_metrics_collector, RETRAIN_QUEUE_LENGTH
from datetime import datetime

logger = setup_logging("api")
executor = ThreadPoolExecutor(max_workers=2)

def _serialize_error_response(error_response: ErrorResponse) -> dict:
    if hasattr(error_response, 'model_dump'):
        return error_response.model_dump()
    return error_response.dict()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MLOps Platform API")
    start_system_metrics_collector()
    queue_manager = RetrainQueueManager()
    async def update_queue_length():
        while True:
            try:
                start_time = time.time()
                queue_length = await asyncio.get_event_loop().run_in_executor(
                    executor, queue_manager.get_queue_length
                )
                elapsed = time.time() - start_time
                logger.debug(f"Queue length query took {elapsed:.3f}s")
                RETRAIN_QUEUE_LENGTH.set(queue_length)
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Failed to update queue length: {e}")
                await asyncio.sleep(60)
    queue_task = asyncio.create_task(update_queue_length())
    yield
    logger.info("Shutting down MLOps Platform API")
    queue_task.cancel()
    try:
        await queue_task
    except asyncio.CancelledError:
        pass
    executor.shutdown(wait=False)

app = FastAPI(
    title="MLOps Platform API",
    description="Comprehensive API for ML Model Management and Predictions with Authentication and Rate Limiting",
    version="3.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.include_router(health.router, tags=["Health"])
app.include_router(predictions.router, prefix="/predictions", tags=["Predictions"])
app.include_router(models.router, prefix="/models", tags=["Model Management"])
app.include_router(batch_jobs.router, prefix="/batch", tags=["Batch Processing"])
app.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring & Metrics"])
app.include_router(retrain_router, tags=["Model Retraining"])
app.include_router(retrain_queue_router, tags=["Model Retraining"])
app.include_router(labeling.router, tags=["Feedback & Labeling"])
app.include_router(drift.router, prefix="/monitoring", tags=["Data Drift Monitoring"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    public_paths = ["/health", "/docs", "/redoc", "/openapi.json", "/", "/monitoring/metrics", "/monitoring/metrics/prometheus", "/health/ready"]
    if any(request.url.path.startswith(path) for path in public_paths):
        request.state.role = "anonymous"
        response = await call_next(request)
        return response
    api_key = request.headers.get("X-API-Key")
    if api_key:
        role = get_role_from_api_key(api_key)
        request.state.role = role if role else "anonymous"
    else:
        request.state.role = "anonymous"
    response = await call_next(request)
    return response

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    limiter = get_rate_limiter()
    real_ip = get_real_client_ip(request)
    api_key = request.headers.get("X-API-Key", "")
    identifier = api_key if api_key else real_ip
    role = getattr(request.state, "role", "anonymous")
    rate_info = limiter.check_rate_limit(identifier, role)
    request.state.rate_limit_info = rate_info
    response = await call_next(request)
    if hasattr(request.state, "rate_limit_info"):
        info = request.state.rate_limit_info
        response.headers["X-RateLimit-Limit"] = str(info.get("limit", 0))
        response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
        response.headers["X-RateLimit-Reset"] = str(info.get("reset_time", 0))
    return response

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    path = request.url.path
    normalized_path = re.sub(r'/api/batch/[^/]+', '/api/batch/{batch_id}', path)
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        REQUESTS.labels(method=request.method, endpoint=normalized_path, status=str(response.status_code)).inc()
        REQUEST_DURATION.labels(method=request.method, endpoint=normalized_path).observe(duration)
        if "/metrics" not in path:
            metrics_collector.record_request(success=response.status_code < 400, response_time_ms=duration*1000)
        return response
    except Exception:
        duration = time.time() - start_time
        REQUESTS.labels(method=request.method, endpoint=normalized_path, status="500").inc()
        REQUEST_DURATION.labels(method=request.method, endpoint=normalized_path).observe(duration)
        metrics_collector.record_request(success=False, response_time_ms=duration*1000)
        raise

@app.middleware("http")
async def tracing_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    start_time = time.time()
    client_ip = get_real_client_ip(request)
    logger.info(
        "Request started",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": client_ip
        }
    )
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            "Request completed",
            extra={
                "request_id": request_id,
                "status_code": response.status_code,
                "duration_ms": duration_ms
            }
        )
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as e:
        logger.error(
            "Request failed",
            exc_info=True,
            extra={
                "request_id": request_id,
                "error": str(e)
            }
        )
        raise

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", str(uuid.uuid4()))
    if exc.status_code >= 500:
        logger.error(f"HTTP {exc.status_code}: {exc.detail}", extra={"request_id": request_id})
        error_response = ErrorResponse(
            error="Internal server error",
            error_code="INTERNAL_ERROR",
            details={"request_id": request_id},
            timestamp=datetime.now()
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_serialize_error_response(error_response)
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "request_id": request_id}
    )

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "MLOps Platform API",
        "version": "3.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json"
    }

@app.get("/health", tags=["Health"])
async def quick_health():
    return {"status": "healthy", "version": "3.0.0"}

@app.get("/health/ready", tags=["Health"])
async def readiness_check():
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

@app.get("/openapi.json", include_in_schema=False)
async def get_custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
        servers=app.servers,
    )
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    openapi_schema["components"]["securitySchemes"] = {
        "APIKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
    if "security" not in openapi_schema:
        openapi_schema["security"] = []
    openapi_schema["security"].append({"APIKeyHeader": []})
    app.openapi_schema = openapi_schema
    return app.openapi_schema

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
