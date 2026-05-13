import redis
import hashlib
import json
import pandas as pd
from typing import Optional, Dict, Any
from shared.config import REDIS_URL
from shared.logging import setup_logging
from shared.metrics import CACHE_HITS, CACHE_MISSES, FEATURE_CACHE_HIT_RATE

logger = setup_logging("feature_store")

# Initialize Redis connection
try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    redis_client.ping()
    logger.info("Redis connection established for feature store")
except Exception as e:
    logger.warning(f"Redis connection failed, caching disabled: {e}")
    redis_client = None

def update_cache_hit_rate():
    """Update the Prometheus gauge with current cache hit rate"""
    try:
        if redis_client is None:
            FEATURE_CACHE_HIT_RATE.set(0)
            return
        
        total_hits = int(redis_client.get("cache_total_hits") or 0)
        total_misses = int(redis_client.get("cache_total_misses") or 0)
        
        if total_hits + total_misses > 0:
            hit_rate = total_hits / (total_hits + total_misses)
        else:
            hit_rate = 0.0
        
        FEATURE_CACHE_HIT_RATE.set(hit_rate)
    except Exception as e:
        logger.error(f"Failed to update cache hit rate: {e}")

def get_feature_hash(df: pd.DataFrame) -> str:
    """Generate unique hash for input data"""
    # Sort columns to ensure consistent hash
    df_sorted = df.reindex(sorted(df.columns), axis=1)
    hash_input = df_sorted.to_json(orient='records')
    return hashlib.md5(hash_input.encode()).hexdigest()

def get_cached_features(df: pd.DataFrame) -> Optional[pd.DataFrame]:
    """Retrieve cached features if available"""
    if redis_client is None:
        return None
    
    try:
        feature_hash = get_feature_hash(df)
        cached = redis_client.get(f"features:{feature_hash}")
        
        if cached:
            CACHE_HITS.labels(service='api').inc()
            logger.info(f"Cache hit for features: {feature_hash[:8]}")
            cached_data = json.loads(cached)
            redis_client.incr("cache_total_hits")
            update_cache_hit_rate()
            return pd.DataFrame(cached_data)
        else:
            CACHE_MISSES.labels(service='api').inc()
            logger.debug(f"Cache miss for features: {feature_hash[:8]}")
            redis_client.incr("cache_total_misses")
            update_cache_hit_rate()
            return None
            
    except Exception as e:
        logger.error(f"Failed to get cached features: {e}")
        return None

def cache_features(df: pd.DataFrame, X: pd.DataFrame, ttl: int = 3600) -> str:
    """Cache computed features with TTL in seconds (default 1 hour)"""
    if redis_client is None:
        return ""
    
    try:
        feature_hash = get_feature_hash(df)
        # Convert to list of lists for JSON serialization
        features_json = X.values.tolist()
        
        redis_client.setex(
            f"features:{feature_hash}", 
            ttl, 
            json.dumps({
                "features": features_json,
                "columns": X.columns.tolist(),
                "shape": X.shape
            })
        )
        
        # Track cache stats
        redis_client.incr("cache_total_writes")
        logger.info(f"Cached features for hash: {feature_hash[:8]}, TTL: {ttl}s")
        return feature_hash
        
    except Exception as e:
        logger.error(f"Failed to cache features: {e}")
        return ""

def get_cache_stats() -> Dict[str, Any]:
    """Get cache performance statistics"""
    if redis_client is None:
        return {"status": "disabled", "reason": "Redis connection failed"}
    
    try:
        stats = {
            "status": "active",
            "total_writes": int(redis_client.get("cache_total_writes") or 0),
            "total_hits": int(redis_client.get("cache_total_hits") or 0),
            "total_misses": int(redis_client.get("cache_total_misses") or 0)
        }
        
        if stats["total_hits"] + stats["total_misses"] > 0:
            stats["hit_rate"] = stats["total_hits"] / (stats["total_hits"] + stats["total_misses"])
        else:
            stats["hit_rate"] = 0
            
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get cache stats: {e}")
        return {"status": "error", "error": str(e)}

def clear_cache(batch_size: int = 100):
    if redis_client is None:
        return
    
    try:
        cursor = 0
        total_deleted = 0
        
        while True:
            cursor, keys = redis_client.scan(cursor, match="features:*", count=batch_size)
            if keys:
                redis_client.delete(*keys)
                total_deleted += len(keys)
            if cursor == 0:
                break
        
        logger.info(f"Cleared {total_deleted} cached features in batches")
        
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")