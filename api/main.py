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
from datetime import datetime, date
from decimal import Decimal
import json

from api.auth import get_role_from_api_key
from api.rate_limiter import get_rate_limiter, get_real_client_ip
from api.routers import inference, models, feedback, drift, monitoring
from api.schemas import ErrorResponse
from shared.logging import setup_logging
from shared.metrics import REQUESTS, REQUEST_DURATION, start_system_metrics_collector, RETRAIN_QUEUE_LENGTH

logger = setup_logging("api")
executor = ThreadPoolExecutor(max_workers=2)


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)


def _serialize_error_response(error_response: ErrorResponse) -> dict:
    if hasattr(error_response, 'model_dump'):
        return error_response.model_dump()
    return error_response.dict()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting MLOps Platform API v3.0")
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
    description="""
    # MLOps Platform API for Customer Churn Prediction
    
    This API provides endpoints for:
    - **Real-time and batch predictions** for customer churn
    - **Model management** including deployment and retraining
    - **Feedback collection** for model improvement
    - **Drift detection** to monitor data quality
    - **System monitoring** for operational health
    
    ## Authentication
    
    All endpoints except health checks require an API key in the `X-API-Key` header.
    
    ### Available API Keys:
    - **Admin**: Full access (read, write, retrain, batch, admin)
    - **User**: Standard access (read, write, batch)
    - **Readonly**: Read-only access (read)
    
    ## Rate Limits
    - Admin: 1000 requests per minute
    - User: 100 requests per minute
    - Readonly: 50 requests per minute
    - Anonymous: 10 requests per minute
    
    ## Response Format
    All responses are in JSON format. Errors follow a consistent structure:
    ```json
    {
        "error": "Error message",
        "error_code": "ERROR_CODE",
        "details": {},
        "timestamp": "2024-01-15T10:30:00Z"
    }
    ```
    """,
    version="4.3.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Register routers with clean, logical structure
app.include_router(inference.router, prefix="/inference")
app.include_router(models.router, prefix="/models")
app.include_router(feedback.router, prefix="/feedback")
app.include_router(drift.router, prefix="/drift")
app.include_router(monitoring.router, prefix="/monitoring")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================
# Middlewares
# ============================================

@app.middleware("http")
async def tracing_middleware(request: Request, call_next):
    """Add trace_id to every request for distributed tracing"""
    trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
    request.state.trace_id = trace_id
    response = await call_next(request)
    response.headers["X-Trace-ID"] = trace_id
    return response


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    public_paths = [
        "/health", "/docs", "/redoc", "/openapi.json", "/",
        "/monitoring/health", "/monitoring/ready", "/monitoring/metrics"
    ]
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
    # Normalize paths for metrics
    normalized_path = re.sub(r'/batch/[^/]+', '/batch/{batch_id}', path)
    normalized_path = re.sub(r'/feedback/[^/]+', '/feedback/{prediction_id}', normalized_path)
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        REQUESTS.labels(
            method=request.method, 
            endpoint=normalized_path, 
            status=str(response.status_code)
        ).inc()
        REQUEST_DURATION.labels(method=request.method, endpoint=normalized_path).observe(duration)
        return response
    except Exception:
        duration = time.time() - start_time
        REQUESTS.labels(method=request.method, endpoint=normalized_path, status="500").inc()
        REQUEST_DURATION.labels(method=request.method, endpoint=normalized_path).observe(duration)
        raise


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
    start_time = time.time()
    client_ip = get_real_client_ip(request)
    
    logger.info(
        "Request started",
        extra={
            "trace_id": trace_id,
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
                "trace_id": trace_id,
                "status_code": response.status_code,
                "duration_ms": duration_ms
            }
        )
        return response
    except Exception as e:
        logger.error(
            "Request failed",
            exc_info=True,
            extra={"trace_id": trace_id, "error": str(e)}
        )
        raise


# ============================================
# Exception Handlers
# ============================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    trace_id = getattr(request.state, "trace_id", str(uuid.uuid4()))
    
    if exc.status_code >= 500:
        logger.error(f"HTTP {exc.status_code}: {exc.detail}", extra={"trace_id": trace_id})
        error_response = ErrorResponse(
            error="Internal server error",
            error_code="INTERNAL_ERROR",
            details={"trace_id": trace_id},
            timestamp=datetime.now()
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=json.loads(json.dumps(_serialize_error_response(error_response), cls=CustomJSONEncoder))
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "trace_id": trace_id}
    )


# ============================================
# Root Endpoints
# ============================================

@app.get("/", tags=["Root"])
async def root():
    return {
        "message": "MLOps Platform API",
        "version": "4.3.0",
        "documentation": "/docs",
        "redoc": "/redoc",
        "openapi": "/openapi.json",
        "endpoints": {
            "inference": "/inference",
            "models": "/models",
            "feedback": "/feedback",
            "drift": "/drift",
            "monitoring": "/monitoring"
        }
    }


@app.get("/health", tags=["Root"])
async def quick_health():
    """Quick health check for load balancers"""
    return {"status": "healthy", "version": "4.3.0"}


# ============================================
# OpenAPI Customization
# ============================================

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
            "name": "X-API-Key",
            "description": "API key for authentication. Use: admin-secret-key, user-secret-key, or readonly-secret-key"
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