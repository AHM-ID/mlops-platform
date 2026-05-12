"""
Prediction Service
Business logic for single predictions
"""

from typing import Tuple
import mlflow
import mlflow.pyfunc
import pandas as pd
from api.schemas import PredictionRequest
from trainer.features import prepare
from shared.config import MODEL_NAME, MLFLOW_TRACKING_URI
from shared.logging import setup_logging

logger = setup_logging("prediction_service")


class PredictionService:
    """Service for handling model predictions"""

    def __init__(self):
        self._model = None
        self._columns = None
        self._model_version = None
        self._load_model()

    def _load_model(self):
        """Load model from MLflow"""
        try:
            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
            self._model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}/Production")
            logger.info(f"Model loaded: {MODEL_NAME}/Production")

            client = mlflow.tracking.MlflowClient()
            latest = client.get_latest_versions(MODEL_NAME, stages=["Production"])[0]
            self._model_version = str(latest.version)
            logger.info(f"Model version: {self._model_version}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def _load_columns(self):
        """Load feature columns from MLflow artifacts"""
        if self._columns is not None:
            return self._columns
        try:
            import tempfile
            import joblib
            client = mlflow.tracking.MlflowClient()
            latest = client.get_latest_versions(MODEL_NAME, stages=["Production"])[0]
            tmp_dir = tempfile.mkdtemp()
            artifact_path = client.download_artifacts(
                latest.run_id, "columns.pkl", tmp_dir
            )
            self._columns = joblib.load(artifact_path)
            logger.info(f"Loaded {len(self._columns)} feature columns")
            return self._columns
        except Exception as e:
            logger.warning(f"Could not load columns.pkl: {e}")
            return None

    def predict(self, request: PredictionRequest) -> Tuple[int, float, str]:
        """Make prediction and automatically save to retrain queue"""
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
            X = prepare(df, training=False, columns=self._columns)

            # Inference
            pred = self._model.predict(X)[0]
            probability = 0.5
            try:
                if hasattr(self._model, 'predict_proba'):
                    probability = self._model.predict_proba(X)[0][1]
                elif hasattr(self._model, '_model_impl') and hasattr(self._model._model_impl, 'predict_proba'):
                    probability = self._model._model_impl.predict_proba(X)[0][1]
            except Exception as e:
                logger.warning(f"Could not get probability: {e}")

            # Update stats
            self.update_prediction_stats(pred, probability)

            # === Save to Retrain Queue (Automatic) ===
            try:
                from shared.retrain_queue import RetrainQueueManager
                queue = RetrainQueueManager()
                queue.add_prediction(data, int(pred), float(probability))
            except Exception as e:
                logger.warning(f"Failed to save prediction to retrain queue: {e}")

            return int(pred), float(probability), self._model_version

        except Exception as e:
            logger.error(f"Prediction failed: {e}", exc_info=True)
            raise

    def update_prediction_stats(self, prediction: int, probability: float):
        try:
            import redis
            from shared.config import REDIS_URL
            redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            redis_client.incr("total_predictions")
            # Update running averages...
            current_avg = float(redis_client.get("avg_confidence") or 0)
            total = int(redis_client.get("total_predictions") or 1)
            new_avg = (current_avg * (total - 1) + probability * 100) / total
            redis_client.set("avg_confidence", new_avg)

            current_churn = float(redis_client.get("churn_rate") or 0)
            new_churn = (current_churn * (total - 1) + prediction) / total
            redis_client.set("churn_rate", new_churn)
        except Exception as e:
            logger.warning(f"Failed to update stats: {e}")