import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pandas as pd
import mlflow
import mlflow.sklearn
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier

from shared.config import MLFLOW_TRACKING_URI, EXPERIMENT_NAME, MODEL_NAME
from trainer.features import prepare
from trainer.optimize import search
from trainer.evaluate import metrics
from shared.logging import setup_logging

logger = setup_logging("trainer")

def _load_data(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        logger.error(f"{path} not found!")
        raise FileNotFoundError(f"{path} not found")
    
    df = pd.read_csv(path)
    logger.info(f"Loaded data, shape: {df.shape}")
    return df

def _prepare_train_test_split(df: pd.DataFrame):
    X, y, cols = prepare(df, training=True)
    logger.info(f"Prepared features, shape: {X.shape}")
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    logger.info(f"Train/test split: {X_train.shape[0]}/{X_test.shape[0]}")
    
    return X_train, X_test, y_train, y_test, cols

def _configure_mlflow():
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

def _train_and_evaluate(X_train, y_train, X_test, y_test, best_params):
    model = RandomForestClassifier(**best_params, n_jobs=-1)
    model.fit(X_train, y_train)
    logger.info("Model training completed")
    
    pred = model.predict(X_test)
    prob = model.predict_proba(X_test)[:, 1]
    scores = metrics(y_test, pred, prob)
    logger.info(f"Metrics: {scores}")
    
    return model, scores

def _log_artifacts_and_model(model, best_params, scores, cols):
    mlflow.log_params(best_params)
    mlflow.log_metrics(scores)
    
    joblib.dump(cols, "columns.pkl")
    mlflow.log_artifact("columns.pkl")
    
    mlflow.sklearn.log_model(model, "model", registered_model_name=MODEL_NAME)
    logger.info(f"Model registered as {MODEL_NAME} in MLflow")

def _promote_to_production():
    client = mlflow.tracking.MlflowClient()
    latest_version = client.get_latest_versions(MODEL_NAME, stages=["None"])[0].version
    client.transition_model_version_stage(MODEL_NAME, int(latest_version), "Production")
    logger.info(f"Model version {latest_version} promoted to Production")

def main():
    logger.info("Starting training pipeline")
    
    df = _load_data("data/churn.csv")
    X_train, X_test, y_train, y_test, cols = _prepare_train_test_split(df)
    
    _configure_mlflow()
    
    best = search(X_train, y_train)
    logger.info(f"Best hyperparameters found: {best}")
    
    with mlflow.start_run():
        model, scores = _train_and_evaluate(X_train, y_train, X_test, y_test, best)
        _log_artifacts_and_model(model, best, scores, cols)
        _promote_to_production()
    
    logger.info("Training pipeline finished successfully")

if __name__ == "__main__":
    main()
