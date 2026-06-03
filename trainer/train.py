# trainer/train.py
import os
import sys
import argparse
import pandas as pd
import mlflow
import mlflow.sklearn
import joblib
from typing import Tuple, Dict, Optional, List
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.config import MLFLOW_TRACKING_URI, EXPERIMENT_NAME, MODEL_NAME, DATA_PATH
from shared.feature_store import FeatureStore
from shared.retrain_queue import RetrainQueueManager
from shared.logging import setup_logging
from trainer.optimize import search
from trainer.evaluate import metrics
from shared.metrics import set_model_metrics

logger = setup_logging("trainer")

def load_data_from_csv() -> pd.DataFrame:
    if not os.path.exists(DATA_PATH):
        raise FileNotFoundError(f"Data file not found: {DATA_PATH}")
    
    df = pd.read_csv(DATA_PATH)
    logger.info(f"Loaded data from CSV: {df.shape[0]} rows")
    
    if "customerID" in df.columns:
        df = df.drop(columns=["customerID"])
    
    df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
    df = df.dropna()
    
    logger.info(f"After preprocessing: {df.shape[0]} rows")
    return df

def load_data_from_redis(batch_size: int = 1000) -> Optional[pd.DataFrame]:
    queue_manager = RetrainQueueManager()
    batch = queue_manager.get_training_batch(batch_size)
    
    if not batch:
        logger.info("No labeled records found in Redis queue")
        return None
    
    records = []
    for record in batch:
        if record.get("label") is not None:
            features = record["features"].copy()
            features["Churn"] = "Yes" if record["label"] == 1 else "No"
            records.append(features)
    
    if not records:
        logger.warning("No valid records with labels found")
        return None
    
    df = pd.DataFrame(records)
    logger.info(f"Loaded {len(df)} labeled records from Redis queue")
    return df

def load_data(source: str = "auto", batch_size: int = 1000) -> pd.DataFrame:
    if source == "redis":
        df = load_data_from_redis(batch_size)
        if df is None:
            raise ValueError("No data available in Redis queue")
        return df
    
    elif source == "csv":
        return load_data_from_csv()
    
    else:
        df = load_data_from_redis(batch_size)
        if df is not None:
            return df
        logger.info("Falling back to CSV data source")
        return load_data_from_csv()

def prepare_features(df: pd.DataFrame, fit: bool = True, columns: list = None) -> Tuple[pd.DataFrame, pd.Series, list]:
    y = df["Churn"].map({"Yes": 1, "No": 0})
    X = df.drop(columns=["Churn"])
    
    categorical_cols = X.select_dtypes(include=["object"]).columns.tolist()
    X = pd.get_dummies(X, columns=categorical_cols)
    
    if fit:
        feature_columns = X.columns.tolist()
        return X, y, feature_columns
    else:
        if columns is None:
            raise ValueError("columns required when fit=False")
        for col in columns:
            if col not in X.columns:
                X[col] = 0
        return X[columns], y, None

def get_current_production_version() -> Optional[str]:
    try:
        client = mlflow.tracking.MlflowClient()
        all_versions = client.search_model_versions(f"name='{MODEL_NAME}'")
        
        for version in all_versions:
            if version.current_stage == "Production":
                return version.version
        return None
    except Exception as e:
        logger.warning(f"Failed to get current production version: {e}")
        return None

def get_production_metrics() -> Dict[str, float]:
    try:
        client = mlflow.tracking.MlflowClient()
        all_versions = client.search_model_versions(f"name='{MODEL_NAME}'")
        
        for version in all_versions:
            if version.current_stage == "Production":
                run = client.get_run(version.run_id)
                return run.data.metrics
        return {}
    except Exception as e:
        logger.warning(f"Failed to get production metrics: {e}")
        return {}

def should_promote_to_production(new_metrics: Dict[str, float]) -> bool:
    try:
        prod_metrics = get_production_metrics()
        
        if not prod_metrics:
            logger.info("No production model exists. Will promote new model.")
            return True
        
        new_auc = new_metrics.get('auc', 0)
        prod_auc = prod_metrics.get('auc', 0)
        
        if new_auc > prod_auc:
            logger.info(f"New model better on AUC: {new_auc:.4f} > {prod_auc:.4f}")
            return True
        elif new_auc < prod_auc:
            logger.info(f"New model worse on AUC: {new_auc:.4f} < {prod_auc:.4f}")
            return False
        else:
            new_f1 = new_metrics.get('f1', 0)
            prod_f1 = prod_metrics.get('f1', 0)
            if new_f1 > prod_f1:
                logger.info(f"New model better on F1: {new_f1:.4f} > {prod_f1:.4f}")
                return True
        
        logger.info("Metrics are comparable. Promoting new model.")
        return True
        
    except Exception as e:
        logger.warning(f"Error comparing with production: {e}. Will promote anyway.")
        return True

def promote_to_production(version: str, auc: float):
    try:
        client = mlflow.tracking.MlflowClient()
        
        old_prod_versions = client.get_latest_versions(MODEL_NAME, stages=["Production"])
        old_version = old_prod_versions[0].version if old_prod_versions else None
        
        client.transition_model_version_stage(MODEL_NAME, int(version), "Production")
        logger.info(f"Model version {version} promoted to Production")
        
        set_model_metrics(version, auc)
        logger.info(f"Updated dashboard metrics: v{version}, AUC: {auc}")
        
        if old_version and str(old_version) != str(version):
            from shared.feature_store import clear_cache_for_model_version
            clear_cache_for_model_version(old_version)
            logger.info(f"Cleared cache for old production model v{old_version}")
                
    except Exception as e:
        logger.error(f"Failed to promote model: {e}")
        raise

def run_training_pipeline(source: str = "auto") -> Dict:
    logger.info(f"Starting training pipeline (source={source})")
    
    df = load_data(source=source)
    logger.info(f"Loaded {len(df)} records for training")
    
    X, y, feature_columns = prepare_features(df, fit=True)
    logger.info(f"Prepared {X.shape[1]} features, {X.shape[0]} samples")
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    logger.info(f"Train: {X_train.shape[0]}, Test: {X_test.shape[0]}")
    
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)
    
    best_params = search(X_train, y_train)
    logger.info(f"Best hyperparameters: {best_params}")
    
    with mlflow.start_run() as run:
        model = RandomForestClassifier(**best_params, n_jobs=-1, random_state=42)
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        metrics_dict = metrics(y_test, y_pred, y_prob)
        logger.info(f"Model metrics: {metrics_dict}")
        
        mlflow.log_params(best_params)
        mlflow.log_metrics(metrics_dict)
        
        joblib.dump(feature_columns, "columns.pkl")
        mlflow.log_artifact("columns.pkl")
        
        mlflow.sklearn.log_model(model, "model", registered_model_name=MODEL_NAME)
        
        feature_importance = dict(zip(feature_columns, model.feature_importances_.tolist()))
        mlflow.log_dict(feature_importance, "feature_importance.json")
        
        client = mlflow.tracking.MlflowClient()
        all_versions = client.search_model_versions(f"name='{MODEL_NAME}'")
        new_version = None
        for v in all_versions:
            if v.run_id == run.info.run_id:
                new_version = v.version
                break
        
        if new_version is None:
            raise RuntimeError("Could not find newly created model version")
        
        auc_value = metrics_dict.get('auc', 0.0)
        
        if should_promote_to_production(metrics_dict):
            promote_to_production(new_version, auc_value)
            status = "promoted"
        else:
            logger.info(f"Model version {new_version} archived (not promoted)")
            status = "archived"
        
        if source in ["redis", "auto"]:
            RetrainQueueManager().clear_queue()
            logger.info("Cleared Redis retrain queue")
        
        return {
            "status": status,
            "version": new_version,
            "metrics": metrics_dict,
            "run_id": run.info.run_id,
            "feature_count": len(feature_columns)
        }

def run_retraining(run_id: str = None) -> dict:
    logger.info(f"Retraining task started (run_id={run_id})")
    try:
        result = run_training_pipeline(source="auto")
        logger.info(f"Retraining completed successfully: {result}")
        return result
    except Exception as e:
        logger.error(f"Retraining failed: {e}", exc_info=True)
        raise

def main():
    parser = argparse.ArgumentParser(description="MLOps Training Pipeline")
    parser.add_argument("--source", type=str, choices=["csv", "redis", "auto"], default="csv", help="Data source")
    args = parser.parse_args()
    
    try:
        result = run_training_pipeline(source=args.source)
        print("\n" + "="*50)
        print("TRAINING COMPLETED SUCCESSFULLY")
        print(f"Status: {result['status']}")
        print(f"Model Version: {result['version']}")
        print(f"Metrics: {result['metrics']}")
        print("="*50)
        return 0
    except Exception as e:
        logger.error(f"Training failed: {e}", exc_info=True)
        print(f"\nERROR: Training failed - {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())