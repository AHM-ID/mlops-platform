# tests/test_models.py
import os
import sys
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestModelsAPI:

    def test_list_models(self, api_client):
        mock_response = {
            "production": {
                "name": "churn_model",
                "version": "3",
                "stage": "Production",
                "created_date": "2024-01-01T00:00:00",
                "last_updated": "2024-01-01T00:00:00",
                "metrics": {"auc": 0.85}
            },
            "staging": None,
            "all_versions": []
        }

        with patch('api.services.model_service.ModelService.get_current_models') as mock_models:
            mock_models.return_value = mock_response

            response = api_client.get("/models/", role="user")

            assert response.status_code == 200
            data = response.json()
            assert "production" in data

    def test_get_current_model_version(self, api_client):
        with patch('api.services.model_service.ModelService.get_current_model_version') as mock_version:
            mock_version.return_value = {
                "model_name": "churn_model",
                "version": "3",
                "stage": "Production"
            }

            response = api_client.get("/models/current", role="user")

            assert response.status_code == 200
            data = response.json()
            assert data["version"] == "3"

    def test_get_model_details(self, api_client):
        mock_model = {
            "name": "churn_model",
            "version": "3",
            "stage": "Production",
            "created_date": "2024-01-01T00:00:00",
            "last_updated": "2024-01-01T00:00:00",
            "metrics": {"auc": 0.85}
        }

        with patch('api.services.model_service.ModelService.get_model_details') as mock_details:
            mock_details.return_value = mock_model

            response = api_client.get("/models/churn_model", role="user")

            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "churn_model"

    def test_deploy_model(self, api_client):
        with patch('api.services.model_service.ModelService.deploy_model') as mock_deploy:
            mock_deploy.return_value = True

            response = api_client.post(
                "/models/deploy",
                json={
                    "model_name": "churn_model",
                    "version": "4",
                    "target_stage": "Production"
                },
                role="admin"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    def test_trigger_retrain(self, api_client):
        with patch('worker.celery_app.retrain.delay') as mock_retrain:
            mock_task = Mock()
            mock_task.id = "task_123"
            mock_retrain.return_value = mock_task

            response = api_client.post("/models/retrain", role="admin")

            assert response.status_code == 202
            data = response.json()
            assert data["task_id"] == "task_123"
            assert data["status"] == "submitted"

    def test_get_retrain_status(self, api_client):
        with patch('worker.celery_app.app.AsyncResult') as mock_async:
            mock_task = Mock()
            mock_task.state = "SUCCESS"
            mock_task.ready.return_value = True
            mock_task.result = {"status": "success"}
            mock_async.return_value = mock_task

            response = api_client.get("/models/retrain/task_123/status", role="user")

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"