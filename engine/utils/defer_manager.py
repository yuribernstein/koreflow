# engine/utils/defer_manager.py

import os
import yaml
import time
import threading
import requests
from datetime import datetime
from commons.get_config import get_config
from commons.logs import get_logger

config = get_config()
logger = get_logger("defer_manager")

def load_deferred_runs():
    lifetime_dir = config["directories"]["lifetimes"]
    pending = {}
    for fname in os.listdir(lifetime_dir):
        if not fname.endswith(".yaml"):
            continue
        path = os.path.join(lifetime_dir, fname)
        try:
            with open(path, "r") as f:
                run = yaml.safe_load(f)
            uid = run.get("uid")
            defer_until = run.get("defer_until")
            if uid and defer_until:
                ts = datetime.fromisoformat(defer_until)
                pending[uid] = ts
        except Exception as e:
            logger.warning(f"[DEFER] Failed parsing {fname}: {e}")
    return pending

def run_defer_manager(poll_interval=30):
    def loop():
        while True:
            now = datetime.utcnow()
            pending = load_deferred_runs()
            for uid, ts in pending.items():
                if ts <= now:
                    try:
                        logger.info(f"[DEFER] Resuming {uid}")
                        resume_url = f"{config['app']['base_url']}/api/resume/{uid}"
                        requests.post(resume_url)
                    except Exception as e:
                        logger.warning(f"[DEFER] Error resuming {uid}: {e}")
            time.sleep(poll_interval)
    threading.Thread(target=loop, daemon=True).start()
