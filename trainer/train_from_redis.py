import os
import sys
import uuid
import atexit
import time
import pandas as pd
import mlflow
import mlflow.sklearn
import joblib
from typing import Tuple

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

from trainer.features import prepare
from trainer.optimize import search
from trainer.evaluate import metrics
from shared.config import MLFLOW_TRACKING_URI, EXPERIMENT_NAME, MODEL_NAME
from shared.retrain_queue import RetrainQueueManager
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

logger = setup_logging("trainer_redis", extra={'run_id': RUN_ID})


def load_data_from_redis() -> Tuple[pd.DataFrame, pd.Series]:
    """Load training data from Redis retrain queue with CSV fallback"""
    try:
        queue_manager = RetrainQueueManager()
        queue_length = queue_manager.get_queue_length()
        
        logger.info(
            "Checking retrain queue",
            extra={
                "run_id": RUN_ID,
                "queue_length": queue_length,
                "source": "redis"
            }
        )
        
        if queue_length == 0:
            logger.info("No training data in Redis, falling back to CSV", extra={"run_id": RUN_ID})
            return load_data_from_csv()
        
        batch = queue_manager.get_training_batch(batch_size=10000)
        if not batch:
            logger.warning("No records retrieved from Redis, falling back to CSV", extra={"run_id": RUN_ID})
            return load_data_from_csv()
        
        records = []
        labeled_count = 0
        for record in batch:
            features = record.get("features", {})
            label = record.get("label")
            if label is not None:
                feature_copy = features.copy()
                feature_copy["Churn"] = "Yes" if label == 1 else "No"
                records.append(feature_copy)
                labeled_count += 1
        
        if not records:
            logger.warning("No valid labeled records found, falling back to CSV", extra={"run_id": RUN_ID})
            return load_data_from_csv()
        
        df = pd.DataFrame(records)
        logger.info(
            "Loaded training data from Redis",
            extra={
                "run_id": RUN_ID,
                "records_loaded": len(df),
                "labeled_count": labeled_count,
                "source": "redis"
            }
        )
        
        y = df["Churn"].map({"Yes": 1, "No": 0})
        X = df.drop(columns=["Churn"])
        return X, y
        
    except Exception as e:
        logger.error(
            "Failed to load data from Redis",
            exc_info=True,
            extra={
                "run_id": RUN_ID,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )
        logger.info("Falling back to CSV", extra={"run_id": RUN_ID})
        return load_data_from_csv()


def load_data_from_csv() -> Tuple[pd.DataFrame, pd.Series]:
    """Load training data from CSV file"""
    try:
        if not os.path.exists("data/churn.csv"):
            logger.error("data/churn.csv not found!", extra={"run_id": RUN_ID})
            raise FileNotFoundError("data/churn.csv not found")
        
        df = pd.read_csv("data/churn.csv")
        logger.info(
            "Loaded data from CSV",
            extra={
                "run_id": RUN_ID,
                "shape": df.shape,
                "source": "csv"
            }
        )
        
        if "customerID" in df.columns:
            df = df.drop(columns=["customerID"])
        
        df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
        df = df.dropna()
        
        y = df["Churn"].map({"Yes": 1, "No": 0})
        X = df.drop(columns=["Churn"])
        return X, y
        
    except Exception as e:
        logger.error(
            "Failed to load data from CSV",
            exc_info=True,
            extra={
                "run_id": RUN_ID,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )
        raise


def compare_with_production(client, model_name: str, new_version: str) -> bool:
    """Compare new model metrics against Production version before promotion"""
    try:
        new_mv = client.get_model_version(model_name, new_version)
        new_run = client.get_run(new_mv.run_id)
        new_metrics = new_run.data.metrics

        prod_versions = client.get_latest_versions(model_name, stages=["Production"])
        if not prod_versions:
            logger.info("No Production model exists. Promoting new model.", extra={"run_id": RUN_ID if 'RUN_ID' in dir() else 'unknown'})
            return True

        prod_version = prod_versions[0]
        prod_run = client.get_run(prod_version.run_id)
        prod_metrics = prod_run.data.metrics

        metrics_to_check = ["auc", "accuracy", "f1"]
        better_count = 0
        worse_count = 0
        
        for metric in metrics_to_check:
            if metric in new_metrics and metric in prod_metrics:
                new_val = new_metrics[metric]
                prod_val = prod_metrics[metric]
                if new_val >= prod_val:
                    better_count += 1
                    logger.info(f"New model better on {metric}: {new_val:.4f} >= {prod_val:.4f}")
                else:
                    worse_count += 1
                    logger.info(f"New model worse on {metric}: {new_val:.4f} < {prod_val:.4f}")
        
        if better_count >= 2:
            logger.info("New model meets promotion criteria")
            return True
        else:
            logger.info("New model does NOT meet promotion criteria")
            return False

    except Exception as e:
        logger.warning(f"Comparison failed: {e}. Promoting anyway.")
        return True


def main():
    try:
        logger.info("Starting retraining pipeline", extra={"run_id": RUN_ID})
        
        X, y = load_data_from_redis()
        
        categorical_cols = X.select_dtypes(include=["object"]).columns.tolist()
        X = pd.get_dummies(X, columns=categorical_cols)
        
        logger.info(
            "Features prepared",
            extra={
                "run_id": RUN_ID,
                "shape": X.shape,
                "n_features": X.shape[1]
            }
        )
        
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=42
        )
        
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(EXPERIMENT_NAME)
        
        best = search(X_train, y_train)
        logger.info(
            "Hyperparameter optimization completed",
            extra={
                "run_id": RUN_ID,
                "best_params": best
            }
        )
        
        with mlflow.start_run() as run:
            model = RandomForestClassifier(**best, n_jobs=-1)
            model.fit(X_train, y_train)
            
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
            
            feature_cols = X.columns.tolist()
            joblib.dump(feature_cols, "columns.pkl")
            mlflow.log_artifact("columns.pkl")
            
            mlflow.sklearn.log_model(model, "model", registered_model_name=MODEL_NAME)
            
            client = mlflow.tracking.MlflowClient()
            latest_version = client.get_latest_versions(MODEL_NAME, stages=["None"])[0].version
            
            should_promote = compare_with_production(client, MODEL_NAME, latest_version)
            
            if should_promote:
                client.transition_model_version_stage(MODEL_NAME, int(latest_version), "Production")
                logger.info(
                    "Model promoted to Production",
                    extra={
                        "run_id": RUN_ID,
                        "model_version": latest_version,
                        "stage": "Production"
                    }
                )
            else:
                logger.info(
                    "Model archived (did not meet promotion criteria)",
                    extra={
                        "run_id": RUN_ID,
                        "model_version": latest_version,
                        "stage": "Archived"
                    }
                )

        try:
            queue_manager = RetrainQueueManager()
            queue_manager.clear_queue()
            logger.info("Retrain queue cleared after successful training", extra={"run_id": RUN_ID})
        except Exception as e:
            logger.warning(
                f"Could not clear retrain queue: {e}",
                extra={"run_id": RUN_ID}
            )
        
        logger.info("Retraining pipeline finished successfully", extra={"run_id": RUN_ID})
        
    except Exception as e:
        logger.error(
            "Retraining pipeline failed",
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