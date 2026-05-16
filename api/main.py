import re
import uuid
import time
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from fastapi import Request
import asyncio
from shared.retrain_queue import RetrainQueueManager

from api.auth import get_role_from_api_key
from api.rate_limiter import get_rate_limiter
from api.routers import (
    health,
    predictions,
    models,
    batch_jobs,
    monitoring
)
from api.routers.retrains import router as retrain_router
from api.routers.retrain_queue import router as retrain_queue_router

from api.routers.monitoring import metrics_collector
from shared.logging import setup_logging
from shared.metrics import REQUESTS, REQUEST_DURATION, ACTIVE_REQUESTS, start_system_metrics_collector, RETRAIN_QUEUE_LENGTH
from shared.feature_store import update_cache_hit_rate

logger = setup_logging("api")

executor = ThreadPoolExecutor(max_workers=2)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MLOps Platform API")
    start_system_metrics_collector()
    
    # Initialize queue manager once, reuse connection
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
    
    # Graceful shutdown
    logger.info("Shutting down MLOps Platform API")
    queue_task.cancel()
    try:
        await queue_task
    except asyncio.CancelledError:
        pass
    executor.shutdown(wait=False)


# Initialize FastAPI app
app = FastAPI(
    title="MLOps Platform API",
    description="Comprehensive API for ML Model Management and Predictions with Authentication and Rate Limiting",
    version="3.0.0",
    docs_url="/docs", 
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """
    Authentication middleware - extracts and validates API key, sets role in request state.
    Public endpoints (health, docs, metrics) are excluded from authentication.
    """
    # Public endpoints that don't require authentication
    public_paths = ["/health", "/docs", "/redoc", "/openapi.json", "/", "/monitoring/metrics"]
    
    if any(request.url.path.startswith(path) for path in public_paths):
        request.state.role = "anonymous"
        response = await call_next(request)
        return response
    
    # Extract API key from header
    api_key = request.headers.get("X-API-Key")
    
    if api_key:
        role = get_role_from_api_key(api_key)
        if role:
            request.state.role = role
        else:
            request.state.role = "anonymous"
    else:
        request.state.role = "anonymous"
    
    response = await call_next(request)
    return response

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Rate limiting middleware - checks rate limits before processing request."""
    limiter = get_rate_limiter()
    api_key = request.headers.get("X-API-Key", "")
    identifier = api_key if api_key else request.client.host
    role = getattr(request.state, "role", "anonymous")
    
    # Check rate limit (raises HTTPException if exceeded)
    rate_info = limiter.check_rate_limit(identifier, role)
    request.state.rate_limit_info = rate_info
    
    response = await call_next(request)
    
    # Add rate limit headers to response
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
        
        # Prometheus Client
        REQUESTS.labels(method=request.method, endpoint=normalized_path, status=str(response.status_code)).inc()
        REQUEST_DURATION.labels(method=request.method, endpoint=normalized_path).observe(duration)
        
        # In-memory collector
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
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    start_time = time.time()
    
    logger.info(
        "Request started",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "client_ip": request.client.host
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

app.include_router(
    health.router,
    tags=["Health"]
)

app.include_router(
    predictions.router,
    prefix="/predictions",
    tags=["Predictions"]
)

app.include_router(
    models.router,
    prefix="/models",
    tags=["Model Management"]
)

app.include_router(
    batch_jobs.router,
    prefix="/batch",
    tags=["Batch Processing"]
)

app.include_router(
    monitoring.router,
    prefix="/monitoring",
    tags=["Monitoring & Metrics"]
)

app.include_router(
    retrain_router,
    tags=["Model Retraining"]
)

app.include_router(
    retrain_queue_router,
    tags=["Model Retraining"]
)


@app.get("/", tags=["Root"])
async def root():
    """API root endpoint with documentation links"""
    return {
        "message": "MLOps Platform API",
        "version": "3.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json"
    }


@app.get("/health", tags=["Health"])
async def quick_health():
    """Quick health check"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )