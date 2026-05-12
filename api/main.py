"""
MLOps Platform API
Main entry point with FastAPI and Swagger documentation
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

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

logger = setup_logging("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage API lifecycle"""
    logger.info("Starting MLOps Platform API")
    yield
    logger.info("Shutting down MLOps Platform API")


# Initialize FastAPI app
app = FastAPI(
    title="MLOps Platform API",
    description=""" Comprehensive API for ML Model Management and Predictions """,
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

from fastapi import Request
import time

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000
        
        if "/metrics" not in request.url.path:
            metrics_collector.record_request(
                success=response.status_code < 400,
                response_time_ms=duration_ms
            )
        
        return response
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        metrics_collector.record_request(success=False, response_time_ms=duration_ms)
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