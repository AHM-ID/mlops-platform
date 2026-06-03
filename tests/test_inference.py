# tests/test_inference.py
import os
import sys
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestInferenceAPI:

    def test_single_prediction_endpoint(self, api_client, sample_prediction_request, mock_mlflow):
        with patch('api.services.prediction_service.PredictionService.predict') as mock_predict:
            mock_predict.return_value = (0, 0.23, "1", "test_pred_id")

            response = api_client.post("/inference/single", json=sample_prediction_request, role="user")

            assert response.status_code == 200
            data = response.json()
            assert "prediction" in data
            assert "probability" in data
            assert "model_version" in data

    def test_single_prediction_requires_auth(self, api_client, sample_prediction_request):
        response = api_client.client.post("/inference/single", json=sample_prediction_request)
        assert response.status_code == 401

    def test_batch_prediction_endpoint(self, api_client, sample_batch_requests):
        with patch('api.services.batch_service.BatchService.submit_batch') as mock_submit:
            mock_submit.return_value = Mock(
                batch_id="test_batch_123",
                status="submitted",
                total_records=10,
                celery_task_id="task_123",
                created_at=datetime.now()
            )

            response = api_client.post("/inference/batch", json=sample_batch_requests, role="user")

            assert response.status_code == 202
            data = response.json()
            assert "batch_id" in data
            assert data["status"] == "submitted"

    def test_get_batch_status(self, api_client):
        with patch('api.services.batch_service.BatchService.get_batch_job_status') as mock_status:
            mock_status.return_value = {
                "batch_id": "batch_123",
                "status": "completed",
                "progress": 100,
                "total_records": 10,
                "processed_records": 10,
                "created_at": "2024-01-01T00:00:00",
                "started_at": "2024-01-01T00:00:00",
                "completed_at": "2024-01-01T00:01:00",
                "celery_task_id": "task_123"
            }

            response = api_client.get("/inference/batch/batch_123", role="user")

            assert response.status_code == 200
            data = response.json()
            assert data["batch_id"] == "batch_123"
            assert data["status"] == "completed"

    def test_list_batches(self, api_client):
        with patch('api.services.batch_service.BatchService.list_recent_jobs') as mock_list:
            mock_list.return_value = [
                {
                    "batch_id": "batch_1",
                    "status": "completed",
                    "progress": 100,
                    "total_records": 100,
                    "processed_records": 100,
                    "created_at": "2024-01-01T00:00:00",
                    "started_at": "2024-01-01T00:00:00",
                    "completed_at": "2024-01-01T00:01:00",
                    "celery_task_id": "task_1"
                },
                {
                    "batch_id": "batch_2",
                    "status": "processing",
                    "progress": 50,
                    "total_records": 50,
                    "processed_records": 25,
                    "created_at": "2024-01-01T00:00:00",
                    "started_at": "2024-01-01T00:00:00",
                    "completed_at": None,
                    "celery_task_id": "task_2"
                }
            ]

            response = api_client.get("/inference/batches?limit=10", role="user")

            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 2

    def test_delete_batch(self, api_client):
        mock_status = {
            "batch_id": "batch_123",
            "status": "completed",
            "progress": 100,
            "total_records": 10,
            "processed_records": 10,
            "created_at": "2024-01-01T00:00:00",
            "celery_task_id": "task_123"
        }

        with patch('api.services.batch_service.BatchService.get_batch_job_status') as mock_status_get:
            mock_status_get.return_value = mock_status

            with patch('api.services.batch_service.BatchService.delete_batch') as mock_delete:
                mock_delete.return_value = True

                response = api_client.delete("/inference/batch/batch_123", role="admin")

                assert response.status_code == 204