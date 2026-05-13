from typing import List, Dict, Optional
import uuid
import json
import redis
from datetime import datetime

from api.schemas import PredictionRequest
from shared.config import REDIS_URL, BATCH_EXPIRY_SECONDS
from shared.logging import setup_logging
from worker.celery_app import app as celery_app

logger = setup_logging("batch_service")


class BatchService:
    """Service for managing batch prediction jobs"""
    
    def __init__(self):
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)

    def create_batch(self, data: List[PredictionRequest], batch_name: Optional[str] = None) -> str:
        try:
            batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            
            batch_data = [
                {
                    "customer_id": req.customer_id,
                    "tenure": req.tenure,
                    "MonthlyCharges": req.MonthlyCharges,
                    "TotalCharges": req.TotalCharges,
                    "Contract": req.Contract,
                    "InternetService": req.InternetService,
                    "PaymentMethod": req.PaymentMethod,
                }
                for req in data
            ]
            
            from worker.batch_predictor import batch_predict
            celery_task = batch_predict.delay(batch_data, batch_id=batch_id)
            
            batch_meta = {
                "batch_id": batch_id,
                "batch_name": batch_name or f"Batch {batch_id}",
                "status": "submitted",
                "total_records": len(data),
                "processed_records": 0,
                "created_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None,
                "celery_task_id": str(celery_task.id),
                "error": None
            }
            
            self.redis_client.setex(f"batch_meta:{batch_id}", BATCH_EXPIRY_SECONDS, json.dumps(batch_meta))
            logger.info(f"Batch created: {batch_id} | records: {len(data)}")
            return batch_id
        except Exception as e:
            logger.error(f"Failed to create batch: {e}", exc_info=True)
            raise

    def get_batch_status(self, batch_id: str) -> Optional[Dict]:
        try:
            meta_data = self.redis_client.get(f"batch_meta:{batch_id}")
            if not meta_data:
                return None
            meta = json.loads(meta_data)
            
            task_id = meta.get("celery_task_id")
            if task_id:
                task = celery_app.AsyncResult(task_id)
                if task.state == "SUCCESS":
                    meta["status"] = "completed"
                    meta["progress"] = 100
                    meta["completed_at"] = datetime.now().isoformat()
                elif task.state == "FAILURE":
                    meta["status"] = "failed"
                    meta["error"] = str(task.info)
                elif task.state in ["STARTED", "PROGRESS"]:
                    meta["status"] = "processing"
                    meta["progress"] = 50 if "progress" not in meta else meta.get("progress")
            
            return meta
        except Exception as e:
            logger.error(f"Failed to get batch status: {e}", exc_info=True)
            return None

    def get_batch_results(self, batch_id: str) -> Optional[Dict]:
        try:
            results_data = self.redis_client.get(f"batch_results:{batch_id}")
            if results_data:
                return json.loads(results_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get batch results: {e}", exc_info=True)
            return None

    def list_recent_jobs(self, limit: int = 10, status_filter: Optional[str] = None) -> List[Dict]:
        try:
            keys = self.redis_client.keys("batch_meta:*")
            jobs = []
            for key in keys:
                data = self.redis_client.get(key)
                if data:
                    job = json.loads(data)
                    if status_filter and job.get("status") != status_filter:
                        continue
                    jobs.append(job)
            jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return jobs[:limit]
        except Exception as e:
            logger.error(f"Failed to list batch jobs: {e}", exc_info=True)
            return []

    def get_batch_job_status(self, batch_id: str) -> Optional[Dict]:
        meta = self.get_batch_status(batch_id)
        if not meta:
            return None
        return {
            "batch_id": meta.get("batch_id"),
            "status": meta.get("status"),
            "progress": meta.get("progress", 0),
            "total_records": meta.get("total_records", 0),
            "processed_records": meta.get("processed_records", 0),
            "created_at": meta.get("created_at"),
            "started_at": meta.get("started_at"),
            "completed_at": meta.get("completed_at"),
            "celery_task_id": meta.get("celery_task_id"),
        }

    def get_batch_summary(self, batch_id: str) -> Optional[Dict]:
        try:
            results = self.get_batch_results(batch_id)
            if not results or "summary" not in results:
                return None
            summary = results["summary"]
            return {
                "batch_id": batch_id,
                "total_records": summary.get("total_records", 0),
                "churn_predictions": summary.get("churn_predictions", 0),
                "no_churn_predictions": summary.get("no_churn_predictions", 0),
                "churn_rate": summary.get("churn_rate", 0.0),
                "average_churn_probability": summary.get("average_churn_probability", 0.0),
            }
        except Exception as e:
            logger.error(f"Failed to get batch summary: {e}", exc_info=True)
            return None

    def delete_batch(self, batch_id: str) -> bool:
        try:
            self.redis_client.delete(f"batch_meta:{batch_id}")
            self.redis_client.delete(f"batch_results:{batch_id}")
            logger.info(f"Batch {batch_id} deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete batch: {e}")
            return False

    def get_celery_task_id(self, batch_id: str) -> str:
        try:
            meta_data = self.redis_client.get(f"batch_meta:{batch_id}")
            if meta_data:
                meta = json.loads(meta_data)
                return meta.get("celery_task_id", "")
            return ""
        except Exception as e:
            logger.error(f"Failed to get celery task ID: {e}")
            return ""