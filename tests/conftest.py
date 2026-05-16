import os
import sys
import pytest
import tempfile
import json
import redis
import pandas as pd
from fastapi.testclient import TestClient
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.config import REDIS_URL, DATA_PATH, MODEL_NAME, MLFLOW_TRACKING_URI
from api.main import app

@pytest.fixture(scope="session")
def test_client():
    """FastAPI test client"""
    return TestClient(app)

@pytest.fixture(scope="session")
def redis_client():
    """Redis client for testing"""
    client = redis.from_url(REDIS_URL, decode_responses=True)
    yield client
    client.flushall()

@pytest.fixture(scope="session")
def sample_prediction_request():
    """Sample valid prediction request"""
    return {
        "customer_id": "TEST001",
        "tenure": 24,
        "MonthlyCharges": 75.5,
        "TotalCharges": 1814.0,
        "Contract": "Two year",
        "InternetService": "Fiber optic",
        "PaymentMethod": "Electronic check"
    }

@pytest.fixture(scope="session")
def sample_batch_requests():
    """Sample batch of prediction requests"""
    return {
        "batch_name": "test_batch",
        "data": [
            {
                "customer_id": f"CUST{i:03d}",
                "tenure": i % 72,
                "MonthlyCharges": 50.0 + i,
                "TotalCharges": (50.0 + i) * (i % 72),
                "Contract": ["Month-to-month", "One year", "Two year"][i % 3],
                "InternetService": ["DSL", "Fiber optic", "No"][i % 3],
                "PaymentMethod": ["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"][i % 4]
            }
            for i in range(50)
        ]
    }

@pytest.fixture(scope="session")
def api_keys():
    """API keys for testing roles"""
    return {
        "admin": "admin-secret-key-change-in-production",
        "user": "user-secret-key-change-in-production",
        "readonly": "readonly-secret-key-change-in-production",
        "invalid": "invalid-key"
    }

@pytest.fixture(autouse=True)
def clear_redis_before_test(redis_client):
    """Automatically clear Redis before each test"""
    redis_client.flushall()
    yield
    redis_client.flushall()