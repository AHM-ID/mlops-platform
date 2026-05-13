from fastapi import APIRouter, HTTPException, status
from shared.retrain_queue import RetrainQueueManager
from shared.logging import setup_logging
from shared.metrics import RETRAIN_QUEUE_LENGTH

logger = setup_logging("retrain_queue_router")

router = APIRouter()

@router.get(
    "/retrain-queue/status",
    status_code=status.HTTP_200_OK,
    summary="Get Retrain Queue Status",
    description="Get the number of pending training records in Redis queue"
)
async def get_retrain_queue_status():
    try:
        queue_manager = RetrainQueueManager()
        queue_length = queue_manager.get_queue_length()

        # Update Prometheus gauge
        RETRAIN_QUEUE_LENGTH.set(queue_length)
        
        return {
            "queue_length": queue_length,
            "max_batch_size": 1000,
            "status": "active" if queue_length > 0 else "empty"
        }
    except Exception as e:
        logger.error(f"Failed to get queue status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete(
    "/retrain-queue/clear",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear Retrain Queue",
    description="Clear all pending training records from Redis queue"
)
async def clear_retrain_queue():
    try:
        queue_manager = RetrainQueueManager()
        queue_manager.clear_queue()
        logger.info("Retrain queue cleared")
        return None
    except Exception as e:
        logger.error(f"Failed to clear queue: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )