import os
import sys
import argparse
import pandas as pd
import mlflow
import mlflow.sklearn
import joblib
from typing import Tuple, Dict, Optional
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

logger = setup_logging("trainer")


# ============================================
# DATA LOADING
# ============================================

def load_data_from_csv() -> pd.DataFrame:
    """Load and preprocess data from CSV file"""
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
    """Load labeled training data from Redis retrain queue"""
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
    """
    Load data from appropriate source.
    
    Args:
        source: "csv", "redis", or "auto" (try redis first, fallback to csv)
        batch_size: Number of records to fetch from Redis
    
    Returns:
        DataFrame with features and Churn column
    """
    if source == "redis":
        df = load_data_from_redis(batch_size)
        if df is None:
            raise ValueError("No data available in Redis queue")
        return df
    
    elif source == "csv":
        return load_data_from_csv()
    
    else:  # auto - try redis first, fallback to csv
        df = load_data_from_redis(batch_size)
        if df is not None:
            return df
        logger.info("Falling back to CSV data source")
        return load_data_from_csv()


# ============================================
# FEATURE ENGINEERING
# ============================================

def prepare_features(df: pd.DataFrame, fit: bool = True, columns: list = None) -> Tuple[pd.DataFrame, pd.Series, list]:
    """
    Prepare features for training.
    
    Args:
        df: Input DataFrame with Churn column
        fit: If True, return feature columns for saving
        columns: Pre-existing feature columns for inference mode
    
    Returns:
        X: Feature matrix
        y: Target series
        feature_columns: List of feature column names (if fit=True)
    """
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


# ============================================
# MODEL COMPARISON & PROMOTION
# ============================================

def should_promote_to_production(new_metrics: Dict[str, float]) -> bool:
    """
    Compare new model metrics with current production model.
    
    Args:
        new_metrics: Metrics dictionary from new model
    
    Returns:
        True if new model should be promoted, False otherwise
    """
    try:
        client = mlflow.tracking.MlflowClient()
        prod_versions = client.get_latest_versions(MODEL_NAME, stages=["Production"])
        
        if not prod_versions:
            logger.info("No production model exists. Will promote new model.")
            return True
        
        prod_run = client.get_run(prod_versions[0].run_id)
        prod_metrics = prod_run.data.metrics
        
        # Compare key metrics
        for metric in ["auc", "accuracy", "f1"]:
            new_val = new_metrics.get(metric, 0)
            prod_val = prod_metrics.get(metric, 0)
            
            if new_val > prod_val:
                logger.info(f"New model better on {metric}: {new_val:.4f} > {prod_val:.4f}")
                return True
            elif new_val < prod_val:
                logger.info(f"New model worse on {metric}: {new_val:.4f} < {prod_val:.4f}")
                return False
        
        logger.info("Metrics are equal or comparable. Promoting new model.")
        return True
        
    except Exception as e:
        logger.warning(f"Error comparing with production: {e}. Will promote anyway.")
        return True


def promote_to_production(version: str):
    """Promote model version to Production and clear old cache"""
    try:
        client = mlflow.tracking.MlflowClient()
        
        # Get current production version before changing
        old_prod_versions = client.get_latest_versions(MODEL_NAME, stages=["Production"])
        
        # Promote new version
        client.transition_model_version_stage(MODEL_NAME, int(version), "Production")
        logger.info(f"Model version {version} promoted to Production")
        
        # Clear cache for old production model
        for old in old_prod_versions:
            if str(old.version) != str(version):
                from shared.feature_store import clear_cache_for_model_version
                clear_cache_for_model_version(old.version)
                logger.info(f"Cleared cache for old production model v{old.version}")
                
    except Exception as e:
        logger.error(f"Failed to promote model: {e}")
        raise


# ============================================
# TRAINING PIPELINE
# ============================================

def run_training_pipeline(source: str = "auto") -> Dict:
    """
    Complete training pipeline.
    
    Args:
        source: "csv", "redis", or "auto"
    
    Returns:
        Dictionary with training results
    """
    logger.info(f"Starting training pipeline (source={source})")
    
    # Load data
    df = load_data(source=source)
    logger.info(f"Loaded {len(df)} records for training")
    
    # Prepare features
    X, y, feature_columns = prepare_features(df, fit=True)
    logger.info(f"Prepared {X.shape[1]} features, {X.shape[0]} samples")
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    logger.info(f"Train: {X_train.shape[0]}, Test: {X_test.shape[0]}")
    
    # Configure MLflow
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)
    
    # Hyperparameter search
    best_params = search(X_train, y_train)
    logger.info(f"Best hyperparameters: {best_params}")
    
    # Train and evaluate
    with mlflow.start_run() as run:
        model = RandomForestClassifier(**best_params, n_jobs=-1, random_state=42)
        model.fit(X_train, y_train)
        
        y_pred = model.predict(X_test)
        y_prob = model.predict_proba(X_test)[:, 1]
        metrics_dict = metrics(y_test, y_pred, y_prob)
        logger.info(f"Model metrics: {metrics_dict}")
        
        # Log to MLflow
        mlflow.log_params(best_params)
        mlflow.log_metrics(metrics_dict)
        
        # Save and log feature columns
        joblib.dump(feature_columns, "columns.pkl")
        mlflow.log_artifact("columns.pkl")
        
        # Log model to registry
        mlflow.sklearn.log_model(model, "model", registered_model_name=MODEL_NAME)
        
        # Log feature importance
        feature_importance = dict(zip(feature_columns, model.feature_importances_.tolist()))
        mlflow.log_dict(feature_importance, "feature_importance.json")
        
        # Get new model version
        client = mlflow.tracking.MlflowClient()
        new_version = client.get_latest_versions(MODEL_NAME, stages=["None"])[0].version
        
        # Decide whether to promote
        if should_promote_to_production(metrics_dict):
            promote_to_production(new_version)
            status = "promoted"
        else:
            logger.info(f"Model version {new_version} archived (not promoted)")
            status = "archived"
        
        # Clear Redis queue if we used it
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


# ============================================
# CELERY TASK WRAPPER (for worker)
# ============================================

def run_retraining(run_id: str = None) -> dict:
    """
    Wrapper function for Celery task.
    
    Args:
        run_id: Optional run ID (for tracking)
    
    Returns:
        Training results dictionary
    """
    logger.info(f"Retraining task started (run_id={run_id})")
    
    try:
        result = run_training_pipeline(source="auto")
        logger.info(f"Retraining completed successfully: {result}")
        return result
    except Exception as e:
        logger.error(f"Retraining failed: {e}", exc_info=True)
        raise


# ============================================
# MAIN ENTRY POINT
# ============================================

def main():
    """Main entry point for CLI execution"""
    parser = argparse.ArgumentParser(description="MLOps Training Pipeline")
    parser.add_argument(
        "--source",
        type=str,
        choices=["csv", "redis", "auto"],
        default="csv",
        help="Data source: csv (initial training), redis (retraining), or auto"
    )
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