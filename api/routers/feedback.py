"""
Feedback Router - Collect labels and training data

Endpoints:
- POST   /feedback/{prediction_id}  - Submit label for a prediction
- POST   /feedback/batch            - Submit multiple labels
- POST   /feedback/train-data       - Manually add training data
"""

from fastapi import APIRouter, HTTPException, status, Depends, Body
from typing import List, Dict, Any
from shared.retrain_queue import RetrainQueueManager
from shared.logging import setup_logging
from api.auth import require_write
from api.schemas import (
    FeedbackRequest, FeedbackResponse,
    BatchFeedbackRequest, BatchFeedbackResponse,
    CollectTrainingDataResponse
)

logger = setup_logging("feedback_router")
router = APIRouter(tags=["Feedback"])


@router.post(
    "/batch",
    response_model=BatchFeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit Batch Feedback",
    description="Submit actual labels for multiple predictions at once."
)
async def submit_batch_feedback(
    request: BatchFeedbackRequest,
    role: str = Depends(require_write)
) -> BatchFeedbackResponse:
    """
    Submit feedback for multiple predictions.
    
    Example curl:
    ```bash
    curl -X POST "http://localhost:8080/api/feedback/batch" \\
         -H "X-API-Key: user-secret-key-change-in-production" \\
         -H "Content-Type: application/json" \\
         -d '{
             "feedbacks": [
                 {"prediction_id": "id1", "actual_label": 0},
                 {"prediction_id": "id2", "actual_label": 1}
             ]
         }'
    ```
    """
    logger.info(f"Batch feedback received: {len(request.feedbacks)} items")
    
    queue_manager = RetrainQueueManager()
    results = []
    succeeded = 0
    failed = 0
    
    for fb in request.feedbacks:
        prediction_id = fb.get("prediction_id")
        actual_label = fb.get("actual_label")
        
        if prediction_id is None or actual_label is None:
            results.append({
                "prediction_id": prediction_id,
                "status": "failed",
                "error": "Missing prediction_id or actual_label"
            })
            failed += 1
            continue
        
        try:
            success = queue_manager.update_label(prediction_id, actual_label)
            if success:
                results.append({
                    "prediction_id": prediction_id,
                    "status": "success",
                    "actual_label": actual_label
                })
                succeeded += 1
            else:
                results.append({
                    "prediction_id": prediction_id,
                    "status": "failed",
                    "error": "Prediction not found or already labeled"
                })
                failed += 1
        except Exception as e:
            results.append({
                "prediction_id": prediction_id,
                "status": "failed",
                "error": str(e)
            })
            failed += 1
    
    return BatchFeedbackResponse(
        status="completed",
        total=len(request.feedbacks),
        succeeded=succeeded,
        failed=failed,
        results=results
    )


@router.post(
    "/train-data",
    response_model=CollectTrainingDataResponse,
    status_code=status.HTTP_200_OK,
    summary="Collect Training Data",
    description="Manually add labeled training data to the retrain queue."
)
async def collect_training_data(
    features: Dict[str, Any] = Body(..., description="Feature dictionary"),
    actual_label: int = Body(..., description="Actual label (0 or 1)"),
    customer_id: str = Body(None, description="Optional customer identifier"),
    role: str = Depends(require_write)
) -> CollectTrainingDataResponse:
    """
    Manually add training data.
    
    Example curl:
    ```bash
    curl -X POST "http://localhost:8080/api/feedback/train-data" \\
         -H "X-API-Key: user-secret-key-change-in-production" \\
         -H "Content-Type: application/json" \\
         -d '{
             "features": {"tenure": 12, "MonthlyCharges": 50.0, ...},
             "actual_label": 1,
             "customer_id": "CUST-2001"
         }'
    ```
    """
    logger.info(f"Training data collected for customer: {customer_id}, label={actual_label}")
    
    queue_manager = RetrainQueueManager()
    success = queue_manager.add_training_record(features, actual_label)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to collect training data"
        )
    
    return CollectTrainingDataResponse(
        status="success",
        message="Training data collected"
    )


@router.post(
    "/{prediction_id}",
    response_model=FeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit Feedback",
    description="""
    Submit actual label (ground truth) for a previous prediction.
    
    Requires 'write' permission.
    The labeled data will be used for model retraining.
    """
)
async def submit_feedback(
    prediction_id: str,
    request: FeedbackRequest,
    role: str = Depends(require_write)
) -> FeedbackResponse:
    """
    Submit feedback for a single prediction.
    
    Example curl:
    ```bash
    curl -X POST "http://localhost:8080/api/feedback/abc123-def456-ghi789" \\
         -H "X-API-Key: user-secret-key-change-in-production" \\
         -H "Content-Type: application/json" \\
         -d '{"actual_label": 0}'
    ```
    """
    logger.info(f"Feedback received for {prediction_id}: label={request.actual_label}")
    
    queue_manager = RetrainQueueManager()
    success = queue_manager.update_label(prediction_id, request.actual_label)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Prediction not found or already labeled: {prediction_id}"
        )
    
    return FeedbackResponse(
        status="success",
        prediction_id=prediction_id,
        actual_label=request.actual_label,
        message="Label recorded successfully"
    )