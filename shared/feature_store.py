import hashlib
import pickle
import pandas as pd
from typing import Optional, Dict, Any, List, Tuple
from shared.config import CACHE_TTL_SECONDS, get_redis_client
from shared.logging import setup_logging

logger = setup_logging("feature_store")

_metrics = None

def _get_metrics():
    global _metrics
    if _metrics is None:
        from shared.metrics import CACHE_HITS, CACHE_MISSES, FEATURE_CACHE_HIT_RATE
        _metrics = {
            'hits': CACHE_HITS,
            'misses': CACHE_MISSES,
            'hit_rate': FEATURE_CACHE_HIT_RATE
        }
    return _metrics

try:
    redis_client = get_redis_client(decode_responses=False)
    redis_client.ping()
    logger.info("Redis connection established for feature store")
except Exception as e:
    logger.warning(f"Redis connection failed, caching disabled: {e}")
    redis_client = None

def update_cache_hit_rate():
    try:
        if redis_client is None:
            metrics = _get_metrics()
            metrics['hit_rate'].set(0)
            return
        total_hits = int(redis_client.get("cache_total_hits") or 0)
        total_misses = int(redis_client.get("cache_total_misses") or 0)
        if total_hits + total_misses > 0:
            hit_rate = total_hits / (total_hits + total_misses)
        else:
            hit_rate = 0.0
        metrics = _get_metrics()
        metrics['hit_rate'].set(hit_rate)
    except Exception as e:
        logger.error(f"Failed to update cache hit rate: {e}")

def get_feature_hash(df: pd.DataFrame) -> str:
    df_sorted = df.reindex(sorted(df.columns), axis=1)
    hash_input = df_sorted.to_json(orient='records', sort_keys=True)
    return hashlib.md5(hash_input.encode()).hexdigest()

def get_cached_features(df: pd.DataFrame, model_version: str = None) -> Optional[pd.DataFrame]:
    if redis_client is None:
        return None
    try:
        feature_hash = get_feature_hash(df)
        version_suffix = f":v{model_version}" if model_version else ""
        key = f"features:{feature_hash}{version_suffix}"
        cached = redis_client.get(key)
        if cached:
            metrics = _get_metrics()
            metrics['hits'].labels(service='api').inc()
            redis_client.incr("cache_total_hits")
            logger.debug(f"Cache hit: {key[:16]}")
            return pickle.loads(cached)
        else:
            metrics = _get_metrics()
            metrics['misses'].labels(service='api').inc()
            redis_client.incr("cache_total_misses")
            return None
    except Exception as e:
        logger.error(f"Failed to get cached features: {e}")
        return None

def cache_features(df: pd.DataFrame, X: pd.DataFrame, ttl: int = None, model_version: str = None) -> str:
    if redis_client is None:
        return ""
    if ttl is None:
        ttl = CACHE_TTL_SECONDS
    try:
        feature_hash = get_feature_hash(df)
        version_suffix = f":v{model_version}" if model_version else ""
        key = f"features:{feature_hash}{version_suffix}"
        redis_client.setex(key, ttl, pickle.dumps(X))
        redis_client.incr("cache_total_writes")
        logger.debug(f"Cached features: {key[:16]}, TTL={ttl}s")
        return key
    except Exception as e:
        logger.error(f"Failed to cache features: {e}")
        return ""

def get_cache_stats() -> Dict[str, Any]:
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

def clear_cache(model_version: str = None, batch_size: int = 100):
    if redis_client is None:
        return
    try:
        cursor = 0
        total_deleted = 0
        pattern = f"features:*{f':v{model_version}' if model_version else ''}"
        while True:
            cursor, keys = redis_client.scan(cursor, match=pattern, count=batch_size)
            if keys:
                redis_client.delete(*keys)
                total_deleted += len(keys)
            if cursor == 0:
                break
        logger.info(f"Cleared {total_deleted} cached features (pattern: {pattern})")
    except Exception as e:
        logger.error(f"Failed to clear cache: {e}")

def clear_cache_for_model_version(model_version: str):
    if redis_client is None:
        logger.warning("Redis not available, cannot clear cache for model version")
        return
    try:
        pattern = f"features:*:v{model_version}"
        cursor = 0
        deleted = 0
        while True:
            cursor, keys = redis_client.scan(cursor, match=pattern, count=100)
            if keys:
                redis_client.delete(*keys)
                deleted += len(keys)
            if cursor == 0:
                break
        logger.info(f"Cleared {deleted} cache entries for model version v{model_version}")
    except Exception as e:
        logger.error(f"Failed to clear cache for model version {model_version}: {e}")

def get_or_prepare_features(df: pd.DataFrame, model_version: str, columns: List[str], ttl: int = None) -> pd.DataFrame:
    cached = get_cached_features(df, model_version)
    if cached is not None:
        return cached
    X = FeatureStore.prepare(df, training=False, columns=columns)
    cache_features(df, X, ttl or CACHE_TTL_SECONDS, model_version)
    return X

class FeatureStore:
    @staticmethod
    def _drop_customer_id(df: pd.DataFrame) -> pd.DataFrame:
        if "customerID" in df.columns:
            return df.drop(columns=["customerID"])
        return df

    @staticmethod
    def _coerce_total_charges(df: pd.DataFrame) -> pd.DataFrame:
        df["TotalCharges"] = pd.to_numeric(df["TotalCharges"], errors="coerce")
        return df

    @staticmethod
    def _get_categorical_columns(df: pd.DataFrame) -> List[str]:
        categorical = df.select_dtypes(include=["object"]).columns.tolist()
        if "Churn" in categorical:
            categorical.remove("Churn")
        return categorical

    @staticmethod
    def _encode_categoricals(df: pd.DataFrame) -> pd.DataFrame:
        categorical = FeatureStore._get_categorical_columns(df)
        return pd.get_dummies(df, columns=categorical)

    @staticmethod
    def _split_target(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, pd.Index]:
        y = df["Churn"].map({"Yes": 1, "No": 0})
        X = df.drop(columns=["Churn"])
        return X, y, X.columns

    @staticmethod
    def _align_columns(df: pd.DataFrame, columns: List[str]) -> pd.DataFrame:
        for col in columns:
            if col not in df.columns:
                df[col] = 0
        return df[columns]

    @classmethod
    def prepare(cls, df: pd.DataFrame, training: bool = True, columns: Optional[List[str]] = None) -> Any:
        df = df.copy()
        df = cls._drop_customer_id(df)
        df = cls._coerce_total_charges(df)
        df = df.dropna()
        df = cls._encode_categoricals(df)
        if training:
            return cls._split_target(df)
        else:
            if columns is None:
                raise ValueError("For inference, columns must be provided")
            return cls._align_columns(df, columns)

    @classmethod
    def prepare_with_cache(cls, df: pd.DataFrame, model_version: str, columns: List[str], ttl: int = None) -> pd.DataFrame:
        return get_or_prepare_features(df, model_version, columns, ttl)
