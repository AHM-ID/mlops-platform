# api/routers/models.py
"""
Model Management Router - Model Registry and Retraining

Endpoints:
- GET    /models                 - List all model versions
- GET    /models/current         - Get current production model
- POST   /models/retrain         - Trigger model retraining
- GET    /models/retrain/{id}    - Get retraining task status
- POST   /models/deploy          - Deploy/promote a model
- GET    /models/{name}          - Get model details
- GET    /models/{name}/versions - List versions of a model
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List

from api.schemas import (
    ModelMetadata, ModelListResponse,
    ModelDeployRequest, ModelDeployResponse,
    TriggerRetrainResponse, RetrainTaskStatus
)
from api.services.model_service import ModelService
from shared.logging import setup_logging
from api.auth import require_read, require_admin, require_retrain
from worker.celery_app import app as celery_app, retrain

logger = setup_logging("models_router")
router = APIRouter(tags=["Model Management"])

model_service = ModelService()


@router.get(
    "/",
    response_model=ModelListResponse,
    summary="List Models",
)
async def list_models(role: str = Depends(require_read)) -> ModelListResponse:
    """List all model versions."""
    try:
        return model_service.get_current_models()
    except Exception as e:
        logger.error(f"Failed to get models: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MLflow service unavailable"
        )


@router.get(
    "/current",
    summary="Get Current Model Version",
)
async def get_current_model_version(role: str = Depends(require_read)):
    """Get current production model version."""
    try:
        return model_service.get_current_model_version()
    except Exception as e:
        logger.error(f"Failed to get current model version: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to retrieve current model version"
        )


@router.post(
    "/retrain",
    response_model=TriggerRetrainResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Retraining",
)
async def trigger_retrain(role: str = Depends(require_retrain)) -> TriggerRetrainResponse:
    """Trigger model retraining."""
    try:
        task = retrain.delay()
        logger.info(f"Retraining task submitted: {task.id}")
        return TriggerRetrainResponse(
            status="submitted",
            task_id=task.id,
            message="Retraining task has been submitted"
        )
    except Exception as e:
        logger.error(f"Failed to submit retraining task: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to submit retraining task"
        )


@router.get(
    "/retrain/{task_id}/status",
    response_model=RetrainTaskStatus,
    summary="Get Retraining Status",
)
async def get_retrain_status(
    task_id: str,
    role: str = Depends(require_read)
) -> RetrainTaskStatus:
    """Get retraining task status."""
    try:
        task = celery_app.AsyncResult(task_id)
        
        if task.state == "PENDING":
            return RetrainTaskStatus(
                task_id=task_id,
                status="pending",
                ready=False,
                result=None,
                error=None
            )
        elif task.state == "PROGRESS":
            return RetrainTaskStatus(
                task_id=task_id,
                status="processing",
                ready=False,
                result=task.info,
                error=None
            )
        elif task.state == "SUCCESS":
            return RetrainTaskStatus(
                task_id=task_id,
                status="success",
                ready=True,
                result=task.result,
                error=None
            )
        elif task.state == "FAILURE":
            return RetrainTaskStatus(
                task_id=task_id,
                status="failed",
                ready=True,
                result=None,
                error=str(task.info)
            )
        else:
            return RetrainTaskStatus(
                task_id=task_id,
                status=task.state,
                ready=task.ready(),
                result=None,
                error=None
            )
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get task status"
        )


@router.post(
    "/deploy",
    response_model=ModelDeployResponse,
    summary="Deploy Model",
)
async def deploy_model(
    request: ModelDeployRequest,
    role: str = Depends(require_admin)
) -> ModelDeployResponse:
    """Deploy a model to staging or production."""
    try:
        if request.target_stage not in ["Staging", "Production"]:
            raise ValueError("Target stage must be 'Staging' or 'Production'")
        
        success = model_service.deploy_model(
            model_name=request.model_name,
            version=request.version,
            target_stage=request.target_stage
        )
        
        if not success:
            raise Exception("Deployment failed")
        
        logger.info(f"Model deployed: {request.model_name} v{request.version} to {request.target_stage}")
        
        return ModelDeployResponse(
            success=True,
            model_name=request.model_name,
            version=request.version,
            target_stage=request.target_stage,
            message=f"Model v{request.version} promoted to {request.target_stage}"
        )
    
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Model deployment failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Deployment failed"
        )


@router.get(
    "/{model_name}",
    response_model=ModelMetadata,
    summary="Get Model Details",
)
async def get_model_details(
    model_name: str,
    role: str = Depends(require_read)
) -> ModelMetadata:
    """Get model details."""
    try:
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
        logger.error(f"Failed to get model details: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MLflow service unavailable"
        )


@router.get(
    "/{model_name}/versions",
    response_model=List[ModelMetadata],
    summary="List Model Versions",
)
async def list_model_versions(
    model_name: str,
    role: str = Depends(require_read)
) -> List[ModelMetadata]:
    """List model versions."""
    try:
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
        logger.error(f"Failed to list model versions: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MLflow service unavailable"
        )