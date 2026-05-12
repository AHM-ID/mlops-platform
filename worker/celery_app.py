import sys
sys.path.insert(0, '/app')

from celery import Celery, signals
import subprocess
from shared.config import REDIS_URL
from shared.logging import setup_logging

logger = setup_logging("worker")

app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)

app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,
    task_soft_time_limit=25 * 60,
    broker_connection_retry_on_startup=True,
)

@signals.worker_process_init.connect
def init_worker(**kwargs):
    logger.info("Worker process initialized")

import worker.batch_predictor

@app.task(bind=True)
def retrain(self):
    logger.info(f"Task {self.request.id} started: retraining model")
    try:
        result = subprocess.run(
            ["python", "trainer/train_from_redis.py"],
            capture_output=True,
            text=True,
            check=True,
            timeout=1800
        )
        logger.info("Retraining succeeded", extra={"stdout": result.stdout[:500]})
        return {"status": "success", "output": result.stdout}
    except subprocess.TimeoutExpired as e:
        logger.error(f"Retraining timeout after {e.timeout}s")
        raise
    except subprocess.CalledProcessError as e:
        logger.error(f"Retraining failed with code {e.returncode}", 
                    extra={"stderr": e.stderr[:500]})
        raise