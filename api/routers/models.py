"""
Model Management Router
Handles model registry and deployment operations
"""

from fastapi import APIRouter, HTTPException, status
from typing import List

from api.schemas import (
    ModelMetadata,
    ModelListResponse,
    ModelDeployRequest,
    ModelDeployResponse,
)
from api.services.model_service import ModelService
from shared.logging import setup_logging

logger = setup_logging("models_router")

router = APIRouter()

# Initialize service
model_service = ModelService()


@router.get(
    "/current",
    response_model=ModelListResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Current Models",
    description="Get information about current production and staging models",
    responses={
        200: {
            "description": "Current models information",
            "example": {
                "production": {
                    "name": "customer-churn-model",
                    "version": "3",
                    "stage": "Production",
                    "created_date": "2024-01-10T08:00:00Z",
                    "last_updated": "2024-01-15T10:30:00Z",
                    "metrics": {
                        "accuracy": 0.85,
                        "precision": 0.82,
                        "recall": 0.79,
                        "f1_score": 0.80,
                        "auc": 0.88
                    }
                },
                "staging": None,
                "all_versions": []
            }
        },
        503: {"description": "MLflow service unavailable"}
    }
)
async def get_current_models() -> ModelListResponse:
    """
    Get information about currently deployed models.
    
    **Returns:**
    - `production`: Model currently serving predictions (if exists)
    - `staging`: Model in staging phase for testing (if exists)
    - `all_versions`: All available versions with their metadata
    
    **Metrics Included:**
    - `accuracy`: Overall prediction accuracy
    - `precision`: True positive rate among positive predictions
    - `recall`: True positive rate among actual positives
    - `f1_score`: Harmonic mean of precision and recall
    - `auc`: Area under ROC curve
    
    **Use Cases:**
    - Monitor which model is in production
    - Track model version history
    - Compare model performance across versions
    """
    try:
        logger.info("Fetching current models")
        
        models = model_service.get_current_models()
        
        return models
    
    except Exception as e:
        logger.error(f"Failed to get models: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal server error. Please try again later."
        )


@router.get(
    "/{model_name}",
    response_model=ModelMetadata,
    status_code=status.HTTP_200_OK,
    summary="Get Model Details",
    description="Get detailed information about a specific model",
    responses={
        200: {"description": "Model information"},
        404: {"description": "Model not found"},
        503: {"description": "MLflow service unavailable"}
    }
)
async def get_model_details(model_name: str) -> ModelMetadata:
    """
    Get detailed information about a specific model.
    
    **Parameters:**
    - `model_name`: Name of the model in MLflow registry
    
    **Returns Complete Information:**
    - Model version and stage
    - All performance metrics
    - Creation and update timestamps
    - Training run information
    
    **Example:**
    ```bash
    curl "http://localhost:8000/api/models/customer-churn-model"
    ```
    """
    try:
        logger.info(f"Fetching details for model: {model_name}")
        
        model = model_service.get_model_details(model_name)
        
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model not found: {model_name}"
            )
        
        return model
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get model details: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal server error. Please try again later."
        )


@router.get(
    "/{model_name}/versions",
    response_model=List[ModelMetadata],
    status_code=status.HTTP_200_OK,
    summary="List Model Versions",
    description="List all available versions of a model",
    responses={
        200: {
            "description": "List of model versions",
            "example": [
                {
                    "name": "customer-churn-model",
                    "version": "3",
                    "stage": "Production",
                    "created_date": "2024-01-10T08:00:00Z",
                    "last_updated": "2024-01-15T10:30:00Z",
                    "metrics": {"accuracy": 0.85}
                }
            ]
        },
        404: {"description": "Model not found"}
    }
)
async def list_model_versions(model_name: str) -> List[ModelMetadata]:
    """
    List all available versions of a specific model with their metadata.
    
    **Returns Version Information:**
    - Version number
    - Current stage (Staging, Production, Archived)
    - Performance metrics
    - Creation timestamps
    
    **Useful For:**
    - Comparing performance across versions
    - Finding previous versions
    - Reviewing model history
    - Version rollback decisions
    """
    try:
        logger.info(f"Listing versions for model: {model_name}")
        
        versions = model_service.list_model_versions(model_name)
        
        if not versions:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model not found: {model_name}"
            )
        
        return versions
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list model versions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal server error. Please try again later."
        )


@router.post(
    "/deploy",
    response_model=ModelDeployResponse,
    status_code=status.HTTP_200_OK,
    summary="Deploy/Promote Model",
    description="Deploy or promote a model to Staging or Production",
    responses={
        200: {
            "description": "Model deployed successfully",
            "example": {
                "success": True,
                "model_name": "customer-churn-model",
                "version": "4",
                "target_stage": "Production",
                "message": "Model v4 promoted to Production"
            }
        },
        400: {"description": "Invalid deployment request"},
        404: {"description": "Model or version not found"},
        503: {"description": "MLflow service unavailable"}
    }
)
async def deploy_model(request: ModelDeployRequest) -> ModelDeployResponse:
    """
    Deploy or promote a model to a target stage.
    
    **Deployment Stages:**
    - `Staging`: Testing environment for validation
    - `Production`: Live serving environment
    
    **Workflow:**
    1. Train new model → New version created (stage: None)
    2. Promote to Staging → Validate with real data
    3. Promote to Production → Serve to users
    
    **Requirements:**
    - Model must exist in MLflow registry
    - Specified version must exist
    - Target stage must be valid
    
    **Example Usage:**
    ```bash
    # Promote v4 to Production
    curl -X POST "http://localhost:8000/api/models/deploy" \\
      -H "Content-Type: application/json" \\
      -d '{
        "model_name": "customer-churn-model",
        "version": "4",
        "target_stage": "Production"
      }'
    ```
    
    **Important Notes:**
    - Previous Production model will be archived
    - All API predictions will use new model
    - Rollback available through older versions
    """
    try:
        logger.info(
            f"Model deployment requested: {request.model_name} v{request.version} "
            f"→ {request.target_stage}"
        )
        
        # Validate request
        if request.target_stage not in ["Staging", "Production"]:
            raise ValueError("Target stage must be 'Staging' or 'Production'")
        
        # Deploy model
        success = model_service.deploy_model(
            model_name=request.model_name,
            version=request.version,
            target_stage=request.target_stage
        )
        
        if not success:
            raise Exception("Deployment failed")
        
        logger.info(f"Model deployed successfully: {request.model_name} v{request.version}")
        
        return ModelDeployResponse(
            success=True,
            model_name=request.model_name,
            version=request.version,
            target_stage=request.target_stage,
            message=f"Model v{request.version} promoted to {request.target_stage}"
        )
    
    except ValueError as e:
        logger.warning(f"Deployment validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Model deployment failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Internal server error. Please try again later."
        )


@router.get(
    "/health/model-version",
    summary="Current Model Version",
    description="Get the version of the model currently serving predictions",
    responses={
        200: {
            "description": "Current production model version",
            "example": {
                "model_name": "customer-churn-model",
                "version": "3",
                "stage": "Production"
            }
        }
    }
)
async def get_current_model_version():
    """
    Get the version of the model currently serving predictions.
    
    This is useful for:
    - Monitoring which model is active
    - Debugging prediction differences
    - Correlation with deployment logs
    """
    try:
        logger.info("Fetching current model version")
        
        model_info = model_service.get_current_model_version()
        
        return model_info
    
    except Exception as e:
        logger.error(f"Failed to get current model version: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to retrieve current model version"
        )
