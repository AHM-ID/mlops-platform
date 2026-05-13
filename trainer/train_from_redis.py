import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
import mlflow
import mlflow.sklearn
import joblib
from typing import Tuple
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

from shared.config import MLFLOW_TRACKING_URI, EXPERIMENT_NAME, MODEL_NAME
from trainer.optimize import search
from trainer.evaluate import metrics
from shared.logging import setup_logging
from services.retrain_queue import RetrainQueueManager

logger = setup_logging("trainer_redis")

def _preprocess_csv_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series]:
    if "customerID" in df.columns:
        df = df.drop(columns=["customerID"])
    
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    df = df.dropna()
    
    y = df["Churn"].map({"Yes": 1, "No": 0})
    X = df.drop(columns=["Churn"])
    return X, y

def load_data_from_csv() -> Tuple[pd.DataFrame, pd.Series]:
    if not os.path.exists("data/churn.csv"):
        logger.error("data/churn.csv not found!")
        raise FileNotFoundError("data/churn.csv not found")
    
    df = pd.read_csv("data/churn.csv")
    logger.info(f"Loaded data from CSV, shape: {df.shape}")
    
    return _preprocess_csv_data(df)

def load_data_from_redis() -> Tuple[pd.DataFrame, pd.Series]:
    queue_manager = RetrainQueueManager()
    queue_length = queue_manager.get_queue_length()
    logger.info(f"Found {queue_length} records in retrain queue")
    
    if queue_length == 0:
        logger.info("No training data in Redis, falling back to CSV")
        return load_data_from_csv()
    
    batch = queue_manager.get_training_batch(batch_size=10000)
    if not batch:
        logger.warning("No records retrieved, falling back to CSV")
        return load_data_from_csv()
    
    records = []
    for record in batch:
        features = record.get("features", {})
        label = record.get("label")
        if label is not None:
            feature_copy = features.copy()
            feature_copy["Churn"] = "Yes" if label == 1 else "No"
            records.append(feature_copy)
    
    if not records:
        logger.warning("No valid labeled records, falling back to CSV")
        return load_data_from_csv()
    
    df = pd.DataFrame(records)
    logger.info(f"Loaded {len(df)} records from Redis")
    
    y = df["Churn"].map({"Yes": 1, "No": 0})
    X = df.drop(columns=["Churn"])
    return X, y

def _should_promote_model(client, model_name: str, new_version: str) -> bool:
    try:
        new_mv = client.get_model_version(model_name, new_version)
        new_run = client.get_run(new_mv.run_id)
        new_metrics = new_run.data.metrics

        prod_versions = client.get_latest_versions(model_name, stages=["Production"])
        if not prod_versions:
            logger.info("No Production model exists. Promoting new model.")
            return True

        prod_version = prod_versions[0]
        prod_run = client.get_run(prod_version.run_id)
        prod_metrics = prod_run.data.metrics

        for metric in ["auc", "accuracy", "f1"]:
            if metric in new_metrics and metric in prod_metrics:
                new_val = new_metrics[metric]
                prod_val = prod_metrics[metric]
                if new_val >= prod_val:
                    logger.info(f"New model is better or equal on {metric} ({new_val:.4f} >= {prod_val:.4f}). Promoting.")
                    return True
                else:
                    logger.info(f"New model is worse on {metric} ({new_val:.4f} < {prod_val:.4f}). Not promoting.")
                    return False

        logger.info("Could not compare metrics properly. Promoting anyway.")
        return True

    except Exception as e:
        logger.warning(f"Comparison failed: {e}. Promoting anyway.")
        return True

def compare_with_production(client, model_name: str, new_version: str) -> bool:
    return _should_promote_model(client, model_name, new_version)

def _clear_retrain_queue():
    try:
        queue_manager = RetrainQueueManager()
        queue_manager.clear_queue()
    except Exception as e:
        logger.warning(f"Could not clear retrain queue: {e}")

def main():
    logger.info("Starting training pipeline with Redis support")
    
    X, y = load_data_from_redis()
    
    categorical_cols = X.select_dtypes(include=["object"]).columns.tolist()
    X = pd.get_dummies(X, columns=categorical_cols)
    
    logger.info(f"Prepared features, shape: {X.shape}")
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)
    
    best = search(X_train, y_train)
    logger.info(f"Best hyperparameters: {best}")
    
    with mlflow.start_run():
        model = RandomForestClassifier(**best, n_jobs=-1)
        model.fit(X_train, y_train)
        
        pred = model.predict(X_test)
        prob = model.predict_proba(X_test)[:, 1]
        scores = metrics(y_test, pred, prob)
        logger.info(f"New model metrics: {scores}")
        
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
            logger.info(f"Model version {latest_version} promoted to Production")
        else:
            logger.info(f"Model version {latest_version} was not promoted")

    _clear_retrain_queue()
    
    logger.info("Training pipeline finished successfully")

if __name__ == "__main__":
    main()
