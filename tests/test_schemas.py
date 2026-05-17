import os
import sys
import pytest
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.schemas import PredictionRequest, PredictionResponse, BatchPredictionRequest, ModelMetadata

class TestSchemas:
    
    def test_prediction_request_valid(self):
        request = PredictionRequest(
            customer_id="TEST001",
            tenure=24,
            MonthlyCharges=75.5,
            TotalCharges=1814.0,
            Contract="Two year",
            InternetService="Fiber optic",
            PaymentMethod="Electronic check"
        )
        
        assert request.tenure == 24
        assert request.Contract == "Two year"
    
    def test_prediction_request_invalid_contract(self):
        with pytest.raises(ValueError):
            PredictionRequest(
                customer_id="TEST001",
                tenure=24,
                MonthlyCharges=75.5,
                TotalCharges=1814.0,
                Contract="Invalid Contract",
                InternetService="Fiber optic",
                PaymentMethod="Electronic check"
            )
    
    def test_prediction_request_invalid_tenure(self):
        with pytest.raises(ValueError):
            PredictionRequest(
                customer_id="TEST001",
                tenure=-5,
                MonthlyCharges=75.5,
                TotalCharges=1814.0,
                Contract="Two year",
                InternetService="Fiber optic",
                PaymentMethod="Electronic check"
            )
    
    def test_prediction_response(self):
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
    
    def test_batch_prediction_request(self):
        request = BatchPredictionRequest(
            batch_name="test_batch",
            data=[]
        )
        
        assert request.batch_name == "test_batch"
    
    def test_model_metadata(self):
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