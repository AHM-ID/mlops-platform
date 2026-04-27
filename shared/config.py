import os

MLFLOW_URI = os.getenv("MLFLOW_URI", "http://mlflow:5000")
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
DB_URL = os.getenv(
    "DB_URL",
    "postgresql://admin:admin@postgres/mlops"
)

EXPERIMENT_NAME = "customer_churn"
MODEL_NAME = "churn_model"

S3_ENDPOINT = os.getenv("MLFLOW_S3_ENDPOINT_URL", "http://garage:3900")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "admin")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "password")