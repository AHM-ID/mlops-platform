# tests/conftest.py
"""
Pytest configuration for isolated unit tests.

No live Postgres, Redis, MLflow, or other platform services are required.
External I/O is mocked at the client boundary.
"""

from __future__ import annotations

import os
import sys
import tempfile
from contextlib import ExitStack
from unittest.mock import Mock, patch

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def _configure_test_env() -> None:
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
    os.environ.setdefault("API_KEY_ADMIN", "admin-secret-key-change-in-production")
    os.environ.setdefault("API_KEY_USER", "user-secret-key-change-in-production")
    os.environ.setdefault("API_KEY_READONLY", "readonly-secret-key-change-in-production")

    prometheus_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if not prometheus_dir:
        prometheus_dir = tempfile.mkdtemp(prefix="prometheus-test-")
        os.environ["PROMETHEUS_MULTIPROC_DIR"] = prometheus_dir


_configure_test_env()


def _build_mlflow_mocks() -> tuple[Mock, Mock]:
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

    mock_model = Mock()
    mock_model.predict.return_value = [0]
    mock_model.predict_proba.return_value = [[0.3, 0.7]]

    return mock_client_instance, mock_model


def _build_redis_mock() -> Mock:
    mock_redis_instance = Mock()
    mock_redis_instance.ping.return_value = True
    mock_redis_instance.rpush.return_value = 1
    mock_redis_instance.llen.return_value = 0
    mock_redis_instance.lrange.return_value = []
    mock_redis_instance.get.return_value = None
    mock_redis_instance.setex.return_value = True
    mock_redis_instance.delete.return_value = 1
    mock_redis_instance.pipeline.return_value = mock_redis_instance
    mock_redis_instance.execute.return_value = []
    mock_redis_instance.scan.return_value = (0, [])
    return mock_redis_instance


@pytest.fixture(scope="session")
def mock_redis(_mock_external_services) -> Mock:
    return _mock_state["redis"]


@pytest.fixture(scope="session")
def mock_mlflow(_mock_external_services) -> Mock:
    return _mock_state["mlflow_model"]


@pytest.fixture(scope="session")
def app(_mock_external_services):
    if "app" not in _mock_state:
        from api.main import app as fastapi_app
        _mock_state["app"] = fastapi_app
    return _mock_state["app"]


@pytest.fixture(scope="session")
def test_client(app):
    from fastapi.testclient import TestClient
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
def api_client(test_client):
    class ApiClient:
        def __init__(self, client):
            self.client = client

        def _add_auth(self, headers, role="user"):
            if headers is None:
                headers = {}
            if "X-API-Key" not in headers:
                if role == "admin":
                    headers["X-API-Key"] = os.environ["API_KEY_ADMIN"]
                elif role == "user":
                    headers["X-API-Key"] = os.environ["API_KEY_USER"]
                elif role == "readonly":
                    headers["X-API-Key"] = os.environ["API_KEY_READONLY"]
            return headers

        def get(self, path, headers=None, role="user"):
            headers = self._add_auth(headers, role)
            return self.client.get(f"{path}", headers=headers)

        def post(self, path, json=None, headers=None, role="user"):
            headers = self._add_auth(headers, role)
            return self.client.post(f"{path}", json=json, headers=headers)

        def delete(self, path, headers=None, role="user"):
            headers = self._add_auth(headers, role)
            return self.client.delete(f"{path}", headers=headers)

    return ApiClient(test_client)


@pytest.fixture(scope="session")
def sample_prediction_request():
    return {
        "customer_id": "TEST001",
        "gender": "Female",
        "SeniorCitizen": 0,
        "Partner": "Yes",
        "Dependents": "No",
        "tenure": 24,
        "PhoneService": "Yes",
        "MultipleLines": "No",
        "InternetService": "Fiber optic",
        "OnlineSecurity": "No",
        "OnlineBackup": "Yes",
        "DeviceProtection": "No",
        "TechSupport": "No",
        "StreamingTV": "Yes",
        "StreamingMovies": "No",
        "Contract": "Two year",
        "PaperlessBilling": "Yes",
        "PaymentMethod": "Electronic check",
        "MonthlyCharges": 75.5,
        "TotalCharges": 1814.0,
    }


@pytest.fixture(scope="session")
def sample_batch_requests():
    return {
        "batch_name": "test_batch",
        "data": [
            {
                "customer_id": f"CUST{i:03d}",
                "gender": "Male" if i % 2 == 0 else "Female",
                "SeniorCitizen": i % 2,
                "Partner": "Yes" if i % 2 == 0 else "No",
                "Dependents": "No",
                "tenure": i % 72,
                "PhoneService": "Yes",
                "MultipleLines": "No",
                "InternetService": ["DSL", "Fiber optic", "No"][i % 3],
                "OnlineSecurity": "No",
                "OnlineBackup": "Yes",
                "DeviceProtection": "No",
                "TechSupport": "No",
                "StreamingTV": "Yes",
                "StreamingMovies": "No",
                "Contract": ["Month-to-month", "One year", "Two year"][i % 3],
                "PaperlessBilling": "Yes",
                "PaymentMethod": [
                    "Electronic check", "Mailed check",
                    "Bank transfer (automatic)", "Credit card (automatic)"
                ][i % 4],
                "MonthlyCharges": 50.0 + i,
                "TotalCharges": (50.0 + i) * (i % 72) if (i % 72) > 0 else 50.0,
            }
            for i in range(10)
        ],
    }


@pytest.fixture(scope="session")
def api_keys():
    return {
        "admin": os.environ["API_KEY_ADMIN"],
        "user": os.environ["API_KEY_USER"],
        "readonly": os.environ["API_KEY_READONLY"],
        "invalid": "invalid-key",
    }


_mock_state: dict = {}


@pytest.fixture(scope="session", autouse=True)
def _mock_external_services():
    mock_client_instance, mock_model = _build_mlflow_mocks()
    mock_redis_instance = _build_redis_mock()

    stack = ExitStack()
    stack.enter_context(patch("redis.from_url", return_value=mock_redis_instance))
    stack.enter_context(patch("shared.config.get_redis_client", return_value=mock_redis_instance))
    stack.enter_context(patch("mlflow.tracking.MlflowClient", return_value=mock_client_instance))
    stack.enter_context(patch("mlflow.pyfunc.load_model", return_value=mock_model))
    stack.enter_context(patch("mlflow.set_tracking_uri"))
    stack.enter_context(patch("shared.logging.SyncHTTPHandler.emit"))

    _mock_state["redis"] = mock_redis_instance
    _mock_state["mlflow_model"] = mock_model

    yield

    stack.close()
    _mock_state.clear()


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "integration" not in item.keywords:
            item.add_marker(pytest.mark.unit)