import os
import sys
import pytest
import time
import json

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.config import REDIS_URL
import redis

class TestPredictionAPI:

    def test_single_prediction_success(self, test_client, sample_prediction_request, api_keys):
        response = test_client.post(
            "/api/predictions/single",
            json=sample_prediction_request,
            headers={"X-API-Key": api_keys["user"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "prediction" in data
        assert "probability" in data
        assert "confidence" in data
        assert "model_version" in data
        assert "prediction_id" in data
        assert data["prediction"] in [0, 1]
        assert 0 <= data["probability"] <= 1

    def test_single_prediction_authentication_failure(self, test_client, sample_prediction_request):
        response = test_client.post(
            "/api/predictions/single",
            json=sample_prediction_request,
            headers={"X-API-Key": "wrong-key"}
        )
        
        assert response.status_code == 401

    def test_single_prediction_missing_api_key(self, test_client, sample_prediction_request):
        response = test_client.post(
            "/api/predictions/single",
            json=sample_prediction_request
        )
        
        assert response.status_code == 401

    def test_single_prediction_invalid_input(self, test_client, api_keys):
        invalid_request = {
            "customer_id": "TEST001",
            "tenure": -5,
            "MonthlyCharges": 75.5,
            "TotalCharges": 1814.0,
            "Contract": "Invalid Contract",
            "InternetService": "Fiber optic",
            "PaymentMethod": "Electronic check"
        }
        
        response = test_client.post(
            "/api/predictions/single",
            json=invalid_request,
            headers={"X-API-Key": api_keys["user"]}
        )
        
        assert response.status_code == 422

    def test_batch_prediction_submission(self, test_client, sample_batch_requests, api_keys):
        response = test_client.post(
            "/api/predictions/batch",
            json=sample_batch_requests,
            headers={"X-API-Key": api_keys["admin"]}
        )
        
        assert response.status_code == 202
        data = response.json()
        assert "batch_id" in data
        assert data["status"] == "submitted"
        assert data["total_records"] == len(sample_batch_requests["data"])

    def test_batch_prediction_readonly_denied(self, test_client, sample_batch_requests, api_keys):
        response = test_client.post(
            "/api/predictions/batch",
            json=sample_batch_requests,
            headers={"X-API-Key": api_keys["readonly"]}
        )
        
        assert response.status_code == 403

    def test_batch_status_check(self, test_client, sample_batch_requests, api_keys):
        submit = test_client.post(
            "/api/predictions/batch",
            json=sample_batch_requests,
            headers={"X-API-Key": api_keys["admin"]}
        )
        batch_id = submit.json()["batch_id"]
        
        response = test_client.get(
            f"/api/predictions/batch/{batch_id}/status",
            headers={"X-API-Key": api_keys["readonly"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["batch_id"] == batch_id
        assert data["status"] in ["submitted", "processing", "completed", "failed"]

    def test_rate_limiting(self, test_client, sample_prediction_request, api_keys):
        for _ in range(110):
            test_client.post(
                "/api/predictions/single",
                json=sample_prediction_request,
                headers={"X-API-Key": api_keys["user"]}
            )
        
        response = test_client.post(
            "/api/predictions/single",
            json=sample_prediction_request,
            headers={"X-API-Key": api_keys["user"]}
        )
        
        assert response.status_code == 429

    def test_prediction_caching(self, test_client, sample_prediction_request, api_keys):
        r = redis.from_url(REDIS_URL, decode_responses=True)
        initial_hits = int(r.get("cache_total_hits") or 0)
        
        for _ in range(5):
            test_client.post(
                "/api/predictions/single",
                json=sample_prediction_request,
                headers={"X-API-Key": api_keys["user"]}
            )
        
        final_hits = int(r.get("cache_total_hits") or 0)
        assert final_hits > initial_hits

    def test_health_endpoint(self, test_client):
        response = test_client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"