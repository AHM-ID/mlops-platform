import os
import uuid
import time
import threading
import mlflow
import mlflow.pyfunc
import pandas as pd
from typing import Tuple, Optional
from api.schemas import PredictionRequest
from shared.config import MODEL_NAME, MLFLOW_TRACKING_URI, CACHE_TTL_SECONDS, COLUMNS_FILE, get_redis_client
from shared.metrics import PREDICTION_LATENCY, MODEL_ACTIVE_VERSION, MODEL_AUC_SCORE, PREDICTION_OUTCOME_TOTAL
from shared.logging import setup_logging
from shared.feature_store import get_or_prepare_features
import joblib
import tempfile

logger = setup_logging("prediction_service")

class PredictionService:
    def __init__(self):
        self._model = None
        self._columns = None
        self._model_version = None
        self._redis_client = None
        self._last_version_check = 0
        self._version_check_interval = 60
        if os.getenv("TESTING", "false").lower() != "true":
            self._load_model()
            self._start_background_version_check()
        else:
            logger.info("Running in test mode, model loading skipped")

    @property
    def redis_client(self):
        if self._redis_client is None and os.getenv("TESTING", "false").lower() != "true":
            self._redis_client = get_redis_client()
        return self._redis_client

    def _start_background_version_check(self):
        def check_loop():
            while True:
                time.sleep(self._version_check_interval)
                try:
                    self._check_and_reload_if_needed()
                except Exception as e:
                    logger.warning(f"Background version check failed: {e}")
        thread = threading.Thread(target=check_loop, daemon=True)
        thread.start()
        logger.info("Background model version checker started")

    def _get_latest_version_from_mlflow(self) -> Optional[str]:
        try:
            client = mlflow.tracking.MlflowClient()
            latest = client.get_latest_versions(MODEL_NAME, stages=["Production"])
            if latest:
                return str(latest[0].version)
        except Exception as e:
            logger.warning(f"Failed to get latest model version: {e}")
        return None

    def _check_and_reload_if_needed(self) -> bool:
        latest_version = self._get_latest_version_from_mlflow()
        if latest_version and latest_version != self._model_version:
            logger.info(f"Model version changed from {self._model_version} to {latest_version}. Reloading...")
            self._load_model()
            return True
        return False

    def _load_model(self):
        try:
            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
            self._model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}/Production")
            client = mlflow.tracking.MlflowClient()
            latest = client.get_latest_versions(MODEL_NAME, stages=["Production"])
            if not latest:
                raise RuntimeError(f"No production model found for {MODEL_NAME}")
            self._model_version = str(latest[0].version)
            MODEL_ACTIVE_VERSION.set(float(self._model_version))
            run = client.get_run(latest[0].run_id)
            auc = run.data.metrics.get('auc', run.data.metrics.get('roc_auc', run.data.metrics.get('AUC', 0)))
            MODEL_AUC_SCORE.set(auc)
            tmp_dir = tempfile.mkdtemp()
            artifact_path = client.download_artifacts(latest[0].run_id, COLUMNS_FILE, tmp_dir)
            self._columns = joblib.load(artifact_path)
            logger.info(f"Loaded {len(self._columns)} feature columns for inference, model version: {self._model_version}")
        except Exception as e:
            logger.error("Failed to load model from MLflow", exc_info=True,
                         extra={"model_name": MODEL_NAME, "error_type": type(e).__name__})
            raise

    def _request_to_dataframe(self, request: PredictionRequest) -> pd.DataFrame:
        data = {
            "tenure": request.tenure,
            "MonthlyCharges": request.MonthlyCharges,
            "TotalCharges": request.TotalCharges,
            "Contract": request.Contract,
            "InternetService": request.InternetService,
            "PaymentMethod": request.PaymentMethod,
        }
        return pd.DataFrame([data])

    def _predict_vectorized(self, X: pd.DataFrame) -> Tuple[int, float]:
        pred = self._model.predict(X)[0]
        probability = 0.5
        try:
            if hasattr(self._model, 'predict_proba'):
                probability = self._model.predict_proba(X)[0][1]
            elif hasattr(self._model, '_model_impl') and hasattr(self._model._model_impl, 'predict_proba'):
                probability = self._model._model_impl.predict_proba(X)[0][1]
            elif hasattr(self._model, 'sk_model') and hasattr(self._model.sk_model, 'predict_proba'):
                probability = self._model.sk_model.predict_proba(X)[0][1]
            else:
                probability = float(pred)
        except Exception as e:
            logger.warning(f"Could not get probability, using prediction as probability: {e}")
            probability = float(pred)
        return int(pred), float(probability)

    def predict(self, request: PredictionRequest) -> Tuple[int, float, str, str]:
        request_id = str(uuid.uuid4())
        start_time = time.perf_counter()
        current_time = time.time()
        if current_time - self._last_version_check > self._version_check_interval:
            self._last_version_check = current_time
            self._check_and_reload_if_needed()
        try:
            df = self._request_to_dataframe(request)
            X = get_or_prepare_features(df, self._model_version, self._columns, CACHE_TTL_SECONDS)
            cache_status = "hit" if X is not None else "miss"
            pred, probability = self._predict_vectorized(X)
            duration_ms = (time.perf_counter() - start_time) * 1000
            PREDICTION_LATENCY.labels(model_version=self._model_version).observe(duration_ms / 1000.0)
            logger.info(
                "Prediction completed",
                extra={
                    "request_id": request_id,
                    "customer_id": request.customer_id,
                    "prediction": pred,
                    "probability": round(probability, 4),
                    "model_version": self._model_version,
                    "cache_status": cache_status,
                    "duration_ms": round(duration_ms, 2)
                }
            )
            self._update_prediction_stats(pred, probability)
            prediction_id = ""
            try:
                from shared.retrain_queue import RetrainQueueManager
                queue = RetrainQueueManager()
                features = df.iloc[0].to_dict()
                prediction_id = queue.add_prediction(
                    features=features,
                    prediction=pred,
                    probability=probability,
                    customer_id=request.customer_id
                )
            except Exception as e:
                logger.warning(f"Failed to save to retrain queue: {e}", extra={"request_id": request_id})
            return pred, probability, self._model_version, prediction_id
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error("Prediction failed", exc_info=True,
                         extra={"request_id": request_id, "customer_id": request.customer_id,
                                "error_type": type(e).__name__, "error_message": str(e),
                                "duration_ms": round(duration_ms, 2)})
            raise

    def _update_prediction_stats(self, prediction: int, probability: float):
        if self.redis_client is None:
            return
        try:
            pipe = self.redis_client.pipeline()
            pipe.incr("total_predictions")
            current_avg = float(self.redis_client.get("avg_confidence") or 0)
            total = int(self.redis_client.get("total_predictions") or 1)
            new_avg = (current_avg * (total - 1) + probability * 100) / total
            pipe.set("avg_confidence", new_avg)
            current_churn = float(self.redis_client.get("churn_rate") or 0)
            new_churn = (current_churn * (total - 1) + prediction) / total
            pipe.set("churn_rate", new_churn)
            pipe.execute()
            PREDICTION_OUTCOME_TOTAL.labels(outcome=str(prediction)).inc()
        except Exception as e:
            logger.warning(f"Failed to update prediction stats: {e}")
