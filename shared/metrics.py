# shared/metrics.py
import os
import psutil
import threading
import time
from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry

_METRICS_REGISTRY = None

def get_metrics_registry():
    global _METRICS_REGISTRY
    if _METRICS_REGISTRY is None:
        _METRICS_REGISTRY = CollectorRegistry()
    return _METRICS_REGISTRY

REGISTRY = get_metrics_registry()

CPU_PERCENT = Gauge('process_cpu_usage_percent', 'CPU usage percentage (0-100)', registry=REGISTRY)
MEMORY_PERCENT = Gauge('process_memory_usage_percent', 'Memory usage percentage (0-100)', registry=REGISTRY)
MLFLOW_STATUS = Gauge('mlflow_up', 'MLflow service status (1=up, 0=down)', registry=REGISTRY)
REDIS_STATUS = Gauge('redis_up', 'Redis service status (1=up, 0=down)', registry=REGISTRY)
POSTGRES_STATUS = Gauge('postgres_up', 'PostgreSQL service status (1=up, 0=down)', registry=REGISTRY)

CACHE_HITS = Counter('feature_cache_hits_total', 'Feature cache hits', ['service'], registry=REGISTRY)
CACHE_MISSES = Counter('feature_cache_misses_total', 'Feature cache misses', ['service'], registry=REGISTRY)
CACHE_WRITES = Counter('feature_cache_writes_total', 'Feature cache writes', ['service'], registry=REGISTRY)

RETRAIN_QUEUE_LENGTH = Gauge('retrain_queue_length', 'Pending records in retrain queue', registry=REGISTRY)
RETRAIN_SUCCESS = Counter('retrain_success_total', 'Successful retraining runs', registry=REGISTRY)
RETRAIN_FAILURE = Counter('retrain_failure_total', 'Failed retraining runs', registry=REGISTRY)
RETRAIN_DURATION = Histogram('retrain_duration_seconds', 'Retraining duration', registry=REGISTRY)

PREDICTION_LATENCY = Histogram('prediction_latency_seconds', 'Prediction latency', ['model_version'], registry=REGISTRY)

REQUESTS = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'], registry=REGISTRY)
REQUEST_DURATION = Histogram('api_request_duration_seconds', 'Request duration', ['method', 'endpoint'], registry=REGISTRY)
ACTIVE_REQUESTS = Gauge('api_active_requests', 'Active requests', registry=REGISTRY)

MODEL_ACTIVE_VERSION = Gauge('model_active_version', 'Active model version number', registry=REGISTRY)
MODEL_AUC_SCORE = Gauge('model_auc_score', 'Current production model AUC score', registry=REGISTRY)
FEATURE_CACHE_HIT_RATE = Gauge('feature_cache_hit_rate', 'Feature cache hit rate', registry=REGISTRY)

PREDICTION_OUTCOME_TOTAL = Counter('prediction_outcome_total', 'Total predictions by outcome', ['outcome'], registry=REGISTRY)

DATASET_DRIFT = Gauge('dataset_drift', 'Data drift detected (1) or not (0)', registry=REGISTRY)
DRIFTED_COLUMNS_COUNT = Gauge('drifted_columns_count', 'Number of drifted columns', registry=REGISTRY)

def get_registry():
    return REGISTRY

def set_model_metrics(version: str, auc: float):
    try:
        version_float = float(version) if version else 0.0
        MODEL_ACTIVE_VERSION.set(version_float)
        MODEL_AUC_SCORE.set(auc)
    except Exception as e:
        import sys
        sys.stderr.write(f"Failed to set model metrics: {e}\n")

def start_system_metrics_collector():
    def collect():
        process = psutil.Process()
        while True:
            try:
                cpu_percent = process.cpu_percent(interval=1)
                CPU_PERCENT.set(cpu_percent)
                mem_percent = process.memory_percent()
                MEMORY_PERCENT.set(mem_percent)
            except Exception:
                pass
            time.sleep(15)
    thread = threading.Thread(target=collect, daemon=True)
    thread.start()