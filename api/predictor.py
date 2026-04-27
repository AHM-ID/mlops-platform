import mlflow
import mlflow.pyfunc
import joblib
import tempfile
import os

from shared.config import MODEL_NAME

mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI"))

model = mlflow.pyfunc.load_model(
    f"models:/{MODEL_NAME}/Production"
)

client = mlflow.tracking.MlflowClient()
latest = client.get_latest_versions(MODEL_NAME, stages=["Production"])[0]

tmp_dir = tempfile.mkdtemp()
artifact_path = client.download_artifacts(
    latest.run_id,
    "columns.pkl",
    tmp_dir
)

cols = joblib.load(artifact_path)


def infer(df):
    pred = model.predict(df)[0]
    prob = model.predict_proba(df)[0][1]
    return int(pred), float(prob)