from fastapi import FastAPI
from prometheus_client import Counter, generate_latest
from fastapi.responses import Response
import pandas as pd

from trainer.features import prepare
from api.predictor import infer, cols

app = FastAPI()

REQ = Counter(
    "prediction_requests_total",
    "Total prediction requests"
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        media_type="text/plain"
    )

@app.post("/predict")
def predict(payload: dict):
    REQ.inc()

    df = pd.DataFrame([payload])

    X = prepare(df, training=False, columns=cols)

    pred, prob = infer(X)

    return {
        "prediction": pred,
        "probability": prob
    }