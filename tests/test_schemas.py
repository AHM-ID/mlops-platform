import os
import sys
import pytest
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.schemas import PredictionRequest, PredictionResponse, BatchPredictionRequest, ModelMetadata


class TestSchemas:
    
    def test_prediction_request_valid(self, sample_prediction_request):
        """Test valid prediction request with all required fields"""
        request = PredictionRequest(**sample_prediction_request)
        assert request.tenure == 24
        assert request.Contract == "Two year"
        assert request.gender == "Female"
    
    def test_prediction_request_invalid_contract(self, sample_prediction_request):
        """Test invalid contract value"""
        invalid_data = sample_prediction_request.copy()
        invalid_data["Contract"] = "Invalid Contract"
        with pytest.raises(ValueError):
            PredictionRequest(**invalid_data)
    
    def test_prediction_request_invalid_tenure(self, sample_prediction_request):
        """Test invalid tenure (negative)"""
        invalid_data = sample_prediction_request.copy()
        invalid_data["tenure"] = -5
        with pytest.raises(ValueError):
            PredictionRequest(**invalid_data)
    
    def test_prediction_request_invalid_senior_citizen(self, sample_prediction_request):
        """Test invalid SeniorCitizen (not 0 or 1)"""
        invalid_data = sample_prediction_request.copy()
        invalid_data["SeniorCitizen"] = 2
        with pytest.raises(ValueError):
            PredictionRequest(**invalid_data)
    
    def test_prediction_response(self):
        """Test prediction response schema"""
        response = PredictionResponse(
            customer_id="TEST001",
            prediction=1,
            probability=0.75,
            confidence=75.0,
            model_version="1",
            prediction_id="pred_123"
        )
        assert response.prediction == 1
        assert response.probability == 0.75
    
    def test_batch_prediction_request(self, sample_batch_requests):
        """Test batch prediction request with data"""
        request = BatchPredictionRequest(**sample_batch_requests)
        assert request.batch_name == "test_batch"
        assert len(request.data) == 10
    
    def test_model_metadata(self):
        """Test model metadata schema"""
        metadata = ModelMetadata(
            name="test_model",
            version="1",
            stage="Production",
            created_date=datetime.now(),
            last_updated=datetime.now(),
            metrics={"accuracy": 0.85}
        )
        assert metadata.name == "test_model"
        assert metadata.metrics["accuracy"] == 0.85