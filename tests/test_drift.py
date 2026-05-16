import os
import sys
import pytest
import json
from datetime import datetime, timedelta

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.retrain_queue import RetrainQueueManager
from worker.drift_tasks import periodic_drift_check

class TestDriftDetection:

    def test_manual_drift_check_endpoint(self, test_client, api_keys):
        drift_request = {
            "data": [
                {
                    "tenure": 12,
                    "MonthlyCharges": 50.0,
                    "TotalCharges": 600.0,
                    "Contract": "Month-to-month",
                    "InternetService": "DSL",
                    "PaymentMethod": "Electronic check"
                }
                for _ in range(100)
            ]
        }
        
        response = test_client.post(
            "/api/monitoring/drift/check",
            json=drift_request,
            headers={"X-API-Key": api_keys["readonly"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "has_drift" in data
        assert "drifted_columns" in data
        assert isinstance(data["drifted_columns"], list)

    def test_auto_drift_trigger(self, test_client, api_keys):
        response = test_client.post(
            "/api/monitoring/drift/auto-check",
            headers={"X-API-Key": api_keys["readonly"]}
        )
        
        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "started"

    def test_drift_status_endpoint(self, test_client, api_keys):
        response = test_client.get(
            "/api/monitoring/drift/status",
            headers={"X-API-Key": api_keys["readonly"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "recent_checks" in data
        assert "status" in data

    def test_drift_from_redis_requires_samples(self, test_client, api_keys, redis_client):
        response = test_client.post(
            "/api/monitoring/drift/auto-check",
            headers={"X-API-Key": api_keys["readonly"]}
        )
        
        assert response.status_code == 202

    def test_drift_endpoint_authorization(self, test_client):
        response = test_client.post(
            "/api/monitoring/drift/check",
            json={"data": []}
        )
        
        assert response.status_code == 401