import os
import threading
import yaml
import time
import tempfile
import shutil
import hashlib
import requests
from datetime import datetime
from croniter import croniter
from git import Repo
from engine.we import WorkflowEngine
from commons.logs import get_logger
from commons.get_config import get_config
from engine.utils.github_webhook_helper import install_webhook
from urllib.parse import urlparse, urlunparse


logger = get_logger(__name__)
config = get_config()

BASE_URL = config["app"]["base_url"]


TRIGGER_THREADS = []
_cron_state = {}
_git_hash_cache = {}


def inject_token_into_url(url, token):
    if not token:
        return url

    parsed = urlparse(url)
    if parsed.username or parsed.password:
        raise ValueError("Repository URL should not already contain credentials.")

    netloc = f"{token}:x-oauth-basic@{parsed.netloc}"
    return urlunparse((parsed.scheme, netloc, parsed.path, "", "", ""))


def initialize_triggers(workflows_base_path, approval_manager):
    logger.info("[TRIGGER] Initializing trigger-based workflows")
    ignored_dirs = set(config["app"].get("ignored_workflow_dirs", []))
    for root, _, files in os.walk(workflows_base_path):
        if any(ignored in root.split(os.sep) for ignored in ignored_dirs):
            continue
        for file in files:
            if not file.endswith(".yaml"):
                continue
            wf_path = os.path.join(root, file)
            try:
                with open(wf_path, "r") as f:
                    workflow_dict = yaml.safe_load(f)
                    
                if not workflow_dict or not isinstance(workflow_dict, dict):
                    logger.warning(f"[TRIGGER] Skipping {wf_path} — YAML is empty or malformed")
                    continue

                trigger = workflow_dict.get("workflow", {}).get("trigger")

                if not trigger:
                    continue
                trigger_type = trigger.get("type")
                if trigger_type == "scheduled":
                    logger.info(f"[DEBUG] Registering scheduled trigger: {wf_path}")
                    _register_scheduled_trigger(wf_path, workflow_dict, trigger, approval_manager)
                elif trigger_type == "gitops":
                    logger.info(f"[DEBUG] Registering git trigger: {wf_path}")
                    trigger_method = trigger.get("method", "poll")
                    _register_git_trigger(wf_path, workflow_dict, trigger, approval_manager)

                    if trigger_method == "webhook":
                        token = trigger.get("token")
                        if not token:
                            logger.warning("[GITOPS] Webhook method requires a token")
                        else:
                            install_webhook(
                                repo_url=trigger.get("repo"),
                                token=token,
                                sawe_url=BASE_URL,
                                repo_name=os.path.relpath(wf_path, config["directories"]["workflows"]).split(os.sep)[0],
                                workflow_name=os.path.splitext(os.path.basename(wf_path))[0]
                            )
                elif trigger_type == "api":
                    # API trigger handling
                    logger.info(f"[TRIGGER] API trigger for {wf_path} is handled via endpoint")
                    # aigent trigger handling
                elif trigger_type == "aiagent":
                    logger.info(f"[TRIGGER] AI Agent workflow {wf_path} is handled externally via API")
    
                else:
                    logger.warning(f"[TRIGGER] Unknown trigger type: {trigger_type}")
            except Exception as e:
                logger.warning(f"[TRIGGER] Failed to process {wf_path}: {e}")

    if _cron_state:
        thread = threading.Thread(target=_schedule_loop, daemon=True)
        thread.start()
        TRIGGER_THREADS.append(thread)

def _register_scheduled_trigger(wf_path, workflow_dict, trigger, approval_manager):
    cron_expr = trigger.get("cron")
    wf_meta = workflow_dict.get("workflow", {})
    if not cron_expr:
        logger.warning(f"[TRIGGER] No cron expression in scheduled trigger")
        return

    wf_id = wf_meta.get("name", wf_path)
    repo = wf_path.split("/workflows/")[1].split("/")[0]
    workflow_name = os.path.splitext(os.path.basename(wf_path))[0]

    _cron_state[wf_id] = {
        "cron": cron_expr,
        "last_run": None,
        "repo": os.path.relpath(wf_path, config["directories"]["workflows"]).split(os.sep)[0],
        "workflow": os.path.splitext(os.path.basename(wf_path))[0],
        "wf_path": wf_path,
        "workflow_dict": workflow_dict,
        "approval_manager": approval_manager
    }
    logger.info(f"[SCHED] Registered scheduled trigger for {wf_id} with cron: {cron_expr}")




def trigger_scheduled_workflow(repo, workflow):
    payload = {"mode": "scheduled"}  # or custom, if needed
    url = f"{own_url}/api/{repo}/{workflow}"
    try:
        res = requests.post(url, json=payload)
        if res.status_code != 202:
            logger.warning(f"[SCHED] Trigger failed: {res.status_code} — {res.text}")
        else:
            logger.info(f"[SCHED] Successfully triggered {workflow}")
    except Exception as e:
        logger.exception(f"[SCHED] Error triggering {workflow}: {e}")


def _schedule_loop():
    logger.info("[TRIGGER] Scheduler thread started")

    # Prepopulate next_run if missing
    for wf_id, entry in _cron_state.items():
        cron_expr = entry["cron"]
        now = datetime.utcnow()
        if not entry.get("next_run"):
            entry["next_run"] = croniter(cron_expr, now).get_next(datetime)

    while True:
        now = datetime.utcnow()

        for wf_id, entry in _cron_state.items():
            next_run = entry.get("next_run")

            if not next_run:
                # Defensive fallback — recalculate
                entry["next_run"] = croniter(entry["cron"], now).get_next(datetime)
                continue

            if now >= next_run:
                repo = entry["repo"]
                workflow = entry["workflow"]
                logger.info(f"[SCHED] Triggering scheduled workflow {repo}/{workflow} at {now.isoformat()}")

                try:
                    url = f"{BASE_URL}/api/{repo}/{workflow}"
                    payload = {"mode": "scheduled"}
                    res = requests.post(url, json=payload)
                    logger.info(f"[SCHED] Triggered {workflow}: {res.status_code} — {res.text}")
                except Exception as e:
                    logger.exception(f"[SCHED] Error triggering {workflow}: {e}")

                # Update timestamps
                entry["last_run"] = now
                entry["next_run"] = croniter(entry["cron"], now).get_next(datetime)

        time.sleep(5)



def md5_of_paths(base_dir, file_paths):
    """Compute a combined MD5 hash of a list of specific files."""
    hash_md5 = hashlib.md5()
    for rel_path in sorted(file_paths):
        full_path = os.path.join(base_dir, rel_path)
        if os.path.exists(full_path) and os.path.isfile(full_path):
            with open(full_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
    return hash_md5.hexdigest()

def _register_git_trigger(wf_path, workflow_dict, trigger, approval_manager):
    raw_repo_url = trigger.get("repo")
    github_token = trigger.get("github_token")
    method = trigger.get("method", "poll")
    branch = trigger.get("branch", "main")
    files = [f.get("path") for f in trigger.get("files", [])]
    interval = int(trigger.get("poll_interval_seconds", 60))
    wf_name = workflow_dict["workflow"].get("name", wf_path)

    if method == "poll":
        if not raw_repo_url or not files:
            logger.warning(f"[GIT-TRIGGER] Poll method missing required fields: {wf_name}")
            return



        def poller():
            logger.info(f"[GIT-TRIGGER] Starting polling for: {raw_repo_url} ({wf_name}) every {interval}s")
            temp_dir = tempfile.mkdtemp()

            while True:
                try:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                    os.makedirs(temp_dir, exist_ok=True)

                    if github_token:
                        clone_url = raw_repo_url.replace("https://", f"https://{github_token}:x-oauth-basic@")
                    else: 
                        clone_url = raw_repo_url
                        
                    Repo.clone_from(clone_url, temp_dir, branch=branch, depth=1)
                    logger.info(f"Constructed URL is {clone_url}")
                    current_md5 = md5_of_paths(temp_dir, files)

                    if wf_name not in _git_hash_cache:
                        _git_hash_cache[wf_name] = current_md5
                        logger.info(f"[GIT-TRIGGER] Initial hash cached for {wf_name}: {current_md5}")
                    elif _git_hash_cache[wf_name] != current_md5:
                        logger.info(f"[GIT-TRIGGER] Change detected in {wf_name}, triggering workflow...")
                        engine = WorkflowEngine(approval_manager, workflow_dict, {}, repo_base_path=config["directories"]["modules"])
                        threading.Thread(target=engine.run, daemon=True).start()
                        _git_hash_cache[wf_name] = current_md5
                    else:
                        logger.debug(f"[GIT-TRIGGER] No change for {wf_name}")

                except Exception as e:
                    logger.error(f"[GIT-TRIGGER] Polling error for {wf_name}: {e}")

                time.sleep(interval)

        thread = threading.Thread(target=poller, daemon=True)
        thread.start()
        TRIGGER_THREADS.append(thread)

    else:
        logger.debug(f"[GIT-TRIGGER] Skipping polling for {wf_name} — method is '{method}'")
