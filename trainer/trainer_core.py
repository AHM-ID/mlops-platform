# trainer/trainer_core.py
import pandas as pd
import mlflow
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from trainer.features import prepare
from trainer.optimize import search
from trainer.evaluate import metrics
from trainer.train_from_redis import compare_with_production
from shared.config import MLFLOW_TRACKING_URI, EXPERIMENT_NAME, MODEL_NAME
from shared.retrain_queue import RetrainQueueManager
from shared.logging import setup_logging

logger = setup_logging("trainer_core")

def run_retraining(run_id: str) -> dict:
    """Execute training pipeline, returns status and metrics."""
    try:
        # Load data from Redis or CSV
        queue_manager = RetrainQueueManager()
        queue_length = queue_manager.get_queue_length()
        if queue_length == 0:
            # fallback to CSV
            df = pd.read_csv("data/churn.csv")
            df = df.drop(columns=["customerID"])
            df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
            df = df.dropna()
            y = df["Churn"].map({"Yes": 1, "No": 0})
            X = df.drop(columns=["Churn"])
        else:
            batch = queue_manager.get_training_batch(batch_size=10000)
            records = []
            for record in batch:
                if record.get("label") is not None:
                    features = record["features"].copy()
                    features["Churn"] = "Yes" if record["label"] == 1 else "No"
                    records.append(features)
            if not records:
                raise ValueError("No labeled records in queue")
            df = pd.DataFrame(records)
            y = df["Churn"].map({"Yes": 1, "No": 0})
            X = df.drop(columns=["Churn"])

        # One-hot encoding
        categorical_cols = X.select_dtypes(include=["object"]).columns.tolist()
        X = pd.get_dummies(X, columns=categorical_cols)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, stratify=y, random_state=42
        )

        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.set_experiment(EXPERIMENT_NAME)

        best_params = search(X_train, y_train)

        with mlflow.start_run() as run:
            model = RandomForestClassifier(**best_params, n_jobs=-1)
            model.fit(X_train, y_train)

            pred = model.predict(X_test)
            prob = model.predict_proba(X_test)[:, 1]
            scores = metrics(y_test, pred, prob)

            mlflow.log_params(best_params)
            mlflow.log_metrics(scores)

            feature_cols = X.columns.tolist()
            joblib.dump(feature_cols, "columns.pkl")
            mlflow.log_artifact("columns.pkl")
            mlflow.sklearn.log_model(model, "model", registered_model_name=MODEL_NAME)

            client = mlflow.tracking.MlflowClient()
            latest_version = client.get_latest_versions(MODEL_NAME, stages=["None"])[0].version

            # Compare with production
            client = mlflow.tracking.MlflowClient()
            latest_version = client.get_latest_versions(MODEL_NAME, stages=["None"])[0].version
            
            should_promote = compare_with_production(client, MODEL_NAME, latest_version)
            
            if should_promote:
                client.transition_model_version_stage(MODEL_NAME, int(latest_version), "Production")
                status = "promoted"
            else:
                status = "archived"

            queue_manager.clear_queue()

            return {
                "status": status,
                "version": latest_version,
                "metrics": scores,
                "run_id": run.info.run_id
            }
    except Exception as e:
        logger.error(f"Retraining failed: {e}", exc_info=True)
        raise