import redis
import json
import pickle
import uuid
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from shared.config import REDIS_URL, RETRAIN_BATCH_SIZE
from shared.logging import setup_logging

logger = setup_logging("retrain_queue")

RETRAIN_QUEUE_KEY = "retrain:training_data"

class RetrainQueueManager:
    def __init__(self):
        try:
            self.redis_client = redis.from_url(
                REDIS_URL,
                decode_responses=False,
                socket_connect_timeout=5
            )
            self.redis_client.ping()
            logger.info("Retrain queue manager connected to Redis")
        except Exception as e:
            logger.warning(f"Redis connection failed for retrain queue: {e}")
            self.redis_client = None

    def add_prediction(self, features: Dict, prediction: int, probability: float, customer_id: str = None, prediction_id: str = None) -> str:
        if self.redis_client is None:
            return ""
        try:
            record_id = prediction_id or str(uuid.uuid4())
            record = {
                "id": record_id,
                "features": features,
                "prediction": prediction,
                "probability": probability,
                "prediction_timestamp": datetime.now().isoformat(),
                "label": None,
                "label_timestamp": None,
                "validation_status": "pending",
                "customer_id": customer_id,
                "source": "auto_prediction"
            }
            serialized = pickle.dumps(record)
            self.redis_client.rpush(RETRAIN_QUEUE_KEY, serialized)
            logger.debug(f"Prediction logged: {record_id}, pred={prediction}")
            return record_id
        except Exception as e:
            logger.error(f"Failed to log prediction: {e}")
            return ""

    def add_training_record(self, features: Dict, label: int) -> bool:
        if self.redis_client is None:
            return False
        try:
            record_id = str(uuid.uuid4())
            record = {
                "id": record_id,
                "features": features,
                "prediction": None,
                "probability": None,
                "prediction_timestamp": None,
                "label": label,
                "label_timestamp": datetime.now().isoformat(),
                "validation_status": "verified",
                "customer_id": None,
                "source": "manual_collection"
            }
            serialized = pickle.dumps(record)
            self.redis_client.rpush(RETRAIN_QUEUE_KEY, serialized)
            logger.info(f"Training record added: {record_id}, label={label}")
            return True
        except Exception as e:
            logger.error(f"Failed to add training record: {e}")
            return False

    def update_label(self, record_id: str, actual_label: int) -> bool:
        if self.redis_client is None:
            return False
        try:
            all_records = self._get_all_records()
            for i, record in enumerate(all_records):
                if record.get("id") == record_id:
                    record["label"] = actual_label
                    record["label_timestamp"] = datetime.now().isoformat()
                    record["validation_status"] = "verified"
                    self._update_record_at_index(i, record)
                    logger.info(f"Label updated for {record_id}: {actual_label}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to update label: {e}")
            return False

    def get_training_batch(self, batch_size: int = None) -> List[Dict]:
        if self.redis_client is None:
            return []
        if batch_size is None:
            batch_size = RETRAIN_BATCH_SIZE
        try:
            all_records = self._get_all_records()
            valid_records = [
                r for r in all_records
                if r.get("label") is not None
                and r.get("validation_status") == "verified"
            ]
            valid_records.sort(key=lambda x: x.get("prediction_timestamp") or x.get("label_timestamp", ""))
            batch = valid_records[:batch_size]
            self._remove_records([r["id"] for r in batch])
            logger.info(f"Retrieved {len(batch)} validated records for training")
            return batch
        except Exception as e:
            logger.error(f"Failed to get training batch: {e}")
            return []

    def get_recent_predictions(self, hours: int = 24, limit: int = 10000) -> List[Dict]:
        """Get recent predictions for drift detection"""
        if self.redis_client is None:
            return []
        try:
            all_records = self._get_all_records()
            cutoff = datetime.now() - timedelta(hours=hours)
            recent = []
            for rec in all_records:
                pred_time = rec.get("prediction_timestamp")
                if pred_time:
                    try:
                        dt = datetime.fromisoformat(pred_time)
                        if dt > cutoff:
                            recent.append(rec)
                    except:
                        pass
                if len(recent) >= limit:
                    break
            logger.info(f"Retrieved {len(recent)} recent predictions for drift analysis")
            return recent
        except Exception as e:
            logger.error(f"Failed to get recent predictions: {e}")
            return []

    def get_queue_length(self) -> int:
        if self.redis_client is None:
            return 0
        try:
            return self.redis_client.llen(RETRAIN_QUEUE_KEY)
        except Exception as e:
            logger.error(f"Failed to get queue length: {e}")
            return 0

    def clear_queue(self) -> bool:
        if self.redis_client is None:
            return False
        try:
            self.redis_client.delete(RETRAIN_QUEUE_KEY)
            logger.info("Retrain queue cleared")
            return True
        except Exception as e:
            logger.error(f"Failed to clear queue: {e}")
            return False

    def expire_old_pending(self, days: int = 30) -> int:
        if self.redis_client is None:
            return 0
        try:
            all_records = self._get_all_records()
            cutoff = datetime.now() - timedelta(days=days)
            expired_ids = []
            for record in all_records:
                if record.get("validation_status") == "pending":
                    pred_time = record.get("prediction_timestamp")
                    if pred_time:
                        try:
                            pred_dt = datetime.fromisoformat(pred_time)
                            if pred_dt < cutoff:
                                expired_ids.append(record.get("id"))
                        except:
                            pass
            self._remove_records(expired_ids)
            logger.info(f"Expired {len(expired_ids)} pending records older than {days} days")
            return len(expired_ids)
        except Exception as e:
            logger.error(f"Failed to expire old records: {e}")
            return 0

    def _get_all_records(self) -> List[Dict]:
        if self.redis_client is None:
            return []
        try:
            raw_records = self.redis_client.lrange(RETRAIN_QUEUE_KEY, 0, -1)
            records = []
            for item in raw_records:
                try:
                    records.append(pickle.loads(item))
                except:
                    continue
            return records
        except Exception as e:
            logger.error(f"Failed to get all records: {e}")
            return []

    def _update_record_at_index(self, index: int, record: Dict) -> bool:
        if self.redis_client is None:
            return False
        try:
            serialized = pickle.dumps(record)
            self.redis_client.lset(RETRAIN_QUEUE_KEY, index, serialized)
            return True
        except Exception as e:
            logger.error(f"Failed to update record: {e}")
            return False

    def _remove_records(self, record_ids: List[str]) -> int:
        if self.redis_client is None or not record_ids:
            return 0
        try:
            all_records = self._get_all_records()
            remaining = [r for r in all_records if r.get("id") not in record_ids]
            self.redis_client.delete(RETRAIN_QUEUE_KEY)
            for record in remaining:
                self.redis_client.rpush(RETRAIN_QUEUE_KEY, pickle.dumps(record))
            return len(record_ids)
        except Exception as e:
            logger.error(f"Failed to remove records: {e}")
            return 0