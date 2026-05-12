"""
Predictions Router
Handles real-time and async batch prediction requests
"""

from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from typing import List, Optional
from datetime import datetime
import uuid
from api.schemas import PredictionRequest

from api.schemas import (
    PredictionRequest,
    PredictionResponse,
    BatchPredictionRequest,
    BatchPredictionResponse,
)
from api.services.prediction_service import PredictionService
from api.services.batch_service import BatchService
from shared.logging import setup_logging

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
    description="Get real-time churn prediction for a single customer",
    responses={
        200: {
            "description": "Successful prediction",
            "example": {
                "customer_id": "CUST001",
                "prediction": 1,
                "probability": 0.75,
                "confidence": 75.0,
                "model_version": "1"
            }
        },
        400: {"description": "Invalid input data"},
        503: {"description": "ML service unavailable"}
    }
)
async def predict_single(request: PredictionRequest) -> PredictionResponse:
    """
    Get a real-time prediction for a single customer record.
    
    **Input Parameters:**
    - `customer_id`: Unique customer identifier (optional)
    - `tenure`: Duration of customer relationship in months
    - `monthly_charges`: Monthly service charges
    - `total_charges`: Total charges accumulated
    - `contract_type`: Current contract type
    - `internet_service`: Type of internet service
    - `payment_method`: Payment method used
    
    **Response:**
    - `prediction`: 0 (no churn) or 1 (likely to churn)
    - `probability`: Confidence probability (0.0 to 1.0)
    - `confidence`: Percentage confidence (0 to 100)
    - `model_version`: Version of model used
    
    **Example Usage:**
    ```bash
    curl -X POST "http://localhost:8000/api/predictions/single" \\
      -H "Content-Type: application/json" \\
      -d '{
        "customer_id": "CUST001",
        "tenure": 24,
        "monthly_charges": 75.5,
        "total_charges": 1814.0,
        "contract_type": "Two year",
        "internet_service": "Fiber optic",
        "payment_method": "Electronic check"
      }'
    ```
    """
    try:
        logger.info(f"Single prediction request for customer: {request.customer_id}")
        
        # Get prediction from service
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
    description="Submit a batch of records for asynchronous prediction",
    responses={
        202: {
            "description": "Batch prediction job submitted",
            "example": {
                "batch_id": "batch_20240115_abc123",
                "status": "submitted",
                "total_records": 1000,
                "celery_task_id": "1f3d2e4a-5c6b-7d8e-9f0a-1b2c3d4e5f6a",
                "created_at": "2024-01-15T10:30:00Z"
            }
        },
        400: {"description": "Invalid batch data"},
        503: {"description": "Batch service unavailable"}
    }
)
async def predict_batch(request: BatchPredictionRequest) -> BatchPredictionResponse:
    """
    Submit a batch of customer records for asynchronous prediction.
    
    This endpoint accepts large batches and processes them asynchronously
    using Celery. Use the returned `batch_id` to check job status and retrieve results.
    
    **Input Parameters:**
    - `batch_name`: Optional human-readable name for the batch
    - `data`: List of customer records (up to 10,000 records per batch)
    
    **Workflow:**
    1. Submit batch → Returns `batch_id` (HTTP 202)
    2. Poll `/batch/{batch_id}/status` for progress
    3. Retrieve results with `/batch/{batch_id}/results` when complete
    
    **Example Usage:**
    ```bash
    # Submit batch
    curl -X POST "http://localhost:8000/api/batch" \\
      -H "Content-Type: application/json" \\
      -d '{
        "batch_name": "Monthly_Predictions_Jan2024",
        "data": [
          {"customer_id": "CUST001", "tenure": 24, ...},
          {"customer_id": "CUST002", "tenure": 12, ...}
        ]
      }'
    
    # Check status
    curl "http://localhost:8000/api/batch/batch_20240115_abc123/status"
    
    # Get results
    curl "http://localhost:8000/api/batch/batch_20240115_abc123/results"
    ```
    """
    try:
        logger.info(
            f"Batch prediction request: name={request.batch_name}, "
            f"records={len(request.data)}"
        )
        
        # Validate batch size
        if len(request.data) > 10000:
            raise ValueError("Batch size cannot exceed 10,000 records")
        
        if len(request.data) == 0:
            raise ValueError("Batch must contain at least 1 record")
        
        # Create batch job
        batch_id = batch_service.create_batch(
            request.data,
            batch_name=request.batch_name
        )
        
        logger.info(f"Batch job created: {batch_id}")
        
        return BatchPredictionResponse(
            batch_id=batch_id,
            status="submitted",
            total_records=len(request.data),
            celery_task_id=batch_service.get_celery_task_id(batch_id),
            created_at=datetime.now()
        )
    
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
    summary="Batch Job Status",
    description="Get the status and progress of a batch prediction job",
    responses={
        200: {
            "description": "Batch job status",
            "example": {
                "batch_id": "batch_20240115_abc123",
                "status": "processing",
                "progress": 45,
                "total_records": 1000,
                "processed_records": 450
            }
        },
        404: {"description": "Batch job not found"}
    }
)
async def get_batch_status(batch_id: str):
    """
    Get the current status and progress of a batch prediction job.
    
    **Response Status Values:**
    - `submitted`: Job accepted, waiting to process
    - `processing`: Job currently running
    - `completed`: Job finished successfully
    - `failed`: Job failed with error
    
    **Progress Tracking:**
    - `progress`: Percentage complete (0-100)
    - `processed_records`: Number of records processed
    - `total_records`: Total records in batch
    """
    try:
        logger.info(f"Status check for batch: {batch_id}")
        
        status_info = batch_service.get_batch_status(batch_id)
        
        if not status_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch job not found: {batch_id}"
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
    summary="Batch Results",
    description="Retrieve the results of a completed batch prediction job",
    responses={
        200: {
            "description": "Batch results",
            "example": {
                "batch_id": "batch_20240115_abc123",
                "summary": {
                    "total_records": 1000,
                    "churn_predictions": 250,
                    "churn_rate": 0.25
                },
                "results": [
                    {
                        "index": 0,
                        "customer_id": "CUST001",
                        "prediction": 1,
                        "probability": 0.75
                    }
                ]
            }
        },
        404: {"description": "Batch not found or results expired"},
        202: {"description": "Batch still processing"}
    }
)
async def get_batch_results(batch_id: str):
    """
    Retrieve prediction results for a completed batch job.
    
    **Notes:**
    - Results are cached for 24 hours
    - If batch still processing, returns HTTP 202
    - Results limited to first 100 records (summary shows all)
    - Use `batch_id` to correlate with original submission
    
    **Response Includes:**
    - `summary`: Aggregated statistics (total records, churn rate, etc.)
    - `results`: Detailed predictions for each customer
    """
    try:
        logger.info(f"Results request for batch: {batch_id}")
        
        results = batch_service.get_batch_results(batch_id)
        
        if results is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch results not found or expired: {batch_id}"
            )
        
        if results.get("status") == "processing":
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="Batch still processing, check status endpoint"
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
    summary="Collect training data for retraining",
    description="Submit prediction data with actual outcome for future retraining"
)
async def collect_training_data(
    request: PredictionRequest,
    actual_churn: int
):
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
            logger.info(f"Training data collected for customer: {request.customer_id}")
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
