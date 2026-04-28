from fastapi import FastAPI, Request
from prometheus_client import Counter, generate_latest
from fastapi.responses import Response
import pandas as pd
import time

from trainer.features import prepare
from api.predictor import infer, cols
from shared.logging import setup_logging

logger = setup_logging("api")

app = FastAPI()

REQ = Counter("prediction_requests_total", "Total prediction requests")

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
    logger.debug("Health check called")
    return {"status": "ok"}

@app.get("/metrics")
def metrics():
    return Response(generate_latest(), media_type="text/plain")

@app.post("/predict")
def predict(payload: dict):
    REQ.inc()
    logger.info("Prediction request received", extra={"payload_keys": list(payload.keys())})

    df = pd.DataFrame([payload])
    X = prepare(df, training=False, columns=cols)
    pred, prob = infer(X)

    logger.info("Prediction completed", extra={"prediction": pred, "probability": prob})
    return {"prediction": pred, "probability": prob}