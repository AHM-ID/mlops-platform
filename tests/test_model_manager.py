import os
import sys
import pytest
from unittest.mock import Mock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from shared.model_manager import ModelManager

class TestModelManager:
    
    def test_get_model_versions(self, mock_mlflow):
        manager = ModelManager()
        versions = manager.get_model_versions()
        
        assert isinstance(versions, list)
    
    def test_get_best_model_by_metric(self, mock_mlflow):
        manager = ModelManager()
        
        with patch.object(manager, 'get_model_versions') as mock_versions:
            mock_version = Mock()
            mock_version.version = "2"
            mock_version.run_id = "run_123"
            mock_versions.return_value = [mock_version]
            
            model, metrics = manager.get_best_model_by_metric("auc")
            
            assert model is not None
    
    def test_load_production_model(self, mock_mlflow):
        manager = ModelManager()
        
        with patch('mlflow.pyfunc.load_model') as mock_load:
            mock_load.return_value = Mock()
            model, metrics = manager.load_production_model()
            
            assert model is not None
    
    def test_compare_performance(self, mock_mlflow):
        manager = ModelManager()
        
        with patch.object(manager, 'get_model_versions') as mock_versions:
            mock_version = Mock()
            mock_version.version = "1"
            mock_version.stage = "Production"
            mock_versions.return_value = [mock_version]
            
            comparison = manager.compare_performance()
            
            assert isinstance(comparison, dict)