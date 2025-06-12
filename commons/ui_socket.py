# routes/api_routes.py

from flask import Blueprint, jsonify, request, send_file, abort
import os
import yaml
import json

from commons.get_config import get_config

config = get_config()
directories = config["directories"]

api = Blueprint("api", __name__, url_prefix="/api")


### ────── CONFIG ENDPOINTS ──────

@api.route("/config/global", methods=["GET"])
def get_global_config():
    return jsonify(config)

@api.route("/config/modules", methods=["GET"])
def list_modules():
    module_base = directories["modules"]
    try:
        return jsonify(sorted(os.listdir(module_base)))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route("/config/modules/<module_name>", methods=["GET"])
def get_module_config(module_name):
    path = os.path.join(directories["modules"], module_name, "module.yaml")
    if not os.path.exists(path):
        return abort(404)
    with open(path, "r") as f:
        return jsonify(yaml.safe_load(f))


### ────── LIFETIME ENDPOINTS ──────

@api.route("/lifetimes", methods=["GET"])
def get_active_lifetimes():
    response = []
    path = os.path.join(directories["lifetimes"])
    for file in os.listdir(path):
        if file.endswith(".yaml"):
            response.append(file.replace(".yaml", ""))
    return response

@api.route("/lifetimes/completed", methods=["GET"])
def get_completed_lifetimes():
    response = []
    path = os.path.join(directories["lifetimes"], "completed")
    for file in os.listdir(path):
        if file.endswith(".yaml"):
            response.append(file.replace(".yaml", ""))
    return response

@api.route("/lifetimes/<uid>", methods=["GET"])
def get_lifetime_by_uid(uid):
    full_path = os.path.join(directories["lifetimes"], f"{uid}.yaml")
    if os.path.exists(full_path):
        with open(full_path, "r") as f:
            return jsonify(yaml.safe_load(f))
    return abort(404)

@api.route("/lifetimes/completed/<uid>", methods=["GET"])
def get_completed_lifetime_by_uid(uid):
    full_path = os.path.join(directories["lifetimes"], "completed", f"{uid}.yaml")
    if os.path.exists(full_path):
        with open(full_path, "r") as f:
            return jsonify(yaml.safe_load(f))
    return abort(404)

### ────── MODULE ENDPOINTS ──────

@api.route("/modules", methods=["GET"])
def list_available_modules():
    module_base = directories["modules"]
    modules = [m for m in os.listdir(module_base) if os.path.isdir(os.path.join(module_base, m))]
    return jsonify(modules)

@api.route("/modules/readme", methods=["POST"])
def get_module_readme():
    data = request.json
    module_name = data.get("module")
    if not module_name:
        return abort(400)
    readme_path = os.path.join(directories["modules"], module_name, "readme.md")
    if not os.path.exists(readme_path):
        return abort(404)
    with open(readme_path, "r") as f:
        return jsonify({"readme": f.read()})

@api.route("/modules/<module_name>/manifest", methods=["GET"])
def get_module_manifest(module_name):
    path = os.path.join(directories["modules"], module_name, "module.yaml")
    if not os.path.exists(path):
        return abort(404)
    with open(path, "r") as f:
        return jsonify(yaml.safe_load(f))


### ────── WORKFLOWS ENDPOINTS ──────

@api.route("/workflows", methods=["GET"])
def list_workflow_dirs():
    base = directories["workflows"]
    result = {}
    for root, dirs, files in os.walk(base):
        rel = os.path.relpath(root, base)
        if rel == "." or any(ignored in rel for ignored in config["app"].get("ignored_workflow_dirs", [])):
            continue
        result[rel] = [f for f in files if f.endswith(".yaml")]
    return jsonify(result)

@api.route("/workflows/<path:dir>/<wf_name>", methods=["GET"])
def get_workflow_yaml(dir, wf_name):
    base = directories["workflows"]
    path = os.path.join(base, dir, wf_name)
    if not os.path.exists(path):
        return abort(404)
    with open(path, "r") as f:
        return jsonify(yaml.safe_load(f))


### ────── LOG ENDPOINTS ──────

@api.route("/logs/components", methods=["GET"])
def list_log_components():
    base = directories["logs"]
    try:
        files = sorted(os.listdir(base))
        return jsonify(files)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api.route("/logs/components/<component_name>", methods=["GET"])
def get_component_log(component_name):
    path = os.path.join(directories["logs"], component_name)
    if not os.path.exists(path):
        return abort(404)
    with open(path, "r") as f:
        return jsonify({"log": f.read()})
    

### ────── HELPER ──────

def _get_lifetime_runs(folder):
    if not os.path.exists(folder):
        return jsonify([])

    entries = []
    for file in os.listdir(folder):
        try:
            with open(os.path.join(folder, file), "r") as f:
                entries.append(yaml.safe_load(f))
        except Exception:
            continue
    return jsonify(entries)
