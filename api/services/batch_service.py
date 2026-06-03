import os
from typing import List, Dict, Optional, Any
import uuid
import pickle
from datetime import datetime

from api.schemas import PredictionRequest, BatchPredictionResponse
from shared.config import BATCH_EXPIRY_SECONDS, get_redis_client
from shared.logging import setup_logging
from worker.celery_app import app as celery_app

logger = setup_logging("batch_service")

class BatchService:
    def __init__(self):
        self._redis_client = None
        self._init_redis()

    def _init_redis(self):
        try:
            self._redis_client = get_redis_client(decode_responses=False)
            self._redis_client.ping()
        except Exception as e:
            logger.warning(f"Redis connection failed for batch service: {e}")
            self._redis_client = None

    @property
    def redis_client(self):
        if self._redis_client is None:
            self._init_redis()
        return self._redis_client

    def create_batch(self, data: List[PredictionRequest], batch_name: Optional[str] = None) -> str:
        try:
            batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
            batch_data = []
            for req in data:
                record = {
                    "customer_id": req.customer_id,
                    "tenure": req.tenure,
                    "MonthlyCharges": req.MonthlyCharges,
                    "TotalCharges": req.TotalCharges,
                    "Contract": req.Contract,
                    "InternetService": req.InternetService,
                    "PaymentMethod": req.PaymentMethod,
                    "gender": req.gender,
                    "SeniorCitizen": req.SeniorCitizen,
                    "Partner": req.Partner,
                    "Dependents": req.Dependents,
                    "PhoneService": req.PhoneService,
                    "MultipleLines": req.MultipleLines,
                    "OnlineSecurity": req.OnlineSecurity,
                    "OnlineBackup": req.OnlineBackup,
                    "DeviceProtection": req.DeviceProtection,
                    "TechSupport": req.TechSupport,
                    "StreamingTV": req.StreamingTV,
                    "StreamingMovies": req.StreamingMovies,
                    "PaperlessBilling": req.PaperlessBilling,
                }
                batch_data.append(record)
            
            from worker.batch_predictor import batch_predict
            celery_task = batch_predict.delay(batch_data, batch_id=batch_id)
            batch_meta = {
                "batch_id": batch_id,
                "batch_name": batch_name or f"Batch {batch_id}",
                "status": "submitted",
                "total_records": len(data),
                "processed_records": len(data),
                "progress": 0,
                "created_at": datetime.now().isoformat(),
                "started_at": None,
                "completed_at": None,
                "celery_task_id": str(celery_task.id),
                "error": None
            }
            if self.redis_client:
                self.redis_client.setex(f"batch_meta:{batch_id}", BATCH_EXPIRY_SECONDS, pickle.dumps(batch_meta))
            logger.info(f"Batch created: {batch_id} | records: {len(data)}")
            return batch_id
        except Exception as e:
            logger.error(f"Failed to create batch: {e}", exc_info=True)
            raise

    def get_batch_status(self, batch_id: str) -> Optional[Dict]:
        if not self.redis_client:
            return None
        try:
            meta_data = self.redis_client.get(f"batch_meta:{batch_id}")
            if not meta_data:
                return None
            meta = pickle.loads(meta_data)
            task_id = meta.get("celery_task_id")
            if task_id:
                task = celery_app.AsyncResult(task_id)
                if task.state == "SUCCESS":
                    meta["status"] = "completed"
                    meta["progress"] = 100
                    if not meta.get("completed_at"):
                        meta["completed_at"] = datetime.now().isoformat()
                elif task.state == "FAILURE":
                    meta["status"] = "failed"
                    meta["error"] = str(task.info)
                elif task.state in ["STARTED", "PROGRESS"]:
                    meta["status"] = "processing"
                    meta["progress"] = meta.get("progress", 50)
                elif task.state == "PENDING":
                    meta["status"] = "submitted"
                    meta["progress"] = 0
            return meta
        except Exception as e:
            logger.error(f"Failed to get batch status: {e}", exc_info=True)
            return None

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

    def get_batch_results(self, batch_id: str) -> Optional[Dict]:
        if not self.redis_client:
            return None
        try:
            results_data = self.redis_client.get(f"batch_results:{batch_id}")
            if results_data:
                return pickle.loads(results_data)
            return None
        except Exception as e:
            logger.error(f"Failed to get batch results: {e}", exc_info=True)
            return None

    def list_recent_jobs(self, limit: int = 10, status_filter: Optional[str] = None) -> List[Dict]:
        if not self.redis_client:
            return []
        try:
            cursor = 0
            jobs = []
            while True:
                cursor, keys = self.redis_client.scan(cursor, match="batch_meta:*", count=100)
                for key in keys:
                    data = self.redis_client.get(key)
                    if data:
                        job = pickle.loads(data)
                        if status_filter and job.get("status") != status_filter:
                            continue
                        jobs.append(job)
                if cursor == 0:
                    break
            jobs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return jobs[:limit]
        except Exception as e:
            logger.error(f"Failed to list batch jobs: {e}", exc_info=True)
            return []

    def get_batch_summary(self, batch_id: str) -> Optional[Dict]:
        try:
            results = self.get_batch_results(batch_id)
            if results and "summary" in results:
                return results["summary"]
            
            status = self.get_batch_status(batch_id)
            if status:
                if status.get("status") == "processing":
                    return {"status": "processing", "message": "Batch still processing"}
                elif status.get("status") == "failed":
                    return {"status": "failed", "error": status.get("error")}
                elif status.get("status") == "completed":
                    if results:
                        total = results.get("total", 0)
                        predictions = results.get("results", [])
                        churn_count = sum(1 for p in predictions if p.get("prediction") == 1)
                        avg_prob = sum(p.get("probability", 0) for p in predictions) / total if total > 0 else 0
                        return {
                            "batch_id": batch_id,
                            "total_records": total,
                            "churn_predictions": churn_count,
                            "no_churn_predictions": total - churn_count,
                            "churn_rate": churn_count / total if total > 0 else 0,
                            "average_churn_probability": avg_prob
                        }
            return None
        except Exception as e:
            logger.error(f"Failed to get batch summary: {e}", exc_info=True)
            return None

    def delete_batch(self, batch_id: str) -> bool:
        if not self.redis_client:
            return False
        try:
            # Check if batch exists
            meta_data = self.redis_client.get(f"batch_meta:{batch_id}")
            if not meta_data:
                return False
            
            meta = pickle.loads(meta_data)
            if meta.get("status") == "processing":
                return False
            
            # Delete batch data
            self.redis_client.delete(f"batch_meta:{batch_id}")
            self.redis_client.delete(f"batch_results:{batch_id}")
            logger.info(f"Batch {batch_id} deleted")
            return True
        except Exception as e:
            logger.error(f"Failed to delete batch: {e}")
            return False

    def get_celery_task_id(self, batch_id: str) -> str:
        if not self.redis_client:
            return ""
        try:
            meta_data = self.redis_client.get(f"batch_meta:{batch_id}")
            if meta_data:
                meta = pickle.loads(meta_data)
                return meta.get("celery_task_id", "")
            return ""
        except Exception as e:
            logger.error(f"Failed to get celery task ID: {e}")
            return ""

    def submit_batch(self, request) -> BatchPredictionResponse:
        batch_id = self.create_batch(request.data, request.batch_name)
        return BatchPredictionResponse(
            batch_id=batch_id,
            status="submitted",
            total_records=len(request.data),
            celery_task_id=self.get_celery_task_id(batch_id),
            created_at=datetime.now()
        )