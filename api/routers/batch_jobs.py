"""
Batch Processing Router
Manages batch job operations and results retrieval
"""

from fastapi import APIRouter, HTTPException, status, Query
from typing import List, Optional

from api.schemas import (
    BatchJobStatus,
    BatchResultsSummary,
)
from api.services.batch_service import BatchService
from shared.logging import setup_logging

logger = setup_logging("batch_router")

router = APIRouter()

# Initialize service
batch_service = BatchService()


@router.get(
    "/jobs",
    response_model=List[BatchJobStatus],
    status_code=status.HTTP_200_OK,
    summary="List Batch Jobs",
    description="Get list of recent batch jobs with their status",
    responses={
        200: {
            "description": "List of batch jobs",
            "example": [
                {
                    "batch_id": "batch_20240115_abc123",
                    "status": "completed",
                    "progress": 100,
                    "total_records": 1000,
                    "processed_records": 1000,
                    "created_at": "2024-01-15T10:30:00Z",
                    "completed_at": "2024-01-15T10:45:00Z",
                    "celery_task_id": "1f3d2e4a-5c6b-7d8e-9f0a-1b2c3d4e5f6a"
                }
            ]
        }
    }
)
async def list_batch_jobs(
    limit: int = Query(10, ge=1, le=100, description="Maximum number of jobs to return"),
    status_filter: Optional[str] = Query(
        None,
        description="Filter by status: submitted, processing, completed, failed"
    )
) -> List[BatchJobStatus]:
    """
    Get a list of recent batch jobs with their current status.
    
    **Query Parameters:**
    - `limit`: Maximum number of jobs to return (1-100, default: 10)
    - `status_filter`: Filter by job status (optional)
    
    **Job Status Values:**
    - `submitted`: Job queued, not yet started
    - `processing`: Job currently running
    - `completed`: Job finished successfully
    - `failed`: Job failed with error
    
    **Returns:**
    List of batch jobs sorted by creation date (newest first)
    
    **Example Usage:**
    ```bash
    # Get last 20 jobs
    curl "http://localhost:8000/api/batch/jobs?limit=20"
    
    # Get only completed jobs
    curl "http://localhost:8000/api/batch/jobs?status_filter=completed"
    ```
    """
    try:
        logger.info(f"Listing batch jobs: limit={limit}, status={status_filter}")
        
        jobs = batch_service.list_recent_jobs(
            limit=limit,
            status_filter=status_filter
        )
        
        return jobs
    
    except Exception as e:
        logger.error(f"Failed to list batch jobs: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve batch jobs"
        )


@router.get(
    "/{batch_id}",
    response_model=BatchJobStatus,
    status_code=status.HTTP_200_OK,
    summary="Get Batch Job Details",
    description="Get detailed status of a specific batch job",
    responses={
        200: {
            "description": "Batch job details",
            "example": {
                "batch_id": "batch_20240115_abc123",
                "status": "completed",
                "progress": 100,
                "total_records": 1000,
                "processed_records": 1000,
                "created_at": "2024-01-15T10:30:00Z",
                "started_at": "2024-01-15T10:31:00Z",
                "completed_at": "2024-01-15T10:45:00Z",
                "celery_task_id": "1f3d2e4a-5c6b-7d8e-9f0a-1b2c3d4e5f6a"
            }
        },
        404: {"description": "Batch job not found"}
    }
)
async def get_batch_job_details(batch_id: str) -> BatchJobStatus:
    """
    Get detailed information about a specific batch job.
    
    **Includes:**
    - Current job status
    - Progress percentage
    - Record counts (total, processed)
    - Timing information (created, started, completed)
    - Celery task ID for troubleshooting
    
    **Progress Tracking:**
    - Use `progress` field to show progress bar
    - Use timestamps to calculate processing time
    - `processed_records / total_records = progress%`
    
    **Example Usage:**
    ```bash
    curl "http://localhost:8000/api/batch/batch_20240115_abc123"
    ```
    """
    try:
        logger.info(f"Getting batch job details: {batch_id}")
        
        job = batch_service.get_batch_job_status(batch_id)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch job not found: {batch_id}"
            )
        
        return job
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get batch job details: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve batch job details"
        )


@router.get(
    "/{batch_id}/summary",
    response_model=BatchResultsSummary,
    status_code=status.HTTP_200_OK,
    summary="Batch Results Summary",
    description="Get aggregated summary statistics of batch results",
    responses={
        200: {
            "description": "Batch results summary",
            "example": {
                "batch_id": "batch_20240115_abc123",
                "total_records": 1000,
                "churn_predictions": 250,
                "no_churn_predictions": 750,
                "churn_rate": 0.25,
                "average_churn_probability": 0.35
            }
        },
        404: {"description": "Batch not found or not completed"},
        202: {"description": "Batch still processing"}
    }
)
async def get_batch_summary(batch_id: str) -> BatchResultsSummary:
    """
    Get aggregated summary statistics of a completed batch job.
    
    **Summary Metrics:**
    - `total_records`: Total customers analyzed
    - `churn_predictions`: Number predicted to churn
    - `no_churn_predictions`: Number predicted to stay
    - `churn_rate`: Percentage likely to churn (0.0-1.0)
    - `average_churn_probability`: Mean probability across batch
    
    **Use Cases:**
    - Quick overview of batch results
    - Risk assessment across customer base
    - Identify high-churn customer segments
    - Business reporting
    
    **Example Usage:**
    ```bash
    curl "http://localhost:8000/api/batch/batch_20240115_abc123/summary"
    ```
    """
    try:
        logger.info(f"Getting batch summary: {batch_id}")
        
        summary = batch_service.get_batch_summary(batch_id)
        
        if not summary:
            # Check if batch still processing
            status_info = batch_service.get_batch_job_status(batch_id)
            if status_info and status_info.status == "processing":
                raise HTTPException(
                    status_code=status.HTTP_202_ACCEPTED,
                    detail="Batch still processing, check status endpoint"
                )
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch results not found: {batch_id}"
            )
        
        return summary
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get batch summary: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve batch summary"
        )


@router.delete(
    "/{batch_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Batch Job",
    description="Delete a batch job and its results",
    responses={
        204: {"description": "Batch job deleted successfully"},
        404: {"description": "Batch job not found"},
        409: {"description": "Cannot delete batch still processing"}
    }
)
async def delete_batch_job(batch_id: str):
    """
    Delete a batch job and its stored results.
    
    **Restrictions:**
    - Cannot delete jobs still processing
    - Completed and failed jobs can be deleted
    - Deletes results from Redis cache
    
    **Use Cases:**
    - Clean up old test batches
    - Remove failed job attempts
    - Data retention compliance
    
    **Example Usage:**
    ```bash
    curl -X DELETE "http://localhost:8000/api/batch/batch_20240115_abc123"
    ```
    """
    try:
        logger.info(f"Deleting batch job: {batch_id}")
        
        # Check if batch exists and get status
        job = batch_service.get_batch_job_status(batch_id)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch job not found: {batch_id}"
            )
        
        # Cannot delete if processing
        if job.status == "processing":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot delete batch job while processing"
            )
        
        # Delete the batch
        batch_service.delete_batch(batch_id)
        
        logger.info(f"Batch job deleted: {batch_id}")
        
        return None
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete batch job: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete batch job"
        )
