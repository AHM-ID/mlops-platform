# tests/test_drift.py
import os
import sys
import pytest
from unittest.mock import Mock, patch, MagicMock

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestDriftAPI:

    def test_trigger_drift_check(self, api_client):
        with patch('worker.drift_tasks.periodic_drift_check.delay') as mock_drift:
            mock_task = Mock()
            mock_task.id = "drift_task_123"
            mock_drift.return_value = mock_task

            response = api_client.post("/drift/auto-check", role="user")

            assert response.status_code == 202
            data = response.json()
            assert data["task_id"] == "drift_task_123"

    def test_get_drift_status(self, api_client):
        mock_df = MagicMock()

        def getitem_side_effect(key):
            if key == "metrics.dataset_drift":
                return 0
            elif key == "run_id":
                return "run1"
            elif key == "start_time":
                return 1609459200000
            return None

        mock_df.__getitem__ = MagicMock(side_effect=getitem_side_effect)

        with patch('mlflow.get_experiment_by_name') as mock_exp:
            mock_exp.return_value = Mock(experiment_id="123")

            with patch('mlflow.search_runs') as mock_search:
                mock_search.return_value = mock_df

                response = api_client.get("/drift/status", role="user")

                assert response.status_code == 200
                data = response.json()
                assert "recent_checks" in data

    def test_trigger_retrain_on_drift(self, api_client):
        with patch('worker.celery_app.retrain.delay') as mock_retrain:
            mock_task = Mock()
            mock_task.id = "retrain_task_123"
            mock_retrain.return_value = mock_task

            response = api_client.post("/drift/retrain", role="user")

            assert response.status_code == 202
            data = response.json()
            assert data["task_id"] == "retrain_task_123"

    def test_drift_check_with_custom_data(self, api_client, sample_prediction_request):
        with patch('api.routers.drift.run_drift_report') as mock_report:
            mock_report.return_value = {
                "has_drift": False,
                "drifted_columns": [],
                "report_path": "/tmp/report.html"
            }

            response = api_client.post(
                "/drift/check",
                json={"data": [sample_prediction_request]},
                role="user"
            )

            assert response.status_code == 200
            data = response.json()
            assert "has_drift" in data