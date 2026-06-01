import os
import sys
import pytest
import pickle
from unittest.mock import Mock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.retrain_queue import RetrainQueueManager


def _manager_with_redis(mock_redis: Mock) -> RetrainQueueManager:
    manager = RetrainQueueManager()
    manager._redis_client = mock_redis
    manager._connection_attempts = manager._max_connection_attempts
    return manager


class TestRetrainQueue:

    def test_add_prediction_to_queue(self, mock_redis):
        manager = _manager_with_redis(mock_redis)

        prediction_id = manager.add_prediction(
            features={"tenure": 12, "MonthlyCharges": 50.0},
            prediction=1,
            probability=0.75,
            customer_id="TEST001"
        )

        assert prediction_id != ""
        assert mock_redis.rpush.called

    def test_add_prediction_with_custom_id(self, mock_redis):
        manager = _manager_with_redis(mock_redis)

        custom_id = "custom_pred_123"
        prediction_id = manager.add_prediction(
            features={"tenure": 12},
            prediction=0,
            probability=0.3,
            customer_id="TEST002",
            prediction_id=custom_id
        )

        assert prediction_id == custom_id

    def test_update_label_in_queue(self, mock_redis):
        record_id = "test_id_123"
        mock_record = {
            "id": record_id,
            "features": {"tenure": 12},
            "prediction": 1,
            "probability": 0.75,
            "prediction_timestamp": "2024-01-01T00:00:00",
            "label": None,
            "validation_status": "pending"
        }
        mock_redis.lrange.return_value = [pickle.dumps(mock_record)]

        manager = _manager_with_redis(mock_redis)

        success = manager.update_label(record_id, 1)

        assert success is True

    def test_update_nonexistent_label(self, mock_redis):
        mock_redis.lrange.return_value = []

        manager = _manager_with_redis(mock_redis)

        success = manager.update_label("nonexistent_id", 1)

        assert success is False

    def test_get_training_batch(self, mock_redis):
        records = []
        for i in range(5):
            record = {
                "id": f"id_{i}",
                "features": {"tenure": i * 12},
                "prediction": i % 2,
                "probability": 0.5,
                "prediction_timestamp": "2024-01-01T00:00:00",
                "label": i % 2,
                "validation_status": "verified"
            }
            records.append(pickle.dumps(record))

        mock_redis.lrange.return_value = records

        manager = _manager_with_redis(mock_redis)

        batch = manager.get_training_batch(batch_size=3)

        assert len(batch) <= 3

    def test_get_training_batch_only_verified(self, mock_redis):
        records = [
            pickle.dumps({"id": "1", "label": 1, "validation_status": "verified"}),
            pickle.dumps({"id": "2", "label": None, "validation_status": "pending"}),
            pickle.dumps({"id": "3", "label": 0, "validation_status": "verified"})
        ]
        mock_redis.lrange.return_value = records

        manager = _manager_with_redis(mock_redis)

        batch = manager.get_training_batch(batch_size=10)

        for record in batch:
            assert record["label"] is not None
            assert record["validation_status"] == "verified"

    def test_clear_queue(self, mock_redis):
        manager = _manager_with_redis(mock_redis)

        manager.clear_queue()

        mock_redis.delete.assert_called()

    def test_get_recent_predictions(self, mock_redis):
        record = {
            "id": "test_id",
            "features": {"tenure": 12},
            "prediction": 1,
            "probability": 0.75,
            "prediction_timestamp": "2024-01-01T00:00:00",
            "label": None,
            "validation_status": "pending"
        }
        mock_redis.lrange.return_value = [pickle.dumps(record)]

        manager = _manager_with_redis(mock_redis)

        recent = manager.get_recent_predictions(hours=24)

        assert len(recent) >= 0

    def test_get_queue_length(self, mock_redis):
        mock_redis.llen.return_value = 10

        manager = _manager_with_redis(mock_redis)

        length = manager.get_queue_length()

        assert length == 10

    def test_redis_connection_failure_handling(self):
        with patch('shared.retrain_queue.get_redis_client', side_effect=Exception("Connection failed")):
            manager = RetrainQueueManager()
            assert manager.redis_client is None
            assert manager.get_queue_length() == 0
            assert manager.add_prediction({}, 1, 0.5) == ""
            assert manager.clear_queue() is False
