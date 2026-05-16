import sys
import os
import uuid
import atexit
import time

sys.path.insert(0, '/app')

from celery import Celery, signals
from shared.config import REDIS_EXPIRE_DAYS, REDIS_EXPIRE_SECONDS, REDIS_URL, TASK_TIMEOUT_SECONDS, TASK_SOFT_TIMEOUT_SECONDS, RETRY_COUNTDOWN_SECONDS, MAX_RETRIES
from shared.logging import setup_logging
from shared.retrain_queue import RetrainQueueManager
from trainer.train import run_retraining
from shared.metrics import RETRAIN_DURATION, RETRAIN_SUCCESS, RETRAIN_FAILURE

WORKER_ID = str(uuid.uuid4())

def _cleanup_logging():
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
    logger.info(
        "Worker process initialized",
        extra={
            "worker_id": WORKER_ID,
            "pid": os.getpid(),
            "broker_url": REDIS_URL
        }
    )

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
        
@app.task(name="expire_old_pending_records")
def expire_old_pending_records():
    queue_manager = RetrainQueueManager()
    expired_count = queue_manager.expire_old_pending(days=REDIS_EXPIRE_DAYS)
    logger.info(f"Expired {expired_count} old pending records")
    return {"expired_count": expired_count}

app.conf.beat_schedule = {
    'expire-old-pending': {
        'task': 'expire_old_pending_records',
        'schedule': REDIS_EXPIRE_SECONDS,
    },
    'periodic-drift-check': {
        'task': 'periodic_drift_check',
        'schedule': 3600.0,
        'args': (24, 100),
    },
}

import worker.batch_predictor
import worker.drift_tasks