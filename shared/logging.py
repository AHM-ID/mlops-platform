import requests
import logging
from pythonjsonlogger import jsonlogger
import os
import sys
import json

class SyncHTTPHandler(logging.Handler):
    """Simple synchronous HTTP handler for Fluent Bit"""
    
    def __init__(self, fluent_bit_url="http://fluent-bit:8888"):
        super().__init__()
        self.fluent_bit_url = fluent_bit_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})
        
    def emit(self, record):
        try:
            log_entry = self.format(record)
            if isinstance(log_entry, str):
                try:
                    log_entry = json.loads(log_entry)
                except:
                    log_entry = {"message": log_entry}
            
            service = getattr(record, 'service', 'unknown')
            
            payload = {
                "log": json.dumps(log_entry),
                "service": service,
                "level": log_entry.get('level', 'INFO').lower(),
                "host": os.getenv('HOSTNAME', 'unknown')
            }
            
            self.session.post(f"{self.fluent_bit_url}/", json=payload, timeout=2)
            
        except Exception as e:
            import sys
            sys.stderr.write(f"HTTP logging failed: {e}\n")
    
    def close(self):
        self.session.close()
        super().close()


def setup_logging(service_name: str, level=logging.INFO, extra=None):
    logger = logging.getLogger()
    logger.setLevel(level)
    
    logger.handlers.clear()
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    json_formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(levelname)s %(name)s %(message)s %(service)s %(request_id)s %(duration_ms)s %(customer_id)s %(prediction)s %(probability)s',
        rename_fields={
            'asctime': 'timestamp',
            'levelname': 'level',
            'name': 'logger'
        },
        datefmt='%Y-%m-%dT%H:%M:%SZ'
    )
    console_handler.setFormatter(json_formatter)
    logger.addHandler(console_handler)
    
    try:
        from shared.config import FLUENT_BIT_URL
        http_handler = SyncHTTPHandler(fluent_bit_url=FLUENT_BIT_URL)
        http_handler.setLevel(level)
        http_handler.setFormatter(json_formatter)
        logger.addHandler(http_handler)
    except Exception as e:
        sys.stderr.write(f"HTTP logging failed: {e}\n")
    
    adapter_extra = {'service': service_name}
    if extra:
        adapter_extra.update(extra)
    
    class CustomLoggerAdapter(logging.LoggerAdapter):
        def process(self, msg, kwargs):
            extra = kwargs.get('extra', {})
            merged_extra = {**self.extra, **extra}
            kwargs['extra'] = merged_extra
            return msg, kwargs
    
    adapter = CustomLoggerAdapter(logger, adapter_extra)
    adapter.info(f"Logging initialized for {service_name}")
    
    return adapter