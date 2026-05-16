"""
Predictions Router
Handles real-time and async batch prediction requests with authentication
"""

from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Depends
from typing import List, Optional
from datetime import datetime
import uuid

from api.schemas import (
    PredictionRequest,
    PredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
)
from api.services.prediction_service import PredictionService
from api.services.batch_service import BatchService
from shared.logging import setup_logging
from shared.config import MAX_BATCH_RECORDS
from api.auth import require_read, require_write

logger = setup_logging("predictions_router")

router = APIRouter()

# Initialize services
prediction_service = PredictionService()
batch_service = BatchService()


@router.post(
    "/single",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Single Prediction",
    description="Get real-time churn prediction for a single customer (requires read permission)",
)
async def predict_single(
    request: PredictionRequest, 
    role: str = Depends(require_read)
) -> PredictionResponse:
    """Get a real-time prediction for a single customer record."""
    try:
        logger.info(f"Single prediction request for customer: {request.customer_id} by role: {role}")
        
        pred, prob, model_version = prediction_service.predict(request)
        
        logger.info(
            f"Prediction completed - customer: {request.customer_id}, "
            f"prediction: {pred}, probability: {prob:.3f}"
        )
        
        return PredictionResponse(
            customer_id=request.customer_id,
            prediction=pred,
            probability=prob,
            confidence=prob * 100,
            model_version=model_version
        )
    
    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Prediction service unavailable: {str(e)}"
        )


@router.post(
    "/batch",
    response_model=BatchPredictionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Batch Prediction",
    description="Submit a batch of records for asynchronous prediction (requires write permission)",
)
async def predict_batch(
    request: BatchPredictionRequest,
    role: str = Depends(require_write)
) -> BatchPredictionResponse:
    """Submit a batch of customer records for asynchronous prediction."""
    try:
        logger.info(
            f"Batch prediction request by role {role}: name={request.batch_name}, "
            f"records={len(request.data)}"
        )
        
        if len(request.data) > MAX_BATCH_RECORDS:
            raise ValueError(f"Batch size exceeds maximum of {MAX_BATCH_RECORDS} records")
        
        response = batch_service.submit_batch(request)
        
        logger.info(f"Batch submitted successfully: {response.batch_id}")
        return response
    
    except ValueError as e:
        logger.warning(f"Batch validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Batch submission failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Batch service unavailable: {str(e)}"
        )


@router.get(
    "/batch/{batch_id}/status",
    summary="Get Batch Job Status",
    description="Check the status of a batch prediction job (requires read permission)"
)
async def get_batch_status(
    batch_id: str,
    role: str = Depends(require_read)
):
    """Get the current status of a batch prediction job."""
    try:
        logger.info(f"Status check for batch: {batch_id} by role: {role}")
        status_info = batch_service.get_batch_status(batch_id)
        
        if "error" in status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=status_info["error"]
            )
        
        return status_info
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get batch status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve batch status"
        )


@router.get(
    "/batch/{batch_id}/results",
    summary="Get Batch Job Results",
    description="Retrieve results from a completed batch prediction job (requires read permission)"
)
async def get_batch_results(
    batch_id: str,
    role: str = Depends(require_read)
):
    """Retrieve the results of a completed batch prediction job."""
    try:
        logger.info(f"Results request for batch: {batch_id} by role: {role}")
        results = batch_service.get_batch_results(batch_id)
        
        if "error" in results:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=results["error"]
            )
        
        return results
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get batch results: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve batch results"
        )


@router.post(
    "/collect-training-data",
    status_code=status.HTTP_200_OK,
    summary="Collect Training Data",
    description="Submit prediction data with actual outcome for future retraining (requires write permission)"
)
async def collect_training_data(
    request: PredictionRequest,
    actual_churn: int,
    role: str = Depends(require_write)
):
    """Collect training data for model retraining."""
    try:
        from shared.retrain_queue import RetrainQueueManager
        
        queue_manager = RetrainQueueManager()
        
        features = {
            "tenure": request.tenure,
            "MonthlyCharges": request.MonthlyCharges,
            "TotalCharges": request.TotalCharges,
            "Contract": request.Contract,
            "InternetService": request.InternetService,
            "PaymentMethod": request.PaymentMethod,
        }
        
        success = queue_manager.add_training_record(features, actual_churn)
        
        if success:
            logger.info(f"Training data collected for customer: {request.customer_id} by role: {role}")
            return {"status": "success", "message": "Training data collected"}
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Failed to collect training data"
            )
    except Exception as e:
        logger.error(f"Failed to collect training data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
