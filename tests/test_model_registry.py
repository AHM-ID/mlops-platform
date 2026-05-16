import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from api.services.model_service import ModelService

class TestModelRegistry:

    def test_get_current_models(self, test_client, api_keys):
        response = test_client.get(
            "/api/models/current",
            headers={"X-API-Key": api_keys["readonly"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "production" in data
        assert "staging" in data
        assert "all_versions" in data

    def test_get_model_details(self, test_client, api_keys):
        response = test_client.get(
            "/api/models/churn_model",
            headers={"X-API-Key": api_keys["readonly"]}
        )
        
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "name" in data
            assert "version" in data

    def test_list_model_versions(self, test_client, api_keys):
        response = test_client.get(
            "/api/models/churn_model/versions",
            headers={"X-API-Key": api_keys["readonly"]}
        )
        
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)

    def test_deploy_model_requires_admin(self, test_client, api_keys):
        deploy_request = {
            "model_name": "churn_model",
            "version": "1",
            "target_stage": "Production"
        }
        
        response = test_client.post(
            "/api/models/deploy",
            json=deploy_request,
            headers={"X-API-Key": api_keys["user"]}
        )
        
        assert response.status_code == 403

    def test_current_model_version_endpoint(self, test_client, api_keys):
        response = test_client.get(
            "/api/models/health/model-version",
            headers={"X-API-Key": api_keys["readonly"]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "model_name" in data or "version" in data