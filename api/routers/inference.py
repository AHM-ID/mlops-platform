"""
Inference Router - Single and Batch Predictions

Endpoints:
- POST   /inference/single           - Make a single prediction
- POST   /inference/batch            - Submit a batch prediction job
- GET    /inference/batch/{batch_id} - Get batch job status
- GET    /inference/batch/{batch_id}/results - Get batch results
- GET    /inference/batch/{batch_id}/summary - Get batch summary
- DELETE /inference/batch/{batch_id} - Delete a batch job
- GET    /inference/batches          - List recent batch jobs
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List, Optional
import time

from api.schemas import (
    PredictionRequest, PredictionResponse,
    BatchPredictionRequest, BatchPredictionResponse,
    BatchJobStatus, BatchResultsSummary, BatchJobResults
)
from api.services.prediction_service import PredictionService
from api.services.batch_service import BatchService
from shared.logging import setup_logging
from shared.config import MAX_BATCH_RECORDS
from api.auth import require_read, require_write

logger = setup_logging("inference_router")
router = APIRouter(tags=["Inference"])

_prediction_service = None
_batch_service = None


def get_prediction_service():
    global _prediction_service
    if _prediction_service is None:
        _prediction_service = PredictionService()
    return _prediction_service


def get_batch_service():
    global _batch_service
    if _batch_service is None:
        _batch_service = BatchService()
    return _batch_service


@router.post(
    "/single",
    response_model=PredictionResponse,
    status_code=status.HTTP_200_OK,
    summary="Make a Single Prediction",
    description="""
    Make a real-time churn prediction for a single customer.
    
    Requires 'read' permission (API key with user or admin role).
    
    Returns prediction (0=No Churn, 1=Churn), probability, confidence score,
    and a prediction_id for submitting feedback.
    """
)
async def predict_single(
    request: PredictionRequest, 
    role: str = Depends(require_read)
) -> PredictionResponse:
    """
    Single prediction endpoint.
    
    Example curl:
    ```bash
    curl -X POST "http://localhost:8080/api/inference/single" \\
         -H "X-API-Key: user-secret-key-change-in-production" \\
         -H "Content-Type: application/json" \\
         -d '{
             "customer_id": "CUST-1001",
             "gender": "Female",
             "SeniorCitizen": 0,
             "Partner": "Yes",
             "Dependents": "No",
             "tenure": 24,
             "PhoneService": "Yes",
             "MultipleLines": "No",
             "InternetService": "Fiber optic",
             "OnlineSecurity": "No",
             "OnlineBackup": "Yes",
             "DeviceProtection": "No",
             "TechSupport": "No",
             "StreamingTV": "Yes",
             "StreamingMovies": "No",
             "Contract": "Two year",
             "PaperlessBilling": "Yes",
             "PaymentMethod": "Electronic check",
             "MonthlyCharges": 75.5,
             "TotalCharges": 1814.0
         }'
    ```
    """
    prediction_service = get_prediction_service()
    start_time = time.time()
    
    pred, prob, version, pred_id = prediction_service.predict(request)
    
    latency_ms = (time.time() - start_time) * 1000
    logger.info(
        f"Prediction completed for {request.customer_id}: {pred} (prob={prob:.3f})",
        extra={"prediction_id": pred_id, "latency_ms": latency_ms, "model_version": version}
    )
    
    return PredictionResponse(
        customer_id=request.customer_id,
        prediction=int(pred),
        probability=float(prob),
        confidence=float(prob) * 100,
        model_version=version,
        prediction_id=pred_id
    )


@router.post(
    "/batch",
    response_model=BatchPredictionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit Batch Prediction Job",
    description="""
    Submit multiple customer records for asynchronous batch processing.
    
    Requires 'write' permission (API key with user or admin role).
    Maximum 10,000 records per batch.
    
    Returns a batch_id for tracking the job status.
    """
)
async def predict_batch(
    request: BatchPredictionRequest,
    role: str = Depends(require_write)
) -> BatchPredictionResponse:
    """
    Submit a batch prediction job.
    
    Example curl:
    ```bash
    curl -X POST "http://localhost:8080/api/inference/batch" \\
         -H "X-API-Key: user-secret-key-change-in-production" \\
         -H "Content-Type: application/json" \\
         -d '{
             "batch_name": "January_2024_Batch",
             "data": [<PredictionRequest objects>]
         }'
    ```
    """
    batch_service = get_batch_service()
    
    if len(request.data) > MAX_BATCH_RECORDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch size exceeds maximum of {MAX_BATCH_RECORDS} records"
        )
    
    logger.info(f"Batch submitted: {request.batch_name}, records={len(request.data)}")
    return batch_service.submit_batch(request)


@router.get(
    "/batch/{batch_id}",
    response_model=BatchJobStatus,
    summary="Get Batch Job Status",
    description="Get detailed status and progress of a batch job."
)
async def get_batch_status(batch_id: str) -> BatchJobStatus:
    """
    Get batch job status.
    
    Example curl:
    ```bash
    curl -X GET "http://localhost:8080/api/inference/batch/batch_20240115_abc123" \\
         -H "X-API-Key: user-secret-key-change-in-production"
    ```
    """
    batch_service = get_batch_service()
    job = batch_service.get_batch_job_status(batch_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch job not found: {batch_id}"
        )
    
    return BatchJobStatus(**job)


@router.get(
    "/batch/{batch_id}/results",
    response_model=BatchJobResults,
    summary="Get Batch Results",
    description="Get detailed prediction results for a completed batch job."
)
async def get_batch_results(batch_id: str) -> BatchJobResults:
    """
    Get batch results.
    
    Example curl:
    ```bash
    curl -X GET "http://localhost:8080/api/inference/batch/batch_20240115_abc123/results" \\
         -H "X-API-Key: user-secret-key-change-in-production"
    ```
    """
    batch_service = get_batch_service()
    results = batch_service.get_batch_results(batch_id)
    
    if not results:
        status_info = batch_service.get_batch_job_status(batch_id)
        if status_info and status_info.get("status") == "processing":
            raise HTTPException(
                status_code=status.HTTP_202_ACCEPTED,
                detail="Batch still processing, use status endpoint"
            )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch results not found: {batch_id}"
        )
    
    return BatchJobResults(**results)


@router.get(
    "/batch/{batch_id}/summary",
    response_model=BatchResultsSummary,
    summary="Get Batch Summary",
    description="Get aggregated summary statistics for a completed batch job."
)
async def get_batch_summary(batch_id: str) -> BatchResultsSummary:
    """
    Get batch summary statistics.
    
    Example curl:
    ```bash
    curl -X GET "http://localhost:8080/api/inference/batch/batch_20240115_abc123/summary" \\
         -H "X-API-Key: user-secret-key-change-in-production"
    ```
    """
    batch_service = get_batch_service()
    summary = batch_service.get_batch_summary(batch_id)
    
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch summary not found: {batch_id}"
        )
    
    return BatchResultsSummary(**summary)


@router.delete(
    "/batch/{batch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Batch Job",
    description="Delete a batch job and its results. Cannot delete processing jobs."
)
async def delete_batch(
    batch_id: str,
    role: str = Depends(require_write)
):
    """
    Delete a batch job.
    
    Example curl:
    ```bash
    curl -X DELETE "http://localhost:8080/api/inference/batch/batch_20240115_abc123" \\
         -H "X-API-Key: admin-secret-key-change-in-production"
    ```
    """
    batch_service = get_batch_service()
    job = batch_service.get_batch_job_status(batch_id)
    
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch job not found: {batch_id}"
        )
    
    if job.get("status") == "processing":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete batch job while processing"
        )
    
    batch_service.delete_batch(batch_id)
    logger.info(f"Batch job deleted: {batch_id}")
    return None


@router.get(
    "/batches",
    response_model=List[BatchJobStatus],
    summary="List Batch Jobs",
    description="Get a list of recent batch jobs with their status."
)
async def list_batches(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of jobs to return"),
    status_filter: Optional[str] = Query(None, description="Filter by status")
) -> List[BatchJobStatus]:
    """
    List recent batch jobs.
    
    Example curl:
    ```bash
    curl -X GET "http://localhost:8080/api/inference/batches?limit=20&status_filter=completed" \\
         -H "X-API-Key: user-secret-key-change-in-production"
    ```
    """
    batch_service = get_batch_service()
    jobs = batch_service.list_recent_jobs(limit=limit, status_filter=status_filter)
    return [BatchJobStatus(**job) for job in jobs]