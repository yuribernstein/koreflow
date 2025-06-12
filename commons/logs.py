import logging
import os
from commons.get_config import get_config
config = get_config()
LOG_DIR = config["directories"]["logs"]

DEFAULT_LEVEL = config["logging"]["level"]
FORMAT = config["logging"]["format"]

os.makedirs(LOG_DIR, exist_ok=True)

def get_logger(name: str = __name__, level: str = DEFAULT_LEVEL):
    logger = logging.getLogger(name)
    logger.setLevel(level.upper())
    # logger.propagate = False
    # logger.handlers.clear() 

    log_path = os.path.join(LOG_DIR, f"{name.replace('.', '_')}.log")
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(logging.Formatter(FORMAT))
    logger.addHandler(file_handler)

    return logger
