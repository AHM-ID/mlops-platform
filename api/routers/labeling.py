from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, Field
from shared.retrain_queue import RetrainQueueManager
from shared.logging import setup_logging
from api.auth import require_write

logger = setup_logging("labeling_router")
router = APIRouter()

class FeedbackRequest(BaseModel):
    actual_label: int = Field(..., ge=0, le=1, description="Actual churn: 0=no, 1=yes")

class FeedbackResponse(BaseModel):
    status: str = Field(..., example="success")
    prediction_id: str
    actual_label: int
    message: str

@router.post(
    "/feedback/{prediction_id}",
    response_model=FeedbackResponse,
    status_code=status.HTTP_200_OK,
    summary="Submit label for a prediction"
)
async def submit_feedback(
    prediction_id: str,
    request: FeedbackRequest,
    role: str = Depends(require_write)
) -> FeedbackResponse:
    try:
        logger.info(f"Feedback received for {prediction_id} from role {role}: label={request.actual_label}")
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
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit feedback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error. Please try again later."
        )