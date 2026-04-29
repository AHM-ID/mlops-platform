# api/main.py

import time
import tempfile

import pandas as pd
import joblib
import mlflow
import mlflow.pyfunc

from fastapi import FastAPI, Request
from fastapi.responses import Response
from prometheus_client import Counter, generate_latest

from shared.config import MODEL_NAME, MLFLOW_TRACKING_URI
from trainer.features import prepare
from api.predictor import infer
from shared.logging import setup_logging


logger = setup_logging("api")

app = FastAPI()

REQ = Counter("prediction_requests_total", "Total prediction requests")


@app.on_event("startup")
def load_model():
    logger.info("Loading model from MLflow")

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    try:
        # Load model from registry
        app.state.model = mlflow.pyfunc.load_model(
            f"models:/{MODEL_NAME}/Production"
        )

        # Load artifacts
        client = mlflow.tracking.MlflowClient()
        latest = client.get_latest_versions(MODEL_NAME, stages=["Production"])[0]

        tmp_dir = tempfile.mkdtemp()
        artifact_path = client.download_artifacts(
            latest.run_id,
            "columns.pkl",
            tmp_dir
        )

        app.state.cols = joblib.load(artifact_path)
        app.state.model_loaded = True

        logger.info("Model and artifacts loaded successfully")

    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        app.state.model_loaded = False


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    logger.info(
        "Request processed",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": round(duration * 1000, 2)
        }
    )

    return response


@app.get("/health")
def health():
    if not hasattr(app.state, "model_loaded") or not app.state.model_loaded:
        return {"status": "model not loaded — run trainer first"}
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")


@app.post("/predict")
def predict(payload: dict):
    REQ.inc()

    df = pd.DataFrame([payload])
    X = prepare(df, training=False, columns=app.state.cols)

    pred, prob = infer(app.state.model, X)

    return {
        "prediction": pred,
        "probability": prob
    }