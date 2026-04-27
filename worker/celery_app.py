from celery import Celery
import subprocess
from shared.config import REDIS_URL

app = Celery(
    "tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

@app.task
def retrain():
    subprocess.run(
        ["python", "trainer/train.py"],
        check=True
    )