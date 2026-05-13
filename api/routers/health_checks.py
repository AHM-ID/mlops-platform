import mlflow
import redis
import psycopg2
import psutil
from typing import Dict
import logging

from shared.config import (
    MLFLOW_TRACKING_URI,
    REDIS_URL,
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
    POSTGRES_DB
)

logger = logging.getLogger(__name__)


def check_mlflow_health() -> bool:
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        mlflow.search_experiments()
        return True
    except Exception as e:
        logger.error(f"MLflow health check failed: {e}")
        return False


def check_redis_health() -> bool:
    try:
        r = redis.from_url(REDIS_URL)
        r.ping()
        return True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return False


def check_postgres_health() -> bool:
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            port=POSTGRES_PORT,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            database=POSTGRES_DB
        )
        conn.close()
        return True
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {e}")
        return False


def get_system_resources() -> Dict[str, float]:
    cpu = psutil.cpu_percent()
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    
    return {
        "cpu_percent": cpu,
        "memory_percent": memory,
        "disk_percent": disk
    }
