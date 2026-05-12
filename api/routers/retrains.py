"""
Retrain Router
Handles asynchronous model retraining requests
"""

from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from datetime import datetime
import uuid

from worker.celery_app import retrain
from shared.logging import setup_logging
from shared.config import REDIS_URL
import redis

logger = setup_logging("retrain_router")

router = APIRouter()

@router.post(
    "/retrain",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger Model Retraining",
    description="Submit an asynchronous request to retrain the model",
    responses={
        202: {
            "description": "Retraining task submitted",
            "example": {
                "task_id": "abc-123-def",
                "status": "submitted",
                "message": "Retraining task has been submitted"
            }
        },
        503: {"description": "Service unavailable"}
    }
)
async def trigger_retrain():
    try:
        task = retrain.delay()
        logger.info(f"Retraining task submitted: {task.id}")
        
        return {
            "task_id": task.id,
            "status": "submitted",
            "message": "Retraining task has been submitted. Check logs for progress."
        }
    except Exception as e:
        logger.error(f"Failed to submit retraining task: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to submit retraining task: {str(e)}"
        )

@router.get(
    "/retrain/{task_id}/status",
    status_code=status.HTTP_200_OK,
    summary="Get Retraining Status",
    description="Get the status of a retraining task",
    responses={
        200: {
            "description": "Task status",
            "example": {
                "task_id": "abc-123-def",
                "status": "SUCCESS",
                "ready": True,
                "result": {"status": "success"}
            }
        },
        404: {"description": "Task not found"}
    }
)
async def get_retrain_status(task_id: str):
    try:
        from worker.celery_app import app
        task = app.AsyncResult(task_id)
        
        if task.state == "PENDING":
            return {
                "task_id": task_id,
                "status": "pending",
                "ready": False,
                "result": None
            }
        elif task.state == "PROGRESS":
            return {
                "task_id": task_id,
                "status": "processing",
                "ready": False,
                "result": task.info
            }
        elif task.state == "SUCCESS":
            return {
                "task_id": task_id,
                "status": "success",
                "ready": True,
                "result": task.result
            }
        elif task.state == "FAILURE":
            return {
                "task_id": task_id,
                "status": "failed",
                "ready": True,
                "error": str(task.info)
            }
        else:
            return {
                "task_id": task_id,
                "status": task.state,
                "ready": task.ready(),
                "result": None
            }
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )