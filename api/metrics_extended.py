from fastapi import APIRouter
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from shared.model_manager import ModelManager
from shared.feature_store import get_cache_stats
import mlflow
from shared.config import MODEL_NAME, MLFLOW_TRACKING_URI
import redis
from shared.config import REDIS_URL
from datetime import datetime, timedelta

router = APIRouter(prefix="/metrics", tags=["metrics"])

# Custom metrics
prediction_duration = Histogram("prediction_duration_seconds", "Time spent processing prediction")
cache_hit_rate = Gauge("cache_hit_rate", "Feature cache hit rate")
model_accuracy = Gauge("model_accuracy", "Current production model accuracy")
model_version = Gauge("model_version", "Current production model version")

@router.get("/detailed")
async def detailed_metrics():
    """Get detailed metrics about models, cache, and predictions"""
    
    model_manager = ModelManager()
    
    # Get model comparison
    model_comparison = model_manager.compare_performance()
    
    # Get cache stats
    cache_stats = get_cache_stats()
    
    # Get MLflow experiment info
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    try:
        experiment = mlflow.get_experiment_by_name("customer_churn")
        experiment_id = experiment.experiment_id if experiment else None
        
        # Get recent runs
        from mlflow.tracking import MlflowClient
        client = MlflowClient()
        recent_runs = client.search_runs(
            experiment_ids=[experiment_id] if experiment_id else [],
            order_by=["start_time DESC"],
            max_results=5
        )
        
        recent_performance = []
        for run in recent_runs:
            recent_performance.append({
                "run_id": run.info.run_id,
                "status": run.info.status,
                "metrics": run.data.metrics,
                "start_time": datetime.fromtimestamp(run.info.start_time / 1000).isoformat()
            })
    except Exception as e:
        recent_performance = []
    
    # Update gauges
    cache_hit_rate.set(cache_stats.get("hit_rate", 0))
    
    # Try to get Redis stats for predictions
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        total_predictions = int(redis_client.get("total_predictions") or 0)
        avg_confidence = float(redis_client.get("avg_confidence") or 0)
    except:
        total_predictions = 0
        avg_confidence = 0
    
    return {
        "models": model_comparison,
        "cache": cache_stats,
        "recent_training_runs": recent_performance,
        "prediction_stats": {
            "total_predictions": total_predictions,
            "average_confidence": avg_confidence,
            "cache_hit_rate": cache_stats.get("hit_rate", 0)
        },
        "system_health": {
            "mlflow": "healthy" if experiment else "unhealthy",
            "redis": "healthy" if cache_stats.get("status") == "active" else "unhealthy",
            "last_updated": datetime.now().isoformat()
        }
    }

@router.get("/model-performance")
async def model_performance():
    """Get all model versions with their performance metrics"""
    model_manager = ModelManager()
    comparison = model_manager.compare_performance()
    
    # Find and update best model's accuracy
    best_auc = 0
    for version, data in comparison.items():
        auc = data["metrics"].get("auc", 0)
        if auc > best_auc:
            best_auc = auc
            model_accuracy.set(auc)
            model_version.set(data["version"])
    
    return comparison