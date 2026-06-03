import os
import sys
import pytest
from unittest.mock import Mock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


class TestFeedbackAPI:

    def test_submit_feedback(self, api_client):
        with patch('shared.retrain_queue.RetrainQueueManager.update_label') as mock_update:
            mock_update.return_value = True
            response = api_client.post(
                "/feedback/pred_123",
                json={"actual_label": 0},
                role="user"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"

    def test_submit_feedback_not_found(self, api_client):
        with patch('shared.retrain_queue.RetrainQueueManager.update_label') as mock_update:
            mock_update.return_value = False
            response = api_client.post(
                "/feedback/invalid_id",
                json={"actual_label": 1},
                role="user"
            )
            assert response.status_code == 404

    def test_submit_batch_feedback(self, api_client):
        with patch('shared.retrain_queue.RetrainQueueManager.update_label') as mock_update:
            mock_update.return_value = True
            
            response = api_client.post(
                "/feedback/batch",
                json={
                    "feedbacks": [
                        {"prediction_id": "id1", "actual_label": 0},
                        {"prediction_id": "id2", "actual_label": 1}
                    ]
                },
                role="user"
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert data["succeeded"] == 2

    def test_collect_training_data(self, api_client):
        with patch('shared.retrain_queue.RetrainQueueManager.add_training_record') as mock_add:
            mock_add.return_value = True
            
            response = api_client.post(
                "/feedback/train-data",
                json={
                    "features": {"tenure": 12, "MonthlyCharges": 50.0},
                    "actual_label": 1,
                    "customer_id": "CUST-001"
                },
                role="user"
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"