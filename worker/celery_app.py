import sys
import os
import uuid
import atexit
import time

sys.path.insert(0, '/app')

from celery import Celery, signals
import subprocess
from shared.config import REDIS_URL, TASK_TIMEOUT_SECONDS, TASK_SOFT_TIMEOUT_SECONDS, RETRY_COUNTDOWN_SECONDS, MAX_RETRIES
from shared.logging import setup_logging
from trainer.trainer_core import run_retraining
from shared.metrics import RETRAIN_DURATION, RETRAIN_SUCCESS, RETRAIN_FAILURE

WORKER_ID = str(uuid.uuid4())

def _cleanup_logging():
    """Ensure async log handlers flush before worker shutdown"""
    for handler in logger.logger.handlers[:]:
        if hasattr(handler, 'close'):
            try:
                handler.close()
            except Exception:
                pass
    time.sleep(0.3)

atexit.register(_cleanup_logging)

logger = setup_logging("worker", extra={'worker_id': WORKER_ID})

app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=TASK_TIMEOUT_SECONDS,
    task_soft_time_limit=TASK_SOFT_TIMEOUT_SECONDS,
    broker_connection_retry_on_startup=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)

@signals.worker_process_init.connect
def init_worker(**kwargs):
    """Initialize logging and resources when worker process starts"""
    logger.info(
        "Worker process initialized",
        extra={
            "worker_id": WORKER_ID,
            "pid": os.getpid(),
            "broker_url": REDIS_URL
        }
    )
    
    import worker.batch_predictor


@app.task(bind=True, name="retrain")
def retrain(self):
    with RETRAIN_DURATION.time():
        try:
            result = run_retraining(self.request.id)
            RETRAIN_SUCCESS.inc()
            logger.info("Retraining succeeded", extra={"task_id": self.request.id, "result": result})
            return result
        except Exception as e:
            RETRAIN_FAILURE.inc()
            logger.error("Retraining failed", extra={"task_id": self.request.id, "error": str(e)})
            raise self.retry(exc=e, countdown=RETRY_COUNTDOWN_SECONDS, max_retries=MAX_RETRIES)