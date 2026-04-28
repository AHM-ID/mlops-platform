import logging
from pythonjsonlogger import jsonlogger

def setup_logging(service_name: str) -> logging.LoggerAdapter:
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplication
    if logger.hasHandlers():
        logger.handlers.clear()

    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt='%(asctime)s %(levelname)s %(name)s %(message)s',
        rename_fields={'asctime': 'timestamp', 'levelname': 'level'},
        datefmt='%Y-%m-%dT%H:%M:%SZ'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # Inject service name into every log record
    return logging.LoggerAdapter(logger, {'service': service_name})