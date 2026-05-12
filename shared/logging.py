import logging
import requests
from pythonjsonlogger import jsonlogger
from threading import Thread
from queue import Queue, Empty 
import os
import json

class AsyncHTTPHandler(logging.Handler):
    def __init__(self, fluent_bit_url="http://fluent-bit:8888"):
        super().__init__()
        self.fluent_bit_url = fluent_bit_url.rstrip('/')
        self.queue = Queue()
        self.running = True
        self.thread = Thread(target=self._send_logs, daemon=True)
        self.thread.start()
    
    def emit(self, record):
        try:
            log_entry = self.format(record)
            
            if isinstance(log_entry, str):
                try:
                    log_entry = json.loads(log_entry)
                except:
                    log_entry = {"message": log_entry, "log": log_entry}
            
            log_message = json.dumps(log_entry)
            payload = {"log": log_message}
            
            self.queue.put(payload)
        except Exception as e:
            print(f"Error in emit: {e}")
    
    def _send_logs(self):
        session = requests.Session()
        while self.running:
            try:
                payload = self.queue.get(timeout=1)
                try:
                    response = session.post(
                        f"{self.fluent_bit_url}/",
                        json=payload,
                        timeout=0.5,
                        headers={"Content-Type": "application/json"}
                    )
                    if response.status_code != 200:
                        print(f"Fluent-bit returned {response.status_code}: {response.text}")
                except requests.exceptions.RequestException as req_err:
                    print(f"Request error to fluent-bit: {req_err}")
            except Empty:
                continue
            except Exception as e:
                print(f"Unexpected error in log sender: {type(e).__name__}: {e}")

def setup_logging(service_name: str):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    if logger.hasHandlers():
        logger.handlers.clear()
    
    console_handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(levelname)s %(name)s %(message)s',
        rename_fields={'asctime': 'timestamp', 'levelname': 'level'},
        datefmt='%Y-%m-%dT%H:%M:%SZ'
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    try:
        if os.path.exists('/.dockerenv') or os.path.exists('/run/.containerenv'):
            import time
            time.sleep(2) 
            http_handler = AsyncHTTPHandler()
            http_handler.setFormatter(formatter)
            logger.addHandler(http_handler)
            logger.info(f"Fluent-bit HTTP logging enabled for {service_name}")
    except Exception as e:
        logger.warning(f"Failed to setup Fluent-bit HTTP handler: {e}")
    
    return logging.LoggerAdapter(logger, {'service': service_name})