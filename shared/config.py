import os
import redis
from redis.connection import ConnectionPool
from typing import Optional

MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow:5000")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_EXPIRE_SECONDS = int(os.getenv("REDIS_EXPIRE_SECONDS", "86400"))
REDIS_EXPIRE_DAYS = int(os.getenv("REDIS_EXPIRE_DAYS", "30"))

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_USER = os.getenv("POSTGRES_USER", "admin")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "admin")
POSTGRES_DB = os.getenv("POSTGRES_DB", "mlops")
POSTGRES_URL = os.getenv("POSTGRES_URL", f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")

EXPERIMENT_NAME = os.getenv("EXPERIMENT_NAME", "customer_churn")
MODEL_NAME = os.getenv("MODEL_NAME", "churn_model")
COLUMNS_FILE = os.getenv("COLUMNS_FILE", "columns.pkl")
DATA_PATH = os.getenv("DATA_PATH", "data/churn.csv")

API_PORT = int(os.getenv("API_PORT", "8000"))
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_ROOT_PATH = os.getenv("API_ROOT_PATH", "/api")
PUBLIC_URL = os.getenv("PUBLIC_URL", "http://localhost:8080")

SERVICE_NAME_API = os.getenv("SERVICE_NAME_API", "api")
SERVICE_NAME_WORKER = os.getenv("SERVICE_NAME_WORKER", "worker")
SERVICE_NAME_TRAINER = os.getenv("SERVICE_NAME_TRAINER", "trainer")

CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
BATCH_EXPIRY_SECONDS = int(os.getenv("BATCH_EXPIRY_SECONDS", "86400"))
RETRAIN_BATCH_SIZE = int(os.getenv("RETRAIN_BATCH_SIZE", "1000"))
MAX_BATCH_RECORDS = int(os.getenv("MAX_BATCH_RECORDS", "10000"))
REDIS_MAX_CONNECTIONS = int(os.getenv("REDIS_MAX_CONNECTIONS", "10"))

HEALTH_TIMEOUT = int(os.getenv("HEALTH_TIMEOUT", "30"))
SOCKET_TIMEOUT = int(os.getenv("SOCKET_TIMEOUT", "5"))
TASK_TIMEOUT_SECONDS = int(os.getenv("TASK_TIMEOUT_SECONDS", "1800"))
TASK_SOFT_TIMEOUT_SECONDS = int(os.getenv("TASK_SOFT_TIMEOUT_SECONDS", "1500"))
RETRY_COUNTDOWN_SECONDS = int(os.getenv("RETRY_COUNTDOWN_SECONDS", "60"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
UPTIME_MOCK_SECONDS = int(os.getenv("UPTIME_MOCK_SECONDS", "3600"))

FLUENT_BIT_URL = os.getenv("FLUENT_BIT_URL", "http://fluent-bit:8888")
FLUENT_BIT_PORT = int(os.getenv("FLUENT_BIT_PORT", "8888"))
FLUENT_BIT_MONITOR_PORT = int(os.getenv("FLUENT_BIT_MONITOR_PORT", "2020"))
FLUENT_BIT_BATCH_SIZE = int(os.getenv("FLUENT_BIT_BATCH_SIZE", "10"))
FLUENT_BIT_FLUSH_INTERVAL = float(os.getenv("FLUENT_BIT_FLUSH_INTERVAL", "1.0"))

PROMETHEUS_MULTIPROC_DIR = os.getenv("PROMETHEUS_MULTIPROC_DIR", "/prometheus-metrics")
PROMETHEUS_SCRAPE_INTERVAL = os.getenv("PROMETHEUS_SCRAPE_INTERVAL", "15s")

RETRAIN_QUEUE_KEY = os.getenv("RETRAIN_QUEUE_KEY", "retrain:training_data")
RETRAIN_QUEUE_MAX_LENGTH = int(os.getenv("RETRAIN_QUEUE_MAX_LENGTH", "100000"))
DRIFT_REPORT_PATH = os.getenv("DRIFT_REPORT_PATH", "/tmp")

S3_ENDPOINT = os.getenv("MLFLOW_S3_ENDPOINT_URL", "http://garage:3900")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "admin")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "password")
AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION", "us-east-1")

RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"
RATE_LIMIT_REQUESTS = int(os.getenv("RATE_LIMIT_REQUESTS", "100"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

ROLE_RATE_LIMITS = {
    "admin": int(os.getenv("RATE_LIMIT_ADMIN", "1000")),
    "user": int(os.getenv("RATE_LIMIT_USER", "100")),
    "readonly": int(os.getenv("RATE_LIMIT_READONLY", "50")),
    "anonymous": int(os.getenv("RATE_LIMIT_ANONYMOUS", "10")),
}

CIRCUIT_BREAKER_FAILURE_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_FAILURE_THRESHOLD", "3"))
CIRCUIT_BREAKER_TIMEOUT_SECONDS = int(os.getenv("CIRCUIT_BREAKER_TIMEOUT_SECONDS", "60"))

_redis_pool = None

def get_redis_pool() -> ConnectionPool:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = ConnectionPool.from_url(
            REDIS_URL,
            max_connections=REDIS_MAX_CONNECTIONS,
            decode_responses=False,
            socket_connect_timeout=SOCKET_TIMEOUT,
            socket_timeout=SOCKET_TIMEOUT
        )
    return _redis_pool

def get_redis_client(decode_responses: bool = False) -> redis.Redis:
    pool = get_redis_pool()
    return redis.Redis(connection_pool=pool, decode_responses=decode_responses)

def is_testing() -> bool:
    return os.getenv("TESTING", "false").lower() == "true"
