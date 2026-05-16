"""
Model Service
Business logic for model management and deployment
"""

from typing import List, Optional, Dict
import mlflow
from datetime import datetime

from api.schemas import ModelMetadata, ModelListResponse
from shared.config import MODEL_NAME, MLFLOW_TRACKING_URI
from shared.feature_store import clear_cache_for_model_version
from shared.logging import setup_logging

logger = setup_logging("model_service")


class ModelService:
    """Service for managing ML models in MLflow"""
    
    def __init__(self):
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        self.client = mlflow.tracking.MlflowClient()
        self.model_name = MODEL_NAME

    def get_current_models(self) -> ModelListResponse:
        """Get current production/staging + all versions"""
        try:
            production_model = None
            staging_model = None
            all_versions = []

            versions = self.client.search_model_versions(f"name='{self.model_name}'")

            for version in versions:
                model_meta = self._version_to_metadata(version)
                all_versions.append(model_meta)
                
                if version.current_stage == "Production":
                    if production_model is None or int(version.version) > int(production_model.version):
                        production_model = model_meta
                elif version.current_stage == "Staging":
                    if staging_model is None or int(version.version) > int(staging_model.version):
                        staging_model = model_meta

            all_versions.sort(key=lambda x: int(x.version), reverse=True)

            logger.info(
                f"Current models → Production: v{production_model.version if production_model else None}, "
                f"Total versions: {len(all_versions)}"
            )
            
            return ModelListResponse(
                production=production_model,
                staging=staging_model,
                all_versions=all_versions
            )
        
        except Exception as e:
            logger.error(f"Failed to get current models: {e}", exc_info=True)
            raise

    def get_model_details(self, model_name: str) -> Optional[ModelMetadata]:
        try:
            versions = self.client.get_latest_versions(model_name, stages=None)
            if versions:
                return self._version_to_metadata(versions[0])
            return None
        except Exception as e:
            logger.error(f"Failed to get model details: {e}", exc_info=True)
            raise

    def list_model_versions(self, model_name: str) -> List[ModelMetadata]:
        try:
            versions = self.client.search_model_versions(f"name='{model_name}'")
            return [self._version_to_metadata(v) for v in versions]
        except Exception as e:
            logger.error(f"Failed to list model versions: {e}", exc_info=True)
            raise

    def deploy_model(self, model_name: str, version: str, target_stage: str) -> bool:
        try:
            if target_stage == "Production":
                # Get current production version before changing
                current_prod_versions = self.client.get_latest_versions(model_name, stages=["Production"])
                
                # Promote new version
                self.client.transition_model_version_stage(
                    model_name, int(version), target_stage
                )
                
                # Clear cache for old production model
                for prod in current_prod_versions:
                    if str(prod.version) != str(version):
                        clear_cache_for_model_version(prod.version)
                        logger.info(f"Cleared feature cache for old production model v{prod.version}")
                
                logger.info(f"Model {model_name} v{version} promoted to {target_stage}")
            else:
                self.client.transition_model_version_stage(
                    model_name, int(version), target_stage
                )
                logger.info(f"Model {model_name} v{version} promoted to {target_stage}")
            
            return True
        except Exception as e:
            logger.error(f"Deployment failed: {e}", exc_info=True)
            raise

    def get_current_model_version(self) -> Dict:
        try:
            versions = self.client.get_latest_versions(self.model_name, stages=["Production"])
            if versions:
                v = versions[0]
                return {
                    "model_name": v.name,
                    "version": str(v.version),
                    "stage": v.current_stage
                }
            return {"model_name": self.model_name, "version": None, "stage": None}
        except Exception as e:
            logger.error(f"Failed to get current model version: {e}")
            raise

    def _version_to_metadata(self, version) -> ModelMetadata:
        try:
            run = self.client.get_run(version.run_id)
            metrics = run.data.metrics or {}
            return ModelMetadata(
                name=version.name,
                version=str(version.version),
                stage=version.current_stage or "None",
                created_date=datetime.fromtimestamp(version.creation_timestamp / 1000),
                last_updated=datetime.fromtimestamp(version.last_updated_timestamp / 1000),
                metrics=metrics
            )
        except Exception:
            return ModelMetadata(
                name=version.name,
                version=str(version.version),
                stage=version.current_stage or "None",
                created_date=datetime.fromtimestamp(version.creation_timestamp / 1000),
                last_updated=datetime.fromtimestamp(version.last_updated_timestamp / 1000),
                metrics={}
            )