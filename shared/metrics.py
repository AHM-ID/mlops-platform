from prometheus_client import Counter, Gauge, Histogram
import psutil
import threading
import time

CPU_PERCENT = Gauge('process_cpu_usage_percent', 'CPU usage percentage (0-100)')
MEMORY_PERCENT = Gauge('process_memory_usage_percent', 'Memory usage percentage (0-100)')
MLFLOW_STATUS = Gauge('mlflow_up', 'MLflow service status (1=up, 0=down)')
REDIS_STATUS = Gauge('redis_up', 'Redis service status (1=up, 0=down)')
POSTGRES_STATUS = Gauge('postgres_up', 'PostgreSQL service status (1=up, 0=down)')
CACHE_HITS = Counter('feature_cache_hits_total', 'Feature cache hits', ['service'])
CACHE_MISSES = Counter('feature_cache_misses_total', 'Feature cache misses', ['service'])
CACHE_WRITES = Counter('feature_cache_writes_total', 'Feature cache writes', ['service'])
RETRAIN_QUEUE_LENGTH = Gauge('retrain_queue_length', 'Pending records in retrain queue')
RETRAIN_SUCCESS = Counter('retrain_success_total', 'Successful retraining runs')
RETRAIN_FAILURE = Counter('retrain_failure_total', 'Failed retraining runs')
RETRAIN_DURATION = Histogram('retrain_duration_seconds', 'Retraining duration')
PREDICTION_LATENCY = Histogram('prediction_latency_seconds', 'Prediction latency', ['model_version'])
REQUESTS = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('api_request_duration_seconds', 'Request duration', ['method', 'endpoint'])
ACTIVE_REQUESTS = Gauge('api_active_requests', 'Active requests')
MODEL_ACTIVE_VERSION = Gauge('model_active_version', 'Active model version number')
MODEL_AUC_SCORE = Gauge('model_auc_score', 'Current production model AUC score')
FEATURE_CACHE_HIT_RATE = Gauge('feature_cache_hit_rate', 'Feature cache hit rate')
PREDICTION_OUTCOME_TOTAL = Counter('prediction_outcome_total', 'Total predictions by outcome', ['outcome'])
DATASET_DRIFT = Gauge('dataset_drift', 'Data drift detected (1) or not (0)')
DRIFTED_COLUMNS_COUNT = Gauge('drifted_columns_count', 'Number of drifted columns')

def start_system_metrics_collector():
    """Start background thread to collect system metrics"""
    def collect():
        process = psutil.Process()
        while True:
            cpu_percent = process.cpu_percent(interval=1)
            CPU_PERCENT.set(cpu_percent)
            
            mem_percent = process.memory_percent()
            MEMORY_PERCENT.set(mem_percent)
            
            time.sleep(15)
    
    thread = threading.Thread(target=collect, daemon=True)
    thread.start()