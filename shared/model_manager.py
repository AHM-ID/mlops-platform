import mlflow
import mlflow.pyfunc
import pandas as pd
from typing import Dict, Any, Optional, Tuple
from shared.config import MODEL_NAME, MLFLOW_TRACKING_URI
from shared.logging import setup_logging

logger = setup_logging("model_manager")

class ModelManager:
    """Manage multiple model versions with automatic best model selection"""
    
    def __init__(self):
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        self.client = mlflow.tracking.MlflowClient()
        self.models_cache = {}
        
    def get_model_versions(self, stage: Optional[str] = None) -> list:
        """Get all model versions, optionally filtered by stage"""
        try:
            versions = self.client.get_latest_versions(MODEL_NAME, stages=[stage] if stage else None)
            return versions
        except Exception as e:
            logger.error(f"Failed to get model versions: {e}")
            return []
    
    def get_best_model_by_metric(self, metric: str = "auc") -> Tuple[Any, Dict]:
        """Automatically find and load the best model based on metric"""
        try:
            versions = self.client.search_model_versions(f"name='{MODEL_NAME}'")
            
            best_score = -1
            best_version = None
            best_metrics = {}
            
            for version in versions:
                run = self.client.get_run(version.run_id)
                score = run.data.metrics.get(metric, 0)
                
                if score > best_score:
                    best_score = score
                    best_version = version
                    best_metrics = run.data.metrics
            
            if best_version:
                logger.info(f"Best model found: version {best_version.version} with {metric}={best_score:.4f}")
                model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}/{best_version.version}")
                return model, best_metrics
            else:
                logger.warning("No models found, loading production model")
                return self.load_production_model()
                
        except Exception as e:
            logger.error(f"Failed to get best model: {e}")
            return self.load_production_model()
    
    def load_production_model(self) -> Tuple[Any, Dict]:
        """Load the production model"""
        try:
            model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}/Production")
            logger.info("Production model loaded")
            return model, {}
        except Exception as e:
            logger.error(f"Failed to load production model: {e}")
            return None, {}
    
    def compare_performance(self) -> Dict:
        """Compare performance metrics across all model versions"""
        try:
            versions = self.get_model_versions()
            comparison = {}
            
            for version in versions:
                run = self.client.get_run(version.run_id)
                comparison[f"version_{version.version}"] = {
                    "stage": version.stage,
                    "metrics": run.data.metrics,
                    "run_id": version.run_id,
                    "created_at": version.creation_timestamp,
                    "version": version.version
                }
            
            return comparison
            
        except Exception as e:
            logger.error(f"Failed to compare models: {e}")
            return {}