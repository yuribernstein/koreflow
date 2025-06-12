# lifetime_manager.py

import os
import threading
import queue
import yaml
import shutil
import time
from datetime import datetime
from commons.logs import get_logger
logger = get_logger("lifetime_manager")
from commons.get_config import get_config
config = get_config()
from commons.utils import retry_this

LIFETIME_DIR = config["directories"]["lifetimes"]
MODULES_BASE = config["directories"]["modules"]

COMPLETED_DIR = os.path.join(LIFETIME_DIR, "completed")

os.makedirs(LIFETIME_DIR, exist_ok=True)
os.makedirs(COMPLETED_DIR, exist_ok=True)

# Ensure the completed directory exists
logger.info(f"[LIFETIME] Lifetime directory: {LIFETIME_DIR}")
logger.info(f"[LIFETIME] Completed directory: {COMPLETED_DIR}")

_lifetime_queue = queue.Queue()
_file_lock = threading.Lock()

def _get_lifetime_path(uid):
    return os.path.join(LIFETIME_DIR, f"{uid}.yaml")

def _get_completed_path(uid):
    return os.path.join(COMPLETED_DIR, f"{uid}.yaml")

class LifetimeManager:
    def __init__(self):
        self.running = True
        self.worker = threading.Thread(target=self._process_loop, daemon=True)
        self.worker.start()

    def stop(self):
        self.running = False
        _lifetime_queue.put(None)

    def _process_loop(self):
        while self.running:
            item = _lifetime_queue.get()
            if item is None:
                break
            uid, lifetime_map = item
            try:
                with _file_lock:
                    with open(_get_lifetime_path(uid), "w") as f:
                        yaml.safe_dump(lifetime_map, f)
            except Exception as e:
                print(f"[ERROR] Failed to write lifetime for {uid}: {e}")

    def update(self, uid, lifetime_map):
        _lifetime_queue.put((uid, lifetime_map))

    @retry_this(2)
    def mark_complete(self, uid):
        time.sleep(0.1) # Ensure the file is written before moving
        with _file_lock:
            src = _get_lifetime_path(uid)
            dst = _get_completed_path(uid)
            if os.path.exists(src):
                shutil.move(src, dst)

# Singleton
lifetime_manager = LifetimeManager()
