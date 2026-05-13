import redis
import json
import pickle
from typing import List, Dict, Optional
from datetime import datetime
from shared.config import REDIS_URL, RETRAIN_BATCH_SIZE, REDIS_MAX_CONNECTIONS
from shared.logging import setup_logging

logger = setup_logging("retrain_queue")

RETRAIN_QUEUE_KEY = "retrain:training_data"

class RetrainQueueManager:
    def __init__(self):
        try:
            self.redis_client = redis.from_url(
                REDIS_URL, 
                decode_responses=False,
                max_connections=REDIS_MAX_CONNECTIONS,  # Add connection pool limit
                socket_keepalive=True,
                socket_connect_timeout=5
            )
            self.redis_client.ping()
            logger.info("Retrain queue manager connected to Redis")
        except Exception as e:
            logger.warning(f"Redis connection failed for retrain queue: {e}")
            self.redis_client = None

    
    def add_prediction(self, features: Dict, prediction: int, probability: float):
        """Automatically store prediction for future retraining"""
        if self.redis_client is None:
            return False
        
        try:
            record = {
                "features": features,
                "label": None,
                "prediction": prediction,
                "probability": probability,
                "timestamp": datetime.now().isoformat(),
                "source": "auto_prediction"
            }
            serialized = pickle.dumps(record)
            self.redis_client.rpush(RETRAIN_QUEUE_KEY, serialized)
            logger.debug(f"Prediction logged to retrain queue | pred={prediction} prob={probability:.3f}")
            return True
        except Exception as e:
            logger.error(f"Failed to log prediction: {e}")
            return False
        
    def add_training_record(self, features: Dict, label: int) -> bool:
        if self.redis_client is None:
            return False
        
        try:
            record = {
                "features": features,
                "label": label,
                "timestamp": datetime.now().isoformat(),
                "source": "manual_collection"
            }
            serialized = pickle.dumps(record)
            self.redis_client.rpush(RETRAIN_QUEUE_KEY, serialized)
            logger.info(f"Training record added to retrain queue | label={label}")
            return True
        except Exception as e:
            logger.error(f"Failed to add training record: {e}")
            return False
    
    def get_training_batch(self, batch_size: int = RETRAIN_BATCH_SIZE) -> List[Dict]:
        if self.redis_client is None:
            logger.warning("Cannot get training batch: Redis unavailable")
            return []
        
        try:
            pipe = self.redis_client.pipeline()
            pipe.lrange(RETRAIN_QUEUE_KEY, 0, batch_size - 1)
            pipe.ltrim(RETRAIN_QUEUE_KEY, batch_size, -1)
            results = pipe.execute()
            
            batch = results[0]
            training_data = []
            
            for item in batch:
                try:
                    record = pickle.loads(item)
                    training_data.append(record)
                except Exception as e:
                    logger.warning(f"Failed to deserialize record: {e}")
            
            logger.info(f"Retrieved {len(training_data)} records from retrain queue")
            return training_data
        except Exception as e:
            logger.error(f"Failed to get training batch: {e}")
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