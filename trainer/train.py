import os
import sys
import uuid
import atexit
import time

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
import mlflow
import mlflow.sklearn
import joblib

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

from shared.config import MLFLOW_TRACKING_URI, EXPERIMENT_NAME, MODEL_NAME, DATA_PATH, COLUMNS_FILE
from trainer.features import prepare
from trainer.optimize import search
from trainer.evaluate import metrics
from shared.logging import setup_logging

RUN_ID = str(uuid.uuid4())

def _cleanup_logging():
    """Ensure async log handlers flush before process exit"""
    for handler in logger.logger.handlers[:]:
        if hasattr(handler, 'close'):
            try:
                handler.close()
            except Exception:
                pass
    time.sleep(0.3)

atexit.register(_cleanup_logging)

logger = setup_logging("trainer", extra={'run_id': RUN_ID})

def main():
    try:
        logger.info("Starting training pipeline", extra={"run_id": RUN_ID})
        
        if not os.path.exists("data/churn.csv"):
            logger.error("data/churn.csv not found!", extra={"run_id": RUN_ID})
            return

        df = pd.read_csv(DATA_PATH)
        logger.info(f"Loaded data, shape: {df.shape}", extra={"run_id": RUN_ID, "rows": len(df)})

        X, y, cols = prepare(df, training=True)
        logger.info(f"Prepared features, shape: {X.shape}", extra={"run_id": RUN_ID, "features": len(cols)})

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=42
        )
        logger.info(f"Train/test split: {X_train.shape[0]}/{X_test.shape[0]}", extra={"run_id": RUN_ID})

        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(EXPERIMENT_NAME)

        best = search(X_train, y_train)
        logger.info(f"Best hyperparameters found: {best}", extra={"run_id": RUN_ID})

        with mlflow.start_run() as run:
            model = RandomForestClassifier(**best, n_jobs=-1)
            model.fit(X_train, y_train)
            logger.info("Model training completed", extra={"run_id": RUN_ID, "mlflow_run_id": run.info.run_id})

            pred = model.predict(X_test)
            prob = model.predict_proba(X_test)[:, 1]
            scores = metrics(y_test, pred, prob)
            
            logger.info(
                "Model evaluation completed",
                extra={
                    "run_id": RUN_ID,
                    "mlflow_run_id": run.info.run_id,
                    "accuracy": scores["accuracy"],
                    "precision": scores["precision"],
                    "recall": scores["recall"],
                    "f1": scores["f1"],
                    "auc": scores["auc"]
                }
            )

            mlflow.log_params(best)
            mlflow.log_metrics(scores)

            joblib.dump(cols, COLUMNS_FILE)
            mlflow.log_artifact(COLUMNS_FILE)

            mlflow.sklearn.log_model(model, "model", registered_model_name=MODEL_NAME)
            logger.info(f"Model registered as {MODEL_NAME} in MLflow", extra={"run_id": RUN_ID})

            client = mlflow.tracking.MlflowClient()
            latest_version = client.get_latest_versions(MODEL_NAME, stages=["None"])[0].version
            client.transition_model_version_stage(MODEL_NAME, int(latest_version), "Production")
            logger.info(
                f"Model version {latest_version} promoted to Production",
                extra={"run_id": RUN_ID, "model_version": latest_version}
            )

        logger.info("Training pipeline finished successfully", extra={"run_id": RUN_ID})
        
    except Exception as e:
        logger.error(
            "Training pipeline failed",
            exc_info=True,
            extra={
                "run_id": RUN_ID,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )
        sys.exit(1)

if __name__ == "__main__":
    main()