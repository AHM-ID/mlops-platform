import os
import sys
import pytest
import tempfile
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault("TESTING", "true")
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
os.environ.setdefault("MLFLOW_TRACKING_URI", "http://localhost:5000")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("POSTGRES_HOST", "localhost")
os.environ.setdefault("POSTGRES_PORT", "5432")
os.environ.setdefault("POSTGRES_USER", "admin")
os.environ.setdefault("POSTGRES_PASSWORD", "admin")
os.environ.setdefault("POSTGRES_DB", "mlops")
os.environ.setdefault("MODEL_NAME", "churn_model")
os.environ.setdefault("DATA_PATH", "data/churn.csv")

temp_dir = tempfile.mkdtemp()
os.environ["PROMETHEUS_MULTIPROC_DIR"] = temp_dir

mock_mlflow_patcher = patch('mlflow.tracking.MlflowClient')
mock_mlflow_client = mock_mlflow_patcher.start()

mock_client_instance = Mock()
mock_version = Mock()
mock_version.version = "1"
mock_version.run_id = "test_run_id_123"
mock_version.current_stage = "Production"
mock_version.name = "churn_model"
mock_version.creation_timestamp = 1609459200000
mock_version.last_updated_timestamp = 1609459200000
mock_client_instance.get_latest_versions.return_value = [mock_version]

mock_run = Mock()
mock_run.data.metrics = {"auc": 0.85, "accuracy": 0.82, "f1": 0.80}
mock_client_instance.get_run.return_value = mock_run
mock_client_instance.search_model_versions.return_value = [mock_version]

mock_mlflow_client.return_value = mock_client_instance

mock_load_patcher = patch('mlflow.pyfunc.load_model')
mock_load_model = mock_load_patcher.start()
mock_model = Mock()
mock_model.predict.return_value = [0]
mock_model.predict_proba.return_value = [[0.3, 0.7]]
mock_load_model.return_value = mock_model

patch('mlflow.set_tracking_uri', Mock()).start()

mock_redis_patcher = patch('redis.from_url')
mock_redis_client = mock_redis_patcher.start()
mock_redis_instance = Mock()
mock_redis_instance.ping.return_value = True
mock_redis_instance.rpush.return_value = 1
mock_redis_instance.llen.return_value = 0
mock_redis_instance.lrange.return_value = []
mock_redis_instance.get.return_value = None
mock_redis_instance.setex.return_value = True
mock_redis_instance.delete.return_value = 1
mock_redis_client.return_value = mock_redis_instance

from api.main import app

def cleanup_patches():
    mock_mlflow_patcher.stop()
    mock_load_patcher.stop()
    mock_redis_patcher.stop()

import atexit
atexit.register(cleanup_patches)

@pytest.fixture(scope="session")
def test_client():
    return TestClient(app)

@pytest.fixture(scope="session")
def sample_prediction_request():
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
    return {
        "batch_name": "test_batch",
        "data": [
            {
                "customer_id": f"CUST{i:03d}",
                "tenure": i % 72,
                "MonthlyCharges": 50.0 + i,
                "TotalCharges": (50.0 + i) * (i % 72) if (i % 72) > 0 else 50.0,
                "Contract": ["Month-to-month", "One year", "Two year"][i % 3],
                "InternetService": ["DSL", "Fiber optic", "No"][i % 3],
                "PaymentMethod": ["Electronic check", "Mailed check", "Bank transfer (automatic)", "Credit card (automatic)"][i % 4]
            }
            for i in range(10)
        ]
    }

@pytest.fixture(scope="session")
def api_keys():
    return {
        "admin": "admin-secret-key-change-in-production",
        "user": "user-secret-key-change-in-production",
        "readonly": "readonly-secret-key-change-in-production",
        "invalid": "invalid-key"
    }

@pytest.fixture
def mock_redis():
    return mock_redis_instance

@pytest.fixture
def mock_mlflow():
    return mock_model