from celery import Celery
import subprocess
from shared.config import REDIS_URL
from shared.logging import setup_logging

logger = setup_logging("worker")

app = Celery("tasks", broker=REDIS_URL, backend=REDIS_URL)

@app.task(bind=True)
def retrain(self):
    logger.info(f"Task {self.request.id} started: retraining model")
    try:
        result = subprocess.run(
            ["python", "trainer/train.py"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("Retraining succeeded", extra={"stdout": result.stdout})
        return {"status": "success", "output": result.stdout}
    except subprocess.CalledProcessError as e:
        logger.error("Retraining failed", extra={"stderr": e.stderr, "returncode": e.returncode})
        raise