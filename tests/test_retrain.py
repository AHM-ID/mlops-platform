import os
import sys
import pytest
import time
from unittest.mock import patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.retrain_queue import RetrainQueueManager

class TestRetrainQueue:

    def test_add_prediction_to_queue(self, redis_client):
        queue = RetrainQueueManager()
        
        prediction_id = queue.add_prediction(
            features={"tenure": 12, "MonthlyCharges": 50.0},
            prediction=1,
            probability=0.75,
            customer_id="TEST001"
        )
        
        assert prediction_id != ""
        assert queue.get_queue_length() == 1

    def test_update_label_in_queue(self, redis_client):
        queue = RetrainQueueManager()
        
        prediction_id = queue.add_prediction(
            features={"tenure": 12, "MonthlyCharges": 50.0},
            prediction=1,
            probability=0.75,
            customer_id="TEST001"
        )
        
        success = queue.update_label(prediction_id, 1)
        assert success is True

    def test_get_training_batch(self, redis_client):
        queue = RetrainQueueManager()
        
        for i in range(10):
            pid = queue.add_prediction(
                features={"tenure": i, "MonthlyCharges": 50.0},
                prediction=i % 2,
                probability=0.5,
                customer_id=f"TEST{i:03d}"
            )
            queue.update_label(pid, i % 2)
        
        batch = queue.get_training_batch(batch_size=5)
        
        assert len(batch) == 5
        assert all("label" in record for record in batch)
        assert all(record["label"] is not None for record in batch)

    def test_clear_queue(self, redis_client):
        queue = RetrainQueueManager()
        
        queue.add_prediction({"tenure": 12}, 1, 0.75, "TEST001")
        assert queue.get_queue_length() == 1
        
        queue.clear_queue()
        assert queue.get_queue_length() == 0

    def test_get_recent_predictions(self, redis_client):
        queue = RetrainQueueManager()
        
        queue.add_prediction({"tenure": 12}, 1, 0.75, "TEST001")
        
        recent = queue.get_recent_predictions(hours=24)
        
        assert len(recent) == 1

    def test_trigger_retrain_endpoint(self, test_client, api_keys):
        response = test_client.post(
            "/api/retrain",
            headers={"X-API-Key": api_keys["admin"]}
        )
        
        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "submitted"

    def test_retrain_readonly_denied(self, test_client, api_keys):
        response = test_client.post(
            "/api/retrain",
            headers={"X-API-Key": api_keys["readonly"]}
        )
        
        assert response.status_code == 403

    def test_retrain_queue_status_endpoint(self, test_client, api_keys, redis_client):
        queue = RetrainQueueManager()
        queue.add_prediction({"tenure": 12}, 1, 0.75, "TEST001")
        
        response = test_client.get(
            "/api/retrain-queue/status",
            headers={"X-API-Key": api_keys["readonly"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "queue_length" in data
        assert data["queue_length"] >= 1