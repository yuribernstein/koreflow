# recovery_loader.py

import os
import yaml
import asyncio
from engine.we import WorkflowEngine
import threading
from commons.logs import get_logger
logger = get_logger(__name__)
from commons.get_config import get_config
config = get_config()


LIFETIME_DIR = config["directories"]["lifetimes"]
MODULES_BASE = config["directories"]["modules"]

if not os.path.exists(LIFETIME_DIR):
    os.makedirs(LIFETIME_DIR)

def discover_recoverable_runs():
    runs = []
    for fname in os.listdir(LIFETIME_DIR):
        if not fname.endswith(".yaml"):
            continue
        if fname.startswith("~") or fname in ["completed"]:
            continue
        full_path = os.path.join(LIFETIME_DIR, fname)
        with open(full_path, "r") as f:
            lifetime_map = yaml.safe_load(f)
            runs.append(lifetime_map)
    return runs

def resume_workflow_from_lifetime(lifetime_map, approval_manager):
    from engine.we import WorkflowEngine

    workflow_dict = {"workflow": lifetime_map["workflow"]}
    context = lifetime_map.get("context", {})
    uid = lifetime_map["uid"]
    workflow_dict["uid"] = uid

    engine = WorkflowEngine(
        approval_manager=approval_manager,
        workflow_dict=workflow_dict,
        payload={},
        modules_base_path=MODULES_BASE,
        skip_payload_parse=True,
        injected_context=context
    )

    engine.workflow_uid = uid
    engine.lifetime_map = lifetime_map
    engine.context.update(context)


    if lifetime_map.get("reason") == "completed":
        logger.info(f"[RECOVERY] Workflow {uid} already completed, skipping")
        engine._archive_completed_workflow()  # This should move it to `completed/`
        return

    current_step = lifetime_map.get("current_step")
    if current_step:
        logger.info(f"[RECOVERY] Resuming workflow {uid} from step '{current_step}'")
        engine.rehydrate_pending_approval(current_step)

    threading.Thread(target=engine.run, daemon=True).start()
