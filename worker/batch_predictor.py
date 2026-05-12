import sys
sys.path.insert(0, '/app')

from celery import Task
from worker.celery_app import app
import pandas as pd
import mlflow
import mlflow.pyfunc
import redis
import json
from typing import List, Dict
from shared.config import MODEL_NAME, MLFLOW_TRACKING_URI, REDIS_URL
from trainer.features import prepare
from shared.logging import setup_logging

logger = setup_logging("batch_predictor")


def infer(model, df):
    pred = model.predict(df)[0]
    prob = 0.5
    try:
        if hasattr(model, 'predict_proba'):
            prob = model.predict_proba(df)[0][1]
        elif hasattr(model, '_model_impl') and hasattr(model._model_impl, 'predict_proba'):
            prob = model._model_impl.predict_proba(df)[0][1]
        elif hasattr(model, 'sk_model') and hasattr(model.sk_model, 'predict_proba'):
            prob = model.sk_model.predict_proba(df)[0][1]
        else:
            prob = float(pred)
    except Exception as e:
        logger.warning(f"Could not get probability, using prediction as probability: {e}")
        prob = float(pred)
    
    return int(pred), float(prob)


class BatchPredictionTask(Task):
    _model = None
    _columns = None
    _redis_client = None

    def get_model(self):
        if self._model is None:
            mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
            self._model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}/Production")
            logger.info("Batch prediction model loaded")
        return self._model

    def get_columns(self):
        if self._columns is None:
            try:
                client = mlflow.tracking.MlflowClient()
                latest = client.get_latest_versions(MODEL_NAME, stages=["Production"])[0]
                import tempfile
                import joblib
                tmp_dir = tempfile.mkdtemp()
                artifact_path = client.download_artifacts(latest.run_id, "columns.pkl", tmp_dir)
                self._columns = joblib.load(artifact_path)
                logger.info(f"Feature columns loaded for batch prediction: {len(self._columns)} columns")
            except Exception as e:
                logger.error(f"Failed to load columns: {e}")
                self._columns = None
        return self._columns

    def get_redis(self):
        if self._redis_client is None:
            try:
                self._redis_client = redis.from_url(REDIS_URL, decode_responses=True)
                self._redis_client.ping()
                logger.info(f"Redis connection established in worker at {REDIS_URL}")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}")
                self._redis_client = None
        return self._redis_client


@app.task(base=BatchPredictionTask, bind=True, name="batch_predict")
def batch_predict(self, data: List[Dict], batch_id: str = None):
    logger.info(f"Batch prediction started for {len(data)} records, batch_id: {batch_id}")

    df = pd.DataFrame(data)
    logger.info(f"Input data shape: {df.shape}")

    model = self.get_model()
    columns = self.get_columns()

    if columns is None:
        logger.error("Columns is None - cannot proceed")
        return {"error": "Model columns not loaded (None)", "batch_id": batch_id}

    if len(columns) == 0:
        logger.error("Columns has zero length - cannot proceed")
        return {"error": "Model columns not loaded (empty)", "batch_id": batch_id}

    logger.info(f"Columns loaded successfully, {len(columns)} features")

    try:
        X = prepare(df, training=False, columns=columns)
        logger.info(f"Features prepared, shape: {X.shape}")

        predictions = []
        probabilities = []

        for idx in range(len(X)):
            row_df = X.iloc[[idx]]
            pred, prob = infer(model, row_df)
            predictions.append(pred)
            probabilities.append(prob)

            try:
                from shared.retrain_queue import RetrainQueueManager
                queue_manager = RetrainQueueManager()
                features = data[idx] if idx < len(data) else {}
                queue_manager.add_prediction(features, int(pred), float(prob))
            except Exception as e:
                logger.warning(f"Failed to save prediction to retrain queue: {e}")

        logger.info(f"Predictions completed for all records")

        # Prepare results
        results = []
        for i, (pred, prob) in enumerate(zip(predictions, probabilities)):
            results.append({
                "index": i,
                "prediction": int(pred),
                "probability": float(prob),
                "original_data": data[i] if i < len(data) else {}
            })

        # Save batch results
        redis_client = self.get_redis()
        import datetime
        if redis_client and batch_id:
            result_data = {
                "batch_id": batch_id,
                "total": len(results),
                "results": results,
                "timestamp": datetime.datetime.now().isoformat()
            }
            redis_client.setex(
                f"batch_results:{batch_id}",
                86400,
                json.dumps(result_data)
            )
            logger.info(f"Batch results stored in Redis with key: batch_results:{batch_id}")

        # Summary
        pred_series = pd.Series(predictions)
        summary = {
            "batch_id": batch_id,
            "total_records": len(results),
            "churn_predictions": int(pred_series.sum()),
            "no_churn_predictions": int(len(predictions) - pred_series.sum()),
            "churn_rate": float(pred_series.mean()),
            "average_churn_probability": float(sum(probabilities) / len(probabilities)) if probabilities else 0
        }

        logger.info(f"Batch prediction completed: {summary}")

        return {
            "status": "success",
            "summary": summary,
            "results": results if len(results) <= 100 else results[:100],
            "total_results": len(results)
        }

    except Exception as e:
        logger.error(f"Error during batch prediction: {e}", exc_info=True)
        return {"error": str(e), "batch_id": batch_id}


@app.task(name="get_batch_results")
def get_batch_results(batch_id: str):
    try:
        redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        results = redis_client.get(f"batch_results:{batch_id}")
        if results:
            return json.loads(results)
        else:
            return {"error": "Batch not found or expired", "batch_id": batch_id}
    except Exception as e:
        return {"error": str(e), "batch_id": batch_id}