from typing import Tuple
import uuid
import time
import mlflow
import mlflow.pyfunc
import pandas as pd
from api.schemas import PredictionRequest
from trainer.features import prepare
from shared.config import MODEL_NAME, MLFLOW_TRACKING_URI, REDIS_URL, CACHE_TTL_SECONDS, COLUMNS_FILE
from shared.metrics import PREDICTION_LATENCY, MODEL_ACTIVE_VERSION, MODEL_AUC_SCORE, PREDICTION_OUTCOME_TOTAL
from shared.logging import setup_logging
from shared.feature_store import get_cached_features, cache_features, get_feature_hash
import redis

logger = setup_logging("prediction_service")


class PredictionService:

    def __init__(self):
        self._model = None
        self._columns = None
        self._model_version = None
        self._load_model()

    def _load_model(self):
        try:
            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
            self._model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}/Production")
            
            client = mlflow.tracking.MlflowClient()
            latest = client.get_latest_versions(MODEL_NAME, stages=["Production"])[0]
            self._model_version = str(latest.version)
        
            MODEL_ACTIVE_VERSION.set(float(self._model_version))

            run = client.get_run(latest.run_id)
            auc = run.data.metrics.get('auc', 
                run.data.metrics.get('roc_auc', 
                run.data.metrics.get('AUC', 0)))
            MODEL_AUC_SCORE.set(auc)
            
            if auc == 0:
                logger.warning(f"AUC metric not found in run {latest.run_id}. Available metrics: {list(run.data.metrics.keys())}")
        except Exception as e:
            logger.error(
                "Failed to load model from MLflow",
                exc_info=True,
                extra={
                    "model_name": MODEL_NAME,
                    "error_type": type(e).__name__
                }
            )
            raise

    def _load_columns(self):
        """Load feature columns from MLflow artifacts (cached in memory)"""
        if self._columns is not None:
            return self._columns
        try:
            import tempfile
            import joblib
            client = mlflow.tracking.MlflowClient()
            latest = client.get_latest_versions(MODEL_NAME, stages=["Production"])[0]
            tmp_dir = tempfile.mkdtemp()
            artifact_path = client.download_artifacts(latest.run_id, COLUMNS_FILE, tmp_dir)
            self._columns = joblib.load(artifact_path)
            logger.info(f"Loaded {len(self._columns)} feature columns for inference")
            return self._columns
        except Exception as e:
            logger.warning(f"Could not load columns.pkl: {e}")
            return None

    def predict(self, request: PredictionRequest) -> Tuple[int, float, str]:
        request_id = str(uuid.uuid4())
        start_time = time.time()
        
        try:
            self._load_columns()
            
            data = {
                "tenure": request.tenure,
                "MonthlyCharges": request.MonthlyCharges,
                "TotalCharges": request.TotalCharges,
                "Contract": request.Contract,
                "InternetService": request.InternetService,
                "PaymentMethod": request.PaymentMethod,
            }
            
            df = pd.DataFrame([data])
            
            X = get_cached_features(df)
            cache_status = "hit" if X is not None else "miss"
            
            if X is None:
                X = prepare(df, training=False, columns=self._columns)
                cache_features(df, X, ttl=CACHE_TTL_SECONDS)
            
            pred = self._model.predict(X)[0]
            probability = 0.5
            try:
                if hasattr(self._model, 'predict_proba'):
                    probability = self._model.predict_proba(X)[0][1]
                elif hasattr(self._model, '_model_impl') and hasattr(self._model._model_impl, 'predict_proba'):
                    probability = self._model._model_impl.predict_proba(X)[0][1]
            except Exception as e:
                logger.warning(f"Could not get probability: {e}", extra={"request_id": request_id})
            
            duration_ms = (time.time() - start_time) * 1000
            PREDICTION_LATENCY.labels(model_version=self._model_version).observe(duration_ms / 1000.0)
            
            logger.info(
                "Prediction completed",
                extra={
                    "request_id": request_id,
                    "customer_id": request.customer_id,
                    "prediction": int(pred),
                    "probability": round(probability, 4),
                    "model_version": self._model_version,
                    "cache_status": cache_status,
                    "duration_ms": round(duration_ms, 2)
                }
            )
            
            self.update_prediction_stats(pred, probability)
            
            try:
                from shared.retrain_queue import RetrainQueueManager
                queue = RetrainQueueManager()
                queue.add_prediction(data, int(pred), float(probability))
            except Exception as e:
                logger.warning(
                    f"Failed to save prediction to retrain queue: {e}",
                    extra={"request_id": request_id}
                )
            
            return int(pred), float(probability), self._model_version

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.error(
                "Prediction failed",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "customer_id": request.customer_id,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "duration_ms": round(duration_ms, 2)
                }
            )
            raise

    def update_prediction_stats(self, prediction: int, probability: float):
        try:
            redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            redis_client.incr("total_predictions")
            
            PREDICTION_OUTCOME_TOTAL.labels(outcome=str(prediction)).inc()
            
            current_avg = float(redis_client.get("avg_confidence") or 0)
            total = int(redis_client.get("total_predictions") or 1)
            new_avg = (current_avg * (total - 1) + probability * 100) / total
            redis_client.set("avg_confidence", new_avg)
            
            current_churn = float(redis_client.get("churn_rate") or 0)
            new_churn = (current_churn * (total - 1) + prediction) / total
            redis_client.set("churn_rate", new_churn)
            
        except Exception as e:
            logger.warning(f"Failed to update prediction stats: {e}")