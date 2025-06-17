# koreflow.py

from flask import Flask, request, jsonify
import os
import yaml
import threading
import time
import uuid
from flask import render_template_string, render_template, send_from_directory
from commons.logs import get_logger
from engine.utils import match_engine
from engine.utils.recovery_loader import discover_recoverable_runs, resume_workflow_from_lifetime
from engine.approval.approval_channel import approval_request_q, approval_result_q
from engine.approval.approval_manager import ApprovalManager
from engine.we import WorkflowEngine
from git import Repo, GitCommandError
from engine.utils.trigger_loader import initialize_triggers
from waitress import serve
from korectl.korectl import validate_workflow_from_file
import engine.management.mock_md_server as mock_md_server
from engine.management.poller import poll_modules

from commons.get_config import get_config
config = get_config()

logger = get_logger("flask_app")

running_engines = {}  # uid → engine
from flask import request

AIAGENT_INPUTS = {}  # Key: (uid, step_id) → dict



app = Flask(__name__)
try:
    MODULES_BASE = config["directories"]["modules"]
    WORKFLOWS_BASE = config["directories"]["workflows"]
    PORT = config['app']['port']
except Exception as e:
    logger.exception("[WEB SERVER] Error reading config")
    raise e

approval_routes = {}
is_workflow_running = False
engine_paused = False


# Init approval manager
approval_manager = ApprovalManager(approval_request_q, approval_result_q)

def handle_approval_hit(uid, step_id):
    logger.info(f"[WEB SERVER] Approval clicked: {uid}/{step_id}")
    route_key = f"/api/approve/{uid}/{step_id}"
    approval_routes.pop(route_key, None)
    logger.info(f"[WEB SERVER] Approval route {route_key} removed")
    approval_manager.resolve(uid, step_id, "approved")
    # Notify the approval manager
    approval_result_q.put({
        "uid": uid,
        "step_id": step_id,
        "status": "approved"
    })


def register_approval_route(uid, step_id, timeout_minutes):
    logger.info(f"Registering approval route for {uid} at step {step_id} with timeout {timeout_minutes} minutes")
    route_key = f"/api/approve/{uid}/{step_id}"
    approval_routes[route_key] = True

    def expire():
        time.sleep(timeout_minutes * 60)
        if route_key in approval_routes:
            approval_result_q.put({
                "uid": uid,
                "step_id": step_id,
                "status": "timeout"
            })
            approval_routes.pop(route_key, None)

    threading.Thread(target=expire, daemon=True).start()

def approval_listener():
    while True:
        try:
            request_data = approval_request_q.get()
            logger.info(f"[APPROVAL-LISTENER] Got request: {request_data}")
            if request_data["action"] == "register":
                register_approval_route(
                    uid=request_data["uid"],
                    step_id=request_data["step_id"],
                    timeout_minutes=min(request_data.get("timeout_minutes", 30), 1440)
                )
                logger.info(f"[APPROVAL] Registered route for {request_data['uid']}/{request_data['step_id']}")
        except Exception as e:
            logger.exception("[APPROVAL-LISTENER] Error")

@app.route("/api/approve/<uid>/<step_id>", methods=["GET"])
def handle_approval(uid, step_id):
    route_key = f"/api/approve/{uid}/{step_id}"
    if route_key in approval_routes:
        handle_approval_hit(uid, step_id)
        return jsonify({"status": "approved"})
    return jsonify({"status": "invalid or expired link"}), 404



@app.route("/api/<repo>/<workflow>", methods=["POST"])
def handle_workflow_request(repo, workflow):
    try:
        workflow_file = os.path.join(WORKFLOWS_BASE, repo, f"{workflow}.yaml")
        if not os.path.isfile(workflow_file):
            return jsonify({"status": "error", "message": "Workflow not found"}), 404

        with open(workflow_file, "r") as f:
            workflow_dict = yaml.safe_load(f)

        payload = {"payload": request.get_json()}

        with open(workflow_file, "r") as f:
            workflow_dict = yaml.safe_load(f)

        # ssign a UID externally to ensure consistency
        uid = str(uuid.uuid4())
        workflow_dict["uid"] = uid

        payload = {"payload": request.get_json(), "workflow_uid": uid}

        # Determine workflow type
        workflow_type = workflow_dict.get("workflow", {}).get("trigger", {}).get("type", "api")

        # For aiagents, assign access key
        if workflow_type == "aiagent":
            access_key = f"agent-{uuid.uuid4().hex[:8]}"
            workflow_dict["access_key"] = access_key
            payload["access_key"] = access_key

        # Proceed with execution
        run_workflow_async(workflow_dict, payload)
        response = {"status": "accepted", "workflow_uid": uid}
        if workflow_type == "aiagent":
            response["access_key"] = access_key
        return jsonify(response), 202

    except Exception as e:
        logger.exception("[WORKFLOW] Error handling request")
        return jsonify({"status": "error", "error": str(e)}), 500


def run_workflow_async(workflow_dict, payload):
    def thread_runner():
        global is_workflow_running, engine_paused
        while engine_paused:
            logger.info("[ENGINE] Engine paused. Waiting before running workflow...")
            time.sleep(1)
        is_workflow_running = True
        try:
            engine = WorkflowEngine(approval_manager, workflow_dict, payload, modules_base_path=MODULES_BASE)
            running_engines[engine.workflow_uid] = engine
            engine.run()
        finally:
            is_workflow_running = False
            running_engines.pop(engine.workflow_uid, None)

    threading.Thread(target=thread_runner, daemon=True).start()


@app.route("/api/sync/<target>", methods=["POST"])
def sync(target):
    global engine_paused, is_workflow_running
    if is_workflow_running:
        return jsonify({"status": "error", "message": "Workflows are currently running. Cannot sync now."}), 409

    if target not in ["modules", "workflows", "all"]:
        return jsonify({"status": "error", "message": f"Unsupported target '{target}'. Must be 'modules' or 'workflows'."}), 400

    try:
        logger.info(f"[SYNC] Starting sync for {target}...")
        engine_paused = True

        if target == "modules":
            poll_modules(poll_modules=True, poll_workflows=False)
        elif target == "workflows":
            poll_modules(poll_modules=False, poll_workflows=True)
        elif target == "all":
            poll_modules(poll_modules=True, poll_workflows=True)
        else:
            return jsonify({"status": "error", "message": f"Unsupported target '{target}'. Must be 'modules' or 'workflows'."}), 400

        logger.info(f"[SYNC] {target} sync completed successfully.")
        return jsonify({"status": "ok", "synced": target})

    except Exception as e:
        logger.error(f"[SYNC] Error during sync: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

    finally:
        engine_paused = False


@app.route("/api/system/status", methods=["GET"])
def system_status():
    global engine_paused, is_workflow_running
    status = {
        "engine_paused": engine_paused,
        "is_workflow_running": is_workflow_running
    }
    return jsonify(status)


def resume_pending_workflows():
    runs = discover_recoverable_runs()
    for run in runs:
        threading.Thread(
            target=resume_workflow_from_lifetime,
            args=(run, approval_manager),
            daemon=True
        ).start()


@app.route("/<module>/<uid>/<step_id>/submit", methods=["POST"])
def handle_module_submit(module, uid, step_id):
    data = request.get_json()
    payload = {
        "step_id": step_id,
        "form_data": data
    }
    approval_manager.resolve(uid, step_id, payload)
    approval_result_q.put(payload)
    return jsonify({"status": "submitted", "handler": module})

# Fully self-describing module structure
@app.route('/<module>/<uid>/<step_id>/<path:filename>')
def serve_module_file(module, uid, step_id, filename):
    SAFE_TEMPLATE_EXTENSIONS = [".html", ".js"]
    if filename.startswith('t.') and filename.endswith(tuple(SAFE_TEMPLATE_EXTENSIONS)):
        config_file = request.args.get("config_file")
        logger.debug(f"Serving template file: {filename} for module: {module}, uid: {uid}, step_id: {step_id}, config_file: {config_file}")
        # Serve a template file
        template_path = os.path.join(MODULES_BASE, module, filename)
        with open(template_path, 'r') as file:
            template = file.read()
        return render_template_string(template, uid=uid, step_id=step_id, module=module, config_file=str(config_file))

    module_dir = os.path.join(MODULES_BASE, module, 'build', 'dist')
    if not os.path.exists(module_dir):
        return jsonify({"error": "File not found"}), 404
    return send_from_directory(module_dir, filename)


def poller_controller():
    poll_required = config['app']['poll_for_modules_on_startup']
    if poll_required:
        logger.info("[WEB SERVER] Starting the Module dispatcher")
        threading.Thread(target=mock_md_server.start_server, daemon=True).start()
        logger.info("[WEB SERVER] waiting for dispatcher to become fully functional")
        time.sleep(3)
        logger.info("[WEB SERVER] Starting Flask server...")
        logger.info(f"[WEB SERVER] Repo base path: {MODULES_BASE}")
        logger.info(f"[WEB SERVER] Workflows base path: {WORKFLOWS_BASE}")
        # Ensure the directories exist
        poll_modules(poll_modules=True, poll_workflows=True)
        logger.info("[WEB SERVER] Polling completed.")
    else:
        logger.info("[WEB SERVER] Polling for modules on startup is disabled. Skipping module discovery.")


@app.route("/api/agent/<run_id>/pause", methods=["POST"])
def agent_pause(run_id):
    return _agent_control(run_id, {"type": "pause"})

@app.route("/api/agent/<run_id>/resume", methods=["POST"])
def agent_resume(run_id):
    return _agent_control(run_id, {"type": "resume"})

@app.route("/api/agent/<run_id>/cancel", methods=["POST"])
def agent_cancel(run_id):
    return _agent_control(run_id, {"type": "cancel"})

@app.route("/api/agent/<run_id>/skip/<step_id>", methods=["POST"])
def agent_skip(run_id, step_id):
    return _agent_control(run_id, {"type": "skip", "step_id": step_id})

@app.route("/api/agent/<run_id>/jump/<step_id>", methods=["POST"])
def agent_jump(run_id, step_id):
    return _agent_control(run_id, {"type": "jump", "step_id": step_id})

def _agent_control(run_id, command):
    access_key = request.headers.get("X-Access-Key")
    # Optionally check access_key against stored value here
    engine = running_engines.get(run_id)
    if not engine:
        return jsonify({"status": "error", "message": "Workflow not found or not running"}), 404
    engine.control_channel.send(command)
    return jsonify({"status": "ok", "command": command})


@app.route("/api/<repo>/<workflow>", methods=["PUT"])
def upload_workflow_yaml(repo, workflow):
    try:
        # Validate request body
        if not request.data:
            return jsonify({"status": "error", "message": "Empty request body"}), 400

        # Enforce .yaml extension
        if not workflow.endswith(".yaml"):
            workflow += ".yaml"

        # Sanitize inputs
        if ".." in repo or ".." in workflow:
            return jsonify({"status": "error", "message": "Invalid path"}), 400

        repo_dir = os.path.join(WORKFLOWS_BASE, repo)
        os.makedirs(repo_dir, exist_ok=True)
        wf_path = os.path.join(repo_dir, workflow)

        # Write uploaded YAML to file
        with open(wf_path, "wb") as f:
            f.write(request.data)

        logger.info(f"[UPLOAD] Workflow saved to: {wf_path}")

        # Validate with korectl (imported method)
        ok, msg = validate_workflow_from_file(wf_path, modules_dir=MODULES_BASE)
        if not ok:
            logger.warning(f"[LINT] Validation failed: {msg}")
            return jsonify({
                "status": "invalid",
                "message": msg
            }), 400

        logger.info(f"[LINT] Workflow '{workflow}' validated successfully")
        return jsonify({
            "status": "ok",
            "message": f"Workflow '{workflow}' uploaded and validated under repo '{repo}'"
        }), 201

    except Exception as e:
        logger.exception("[UPLOAD] Unexpected failure during upload or validation")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500


@app.route("/api/agent/<uid>/<step_id>/input", methods=["POST"])
def receive_aiagent_input(uid, step_id):
    data = request.get_json()

    if uid not in running_engines:
        return jsonify({"status": "error", "message": "Unknown or completed workflow"}), 404

    engine = running_engines[uid]
    ctx = engine.context

    shared = ctx.get("_aiagent_inputs", {})
    shared[step_id] = data
    ctx.set("_aiagent_inputs", shared)

    logger.info(f"[AIAGENT] Input received for {uid}/{step_id}: {data}")
    return jsonify({"status": "ok", "message": "Input accepted"})

@app.route("/api/agent/<uid>/status", methods=["GET"])
def agent_status(uid):
    access_key = request.headers.get("X-Access-Key")
    path = os.path.join(config["directories"]["lifetimes"], f"{uid}.yaml")
    if not os.path.exists(path):
        path = os.path.join(config["directories"]["lifetimes"], "completed", f"{uid}.yaml")
        if not os.path.exists(path):
            return jsonify({"error": "uid not found"}), 404

    with open(path, "r") as f:
        lifetime = yaml.safe_load(f)

    # Validate access key if AI agent
    if lifetime.get("workflow", {}).get("trigger", {}).get("type") == "aiagent":
        expected_key = lifetime.get("access_key")
        if not expected_key or expected_key != access_key:
            return jsonify({"error": "invalid access key"}), 403

    # Determine current status
    if lifetime.get("reason") != "completed":
        status = "in_progress"
    elif lifetime.get("context", {}).get("workflow_failed"):
        status = "failed"
    else:
        status = "completed"

    # Current step info
    current_step = lifetime.get("current_step")
    step_def = next(
        (s for s in lifetime.get("workflow", {}).get("steps", []) if s.get("id") == current_step),
        None
    )

    return jsonify({
        "uid": uid,
        "current_step": current_step,
        "current_step_type": step_def.get("type") if step_def else None,
        "context": lifetime.get("context", {}),
        "step_results": lifetime.get("context", {}).get("step_results", {}),
        "status": status
    })

@app.route("/api/resume/<uid>", methods=["POST"])
def resume_deferred_workflow(uid):
    path = os.path.join(config["directories"]["lifetimes"], f"{uid}.yaml")
    if not os.path.exists(path):
        return jsonify({"status": "error", "message": f"uid {uid} not found"}), 404

    with open(path, "r") as f:
        lifetime_map = yaml.safe_load(f)

    if "defer_until" not in lifetime_map:
        return jsonify({"status": "error", "message": "Not a deferred workflow"}), 400

    # Remove defer_until to avoid re-triggering
    lifetime_map.pop("defer_until", None)

    threading.Thread(
        target=resume_workflow_from_lifetime,
        args=(lifetime_map, approval_manager),
        daemon=True
    ).start()

    return jsonify({"status": "ok", "resumed": uid})

from engine.utils.defer_manager import run_defer_manager
run_defer_manager()


if __name__ == "__main__":
    # registering api routes for UI
    logger.info("[WEB SERVER] Registering API routes...")
    from commons.ui_socket import api
    app.register_blueprint(api)

    poller_controller()
    # Resume any pending workflows
    logger.info("[WEB SERVER] Resuming pending workflows...")
    resume_pending_workflows()
    logger.info("[WEB SERVER] Pending workflows resumed.")
    # Start the scheduler loop for scheduled triggers
    logger.info("[BOOT] Starting scheduler thread...")
    initialize_triggers(WORKFLOWS_BASE, approval_manager)
    threading.Thread(target=approval_listener, daemon=True).start()
    if os.getenv('ENV') == 'prod':
        serve(app, host='0.0.0.0', port=PORT)
    else:
        app.run(port=PORT, debug=False, host='0.0.0.0')
