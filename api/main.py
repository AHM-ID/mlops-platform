import time
import tempfile

import pandas as pd
import joblib
import mlflow
import mlflow.pyfunc
import redis
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import Response
from prometheus_client import Counter, generate_latest

from shared.config import MODEL_NAME, MLFLOW_TRACKING_URI, REDIS_URL
from trainer.features import prepare
from api.predictor import infer
from shared.logging import setup_logging
from shared.validator import CustomerData
from shared.feature_store import get_cached_features, cache_features, get_cache_stats


logger = setup_logging("api")

app = FastAPI(
    title="MLOps Platform – Customer Churn Prediction",
    description="Predict whether a customer will churn based on their account information and service usage.",
    version="2.0.0",
    root_path="/api"
)

REQ = Counter("prediction_requests_total", "Total prediction requests")

# Initialize Redis for tracking
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
except:
    redis_client = None

@app.on_event("startup")
def load_model():
    logger.info("Loading model from MLflow")

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    try:
        # Load model from registry
        app.state.model = mlflow.pyfunc.load_model(
            f"models:/{MODEL_NAME}/Production"
        )

        # Load artifacts
        client = mlflow.tracking.MlflowClient()
        latest = client.get_latest_versions(MODEL_NAME, stages=["Production"])[0]

        tmp_dir = tempfile.mkdtemp()
        artifact_path = client.download_artifacts(
            latest.run_id,
            "columns.pkl",
            tmp_dir
        )

        app.state.cols = joblib.load(artifact_path)
        app.state.model_loaded = True

        logger.info("Model and artifacts loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        app.state.model_loaded = False


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    logger.info(
        "Request processed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2)
        }
    )

    return response


@app.get("/health")
def health():
    if not hasattr(app.state, "model_loaded") or not app.state.model_loaded:
        return {"status": "model not loaded — run trainer first"}
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")


@app.get("/metrics/cache")
def cache_metrics():
    """Get cache performance statistics"""
    return get_cache_stats()


@app.post("/predict")
async def predict(payload: CustomerData):
    """Predict customer churn with validation and caching"""
    
    start_time = time.time()
    REQ.inc()
    
    # Convert to DataFrame
    df = pd.DataFrame([payload.dict()])
    logger.info(f"Prediction request received for tenure={payload.tenure}, contract={payload.Contract}")
    
    # Try to get from cache
    cached_X = get_cached_features(df)
    
    if cached_X is not None:
        logger.info("Using cached features")
        X = cached_X
    else:
        # Prepare features (no caching)
        X = prepare(df, training=False, columns=app.state.cols)
        # Cache for future use
        cache_features(df, X, ttl=3600)
    
    # Make prediction
    pred, prob = infer(app.state.model, X)
    
    # Track prediction stats in Redis
    if redis_client:
        redis_client.incr("total_predictions")
        current_avg = float(redis_client.get("avg_confidence") or 0)
        total = int(redis_client.get("total_predictions") or 1)
        new_avg = ((current_avg * (total - 1)) + prob) / total
        redis_client.set("avg_confidence", new_avg)
        
        # Track churn rate
        churn_count = int(redis_client.get("churn_count") or 0)
        if pred == 1:
            redis_client.incr("churn_count")
            churn_count += 1
        redis_client.set("churn_rate", churn_count / total)
    
    duration = time.time() - start_time
    logger.info(f"Prediction completed in {duration:.3f}s: prediction={pred}, probability={prob:.3f}")
    
    return {
        "prediction": pred,
        "probability": prob,
        "processing_time_ms": round(duration * 1000, 2)
    }