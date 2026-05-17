import os
import sys
import pytest
import pandas as pd
from unittest.mock import Mock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.services.prediction_service import PredictionService
from api.schemas import PredictionRequest

class TestPredictionService:
    
    def test_prediction_service_initialization(self, mock_mlflow):
        import os
        original_testing = os.environ.get("TESTING", "true")
        os.environ["TESTING"] = "false"
        
        with patch('shared.feature_store.redis_client', None):
            with patch.object(PredictionService, '_load_model') as mock_load:
                mock_load.return_value = None
                service = PredictionService()
                assert service._model is None
        
        os.environ["TESTING"] = original_testing

    def test_predict_method(self, mock_mlflow):
        import os
        original_testing = os.environ.get("TESTING", "true")
        os.environ["TESTING"] = "false"
        
        with patch('shared.feature_store.redis_client', None):
            with patch('joblib.load') as mock_joblib_load:
                mock_joblib_load.return_value = ["tenure", "MonthlyCharges", "TotalCharges", "Contract_Month-to-month", "Contract_One year", "Contract_Two year", "InternetService_DSL", "InternetService_Fiber optic", "InternetService_No", "PaymentMethod_Electronic check", "PaymentMethod_Mailed check", "PaymentMethod_Bank transfer (automatic)", "PaymentMethod_Credit card (automatic)"]
                
                with patch('mlflow.pyfunc.load_model', return_value=mock_mlflow):
                    service = PredictionService()
                    
                    request = PredictionRequest(
                        customer_id="TEST001",
                        tenure=24,
                        MonthlyCharges=75.5,
                        TotalCharges=1814.0,
                        Contract="Two year",
                        InternetService="Fiber optic",
                        PaymentMethod="Electronic check"
                    )
                    
                    pred, prob, version, pred_id = service.predict(request)
                    
                    assert pred in [0, 1]
                    assert 0 <= prob <= 1
                    assert version is not None
        
        os.environ["TESTING"] = original_testing