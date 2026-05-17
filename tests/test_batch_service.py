import os
import sys
import pytest
import json
from unittest.mock import Mock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.services.batch_service import BatchService
from api.schemas import PredictionRequest

class TestBatchService:
    
    def test_create_batch(self):
        with patch('api.services.batch_service.redis.from_url') as mock_redis, \
            patch('worker.batch_predictor.batch_predict') as mock_task:
            
            import os
            os.environ["TESTING"] = "false"
            
            mock_client = Mock()
            mock_redis.return_value = mock_client
            mock_task.delay.return_value.id = "task_123"
            
            service = BatchService()
            
            requests = [
                PredictionRequest(
                    customer_id="TEST001",
                    tenure=24,
                    MonthlyCharges=75.5,
                    TotalCharges=1814.0,
                    Contract="Two year",
                    InternetService="Fiber optic",
                    PaymentMethod="Electronic check"
                )
            ]
            
            batch_id = service.create_batch(requests, "test_batch")
            
            assert batch_id.startswith("batch_")
            assert mock_client.setex.called
            
            os.environ["TESTING"] = "true"

    def test_get_batch_status_not_found(self):
        with patch('api.services.batch_service.redis.from_url') as mock_redis:
            mock_client = Mock()
            mock_client.get.return_value = None
            mock_redis.return_value = mock_client
            
            import os
            os.environ["TESTING"] = "false"
            
            service = BatchService()
            status = service.get_batch_status("invalid_id")
            
            assert status is None
            
            os.environ["TESTING"] = "true"
    
    def test_list_recent_jobs_empty(self):
        with patch('api.services.batch_service.redis.from_url') as mock_redis:
            mock_client = Mock()
            mock_client.keys.return_value = []
            mock_redis.return_value = mock_client
            
            service = BatchService()
            jobs = service.list_recent_jobs()
            
            assert jobs == []
    
    def test_delete_batch(self):
        with patch('api.services.batch_service.redis.from_url') as mock_redis:
            mock_client = Mock()
            mock_redis.return_value = mock_client
            
            service = BatchService()
            result = service.delete_batch("test_batch_id")
            
            assert result is True