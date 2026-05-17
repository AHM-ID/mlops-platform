import os
import sys
import pytest
from datetime import datetime
from unittest.mock import Mock, patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.services.model_service import ModelService
from api.schemas import ModelMetadata

class TestModelService:
    
    def test_get_current_models(self, mock_mlflow):
        service = ModelService()
        
        with patch.object(service.client, 'search_model_versions') as mock_search:
            mock_version = Mock()
            mock_version.name = "churn_model"
            mock_version.version = "1"
            mock_version.current_stage = "Production"
            mock_version.creation_timestamp = 1609459200000
            mock_version.last_updated_timestamp = 1609459200000
            mock_version.run_id = "run_123"
            mock_search.return_value = [mock_version]
            
            real_metadata = ModelMetadata(
                name="churn_model",
                version="1",
                stage="Production",
                created_date=datetime.now(),
                last_updated=datetime.now(),
                metrics={"auc": 0.85}
            )
            
            with patch.object(service, '_version_to_metadata', return_value=real_metadata):
                result = service.get_current_models()
                
                assert result is not None
                assert result.production is not None
                assert result.production.version == "1"
    
    def test_get_model_details_not_found(self, mock_mlflow):
        service = ModelService()
        
        with patch.object(service.client, 'get_latest_versions') as mock_versions:
            mock_versions.return_value = []
            result = service.get_model_details("nonexistent_model")
            
            assert result is None
    
    def test_list_model_versions(self, mock_mlflow):
        service = ModelService()
        
        with patch.object(service.client, 'search_model_versions') as mock_search:
            mock_version = Mock()
            mock_version.name = "churn_model"
            mock_version.version = "1"
            mock_search.return_value = [mock_version]
            
            real_metadata = ModelMetadata(
                name="churn_model",
                version="1",
                stage="None",
                created_date=datetime.now(),
                last_updated=datetime.now(),
                metrics={}
            )
            
            with patch.object(service, '_version_to_metadata', return_value=real_metadata):
                versions = service.list_model_versions("churn_model")
                
                assert isinstance(versions, list)
                assert len(versions) == 1
    
    def test_deploy_model(self, mock_mlflow):
        service = ModelService()
        
        with patch.object(service.client, 'transition_model_version_stage') as mock_transition:
            with patch.object(service.client, 'get_latest_versions', return_value=[]):
                result = service.deploy_model("churn_model", "1", "Production")
                
                assert result is True