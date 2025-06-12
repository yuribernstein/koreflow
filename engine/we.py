# we.py

import importlib.util
import os
import sys
import inspect
import uuid
from jinja2 import Template, Environment
from time import time
from datetime import datetime
import yaml
from engine.utils.context_manager import ContextManager
from engine.utils.step_flow_controller import StepFlowController
from engine.utils.preflight_module.preflight import Preflight
from engine.state.lifetime_manager import lifetime_manager
from engine.utils.config_merge import merge_module_config
from commons.logs import get_logger
logger = get_logger("workflow_engine")

from commons.get_config import get_config
config = get_config()

logger.debug(f"[DEBUG] Workflow Engine initialized with config: {config}")
REPO_BASE = config["directories"]["modules"]
WORKFLOWS_BASE = config["directories"]["workflows"]
BASE_URL = config["app"]["base_url"]

# Add the repo base path to sys.path if not already present
if REPO_BASE not in sys.path:
    sys.path.insert(0, REPO_BASE)
    
logger.info(f"[DEBUG] Added {REPO_BASE} to sys.path")

class WorkflowEngine:
    def __init__(self, approval_manager, workflow_dict, payload, modules_base_path=REPO_BASE, skip_payload_parse=False, injected_context=None):
        self.approval_manager = approval_manager
        from engine.utils.control_channel import WorkflowControlChannel
        self.control_channel = WorkflowControlChannel()
        self.workflow = workflow_dict["workflow"]
        self.payload = payload
        self.modules_base_path = modules_base_path
        
        self.context = ContextManager()
        self.context.set("step_results", {})
        self.context.set("workflow_failed", False)
        self.context.set("failed_step_id", None)
        self.context.set("failed_reason", None)
        self.module_cache = {}

        self.workflow_uid = workflow_dict.get("uid", str(uuid.uuid4()))
        self.lifetime_map = {
            "uid": self.workflow_uid,
            "workflow": self.workflow,
            "current_step": None,
            "context": {},
            "started_at": datetime.utcnow().isoformat()
        }

        # Inject access_key if present
        if "access_key" in workflow_dict:
            self.lifetime_map["access_key"] = workflow_dict["access_key"]

        if injected_context:
            self.context.update(injected_context)  # Injected from lifetime

        self._load_context_variables()
        if not skip_payload_parse:
            self._parse_payload()
        self._validate_modules()

        self.controller = StepFlowController(self.workflow, self.context)
        self._load_context_modules()

        self._persist_lifetime("initialized")

        
    def _load_context_modules(self):
        self.context_modules = {}
        for name, cfg in self.workflow.get("context_modules", {}).items():
            module_path = cfg["module"]
            module_name, class_name = module_path.split(".")
            cls = self._load_module(module_name, class_name)
            rendered_cfg = self._render_input({k: v for k, v in cfg.items() if k != "module"})
            instance = cls(self.context, **rendered_cfg)
            self.context_modules[name] = instance
            logger.debug(f"[CTX-MOD] Rendering context module '{name}' with: {rendered_cfg}")



    def _load_context_variables(self):
        for var in self.workflow.get("context_variables", []):
            name = var["name"]
            value = var.get("default")
            self.context.set(name, value)

    def _parse_payload(self):
        for parser in self.workflow.get("payload_parser", []):
            path = parser["path"]
            var_name = parser["var"]
            absent_action = parser.get("absent_action", "fail")

            try:
                parts = path.split(".")
                data = self.payload
                for part in parts:
                    if part.endswith("]"):
                        key = part[:-1].split("[")[0]
                        data = data[key]
                    else:
                        data = data[part]
                self.context.set(var_name, data)
            except KeyError:
                if absent_action == "fail":
                    raise ValueError(f"Path '{path}' not found in payload for var '{var_name}'")
                else:
                    continue

    def _validate_modules(self):
        preflight = Preflight(self.context.get_all())
        for step in self.workflow.get("steps", []):
            action = step.get("action")
            if not action or action.startswith("context."):
                continue  # skip context modules
            raw_module = action.split(".")[0]
            if "/" in raw_module:
                raise ValueError(f"Invalid module name '{raw_module}' — must not contain slashes")
            module_path = os.path.join(self.modules_base_path, raw_module)
            result = preflight.validate_manifest(module_path)
            if not result.get("valid"):
                raise ValueError(f"Preflight validation failed for module '{raw_module}': {result.get('error')}")

    def run(self):
        try:
            logger.info(f"[WF] Workflow {self.workflow_uid} started: {self.workflow.get('name')}")

            if not self.controller.steps:
                raise RuntimeError(f"No steps defined in workflow '{self.workflow_uid}'")

            step_id = self.lifetime_map.get("current_step") or list(self.controller.steps.keys())[0]
        
            try:
                while step_id:
                    self.control_channel.fetch_and_apply()

                    if self.control_channel.status["cancelled"]:
                        logger.warning(f"[CONTROL] Workflow {self.workflow_uid} was cancelled.")
                        break

                    if self.control_channel.status["paused"]:
                        logger.info(f"[CONTROL] Workflow {self.workflow_uid} paused.")
                        time.sleep(1)
                        continue

                    if step_id in self.control_channel.status["skip"]:
                        logger.info(f"[CONTROL] Skipping step {step_id}")
                        step_id = self.controller.get_next_step(step_id)
                        continue

                    if self.control_channel.status["jump_to"]:
                        jump_to = self.control_channel.status["jump_to"]
                        if jump_to in self.controller.steps:
                            logger.info(f"[CONTROL] Jumping to step {jump_to}")
                            step_id = jump_to
                            self.control_channel.status["jump_to"] = None
                        else:
                            logger.warning(f"[CONTROL] jump_to target {jump_to} not found")
                            break
                        continue                    
                    self.lifetime_map["current_step"] = step_id
                    self._persist_lifetime("step_start")

                    step = self.controller.get_step(step_id)

                    if self.controller.should_run_step(step_id):
                        try:
                            result = self._run_step(step)

                        except Exception as e:
                            logger.error(f"[WF] Step {step['id']} failed: {e}")
                            self.context.set("workflow_failed", True)
                            step_id = None
                            break

                        self.controller.register_step_result(step_id, result)

                        # Only if no exception: move to next
                        next_step_id = self.controller.get_next_step(step_id)
                        logger.info(f"[DEBUG] Completed step {step['id']} → next → {next_step_id}")
                        step_id = next_step_id

                    else:
                        # If step shouldn't run, just go to next
                        next_step_id = self.controller.get_next_step(step_id)
                        logger.info(f"[DEBUG] Skipped step {step['id']} → next → {next_step_id}")
                        step_id = next_step_id

            finally:
                if self.context.get("workflow_failed"):
                    global_handler = self.workflow.get("global_failure_handler")
                    if global_handler:
                        logger.info("[WF FAIL] Running global_failure_handler")
                        try:
                            if isinstance(global_handler, list):
                                for handler_step_id in global_handler:
                                    step_def = self.controller.get_step(handler_step_id)
                                    self._run_inline_step(step_def)
                            elif isinstance(global_handler, dict):
                                self._run_inline_step(global_handler)
                            else:
                                logger.warning("[WF FAIL] global_failure_handler has invalid format")
                        except Exception as e:
                            logger.exception("[WF FAIL] Global failure handler failed")

                self._persist_lifetime("completed")
                lifetime_manager.mark_complete(self.workflow_uid)
                # self._archive_completed_workflow()

                if self.context.get("workflow_failed"):
                    self.lifetime_map["failure"] = {
                        "step_id": self.context.get("failed_step_id"),
                        "reason": self.context.get("failed_reason")
                    }
                    logger.info(f"[WF] Workflow {self.workflow_uid} completed WITH FAILURE.")
                else:
                    logger.info(f"[WF] Workflow {self.workflow_uid} completed SUCCESSFULLY.")
        
        except Exception as e:
            logger.exception(f"[WF] Workflow {self.workflow_uid} crashed during run(): {e}")

    def _run_inline_step(self, step_dict):
        logger.info(f"[INLINE STEP] Running {step_dict['id']}")

        if step_dict["type"] != "action":
            raise ValueError("Only 'action' steps are allowed as inline handlers.")

        action = step_dict["action"]
        input_data = self._render_input(step_dict.get("input", {}))

        if action.startswith("context."):
            parts = action.split(".")
            module_name = parts[1]
            method_name = parts[2]
            instance = self.context_modules[module_name]

            global_cfg = config.get("module_defaults", {}).get(module_name, {})
            final_input = merge_module_config(global_cfg, input_data)
        else:
            module_name, class_name, method_name = action.split(".")
            global_cfg = config.get("module_defaults", {}).get(module_name, {})
            merged_input = merge_module_config(global_cfg, input_data)

            cls = self._load_module(module_name, class_name)
            instance = cls(self.context, **merged_input)
            final_input = merged_input

        logger.debug(f"[INLINE STEP] Calling {action} with: {final_input}")
        method = getattr(instance, method_name)
        return method(**final_input)



    def _run_step(self, step):
        try:
            if step["type"] == "action":
                return self._run_action_step(step)
            elif step["type"] == "webform":
                return self._run_webform_step(step)
            elif step["type"] == "approval":
                return self._run_approval_step(step)
            else:
                raise ValueError(f"Unsupported step type: {step['type']}")
        except Exception as e:
            logger.error(f"[STEP FAIL] Step {step['id']} failed: {e}")
            self.context.set("workflow_failed", True)
            self.context.set("failed_step_id", step["id"])
            self.context.set("failed_reason", str(e))

            if step.get("step_failure_handler"):
                logger.info(f"[STEP FAIL] Running step_failure_handler for {step['id']}")
                self._run_inline_step(step["step_failure_handler"])

            raise


    def _run_webform_step(self, step):
        step_id = step["id"]
        timeout = min(int(step.get("timeout_minutes", 30)), 1440)
        module = step["module"]
        config_file = step.get("config_file", "configs/reference_config.js")
        css_file = step.get("css_file", "custom.css")

        approval_link = f"{BASE_URL}/{module}/{self.workflow_uid}/{step_id}/t.webform.html?config_file={config_file}"

        self.context.set("approval_link", approval_link)
        self.context.set("webform_config_file", config_file)
        self.context.set("webform_css_file", css_file)

        # Prepare the event **before** sending delivery
        future = self.approval_manager.request_approval(
            uid=self.workflow_uid,
            step_id=step_id,
            message=step.get("message", f"Form approval required for {step_id}"),
            timeout_minutes=timeout,
            approval_link=approval_link
        )

        self._persist_lifetime("pre_delivery_context_snapshot")

        # Now run delivery_step if needed
        delivery = step.get("delivery_step")
        if delivery:
            logger.info(f"[WEBFORM] Running delivery step for approval {step_id}")
            self._run_action_step(delivery)

        logger.info(f"[WEBFORM] Waiting for approval {self.workflow_uid}/{step_id}...")

        # Blocking here until user approves or times out
        result = self.approval_manager.wait_for_approval(self.workflow_uid, step_id)

        if step.get("register_output"):
            self.context.set(step["register_output"], result)
            self._persist_lifetime("register_output")

        self.context.set(f"webform_{step_id}_data", result.get("form_data", {}))
        self._persist_lifetime("webform_result")

        return result


    def _wait_for_context_keys(self, keys, timeout_sec=5):
        import time
        start = time.time()
        while True:
            missing = [k for k in keys if k not in self.context.get_all()]
            if not missing:
                return
            if time.time() - start > timeout_sec:
                raise TimeoutError(f"Timed out waiting for context keys: {missing}")
            time.sleep(0.1)
        logger.info(f"[WF] Waited {round(time.time() - start, 2)}s for context keys: {keys}")



    def _get_missing_context_keys(self, input_dict):
        from jinja2 import meta

        env = Environment()
        missing = []
        context_keys = self.context.get_all().keys()

        for val in input_dict.values():
            if isinstance(val, str):
                ast = env.parse(val)
                variables = meta.find_undeclared_variables(ast)
                for v in variables:
                    if v not in context_keys:
                        missing.append(v)
        return list(set(missing))




    def _run_action_step(self, step):
        action = step["action"]
        input_data = self._render_input(step.get("input", {}))

        # Wait until all context variables in the input are available
        missing_keys = self._get_missing_context_keys(input_data)
        if missing_keys:
            logger.info(f"[WF] Waiting for context keys before running step {step['id']}: {missing_keys}")
            self._wait_for_context_keys(missing_keys)

        if action.startswith("context."):
            parts = action.split(".")
            module_name = parts[1]
            method_name = parts[2]
            instance = self.context_modules[module_name]
            merged_input = input_data
        else:
            module_name, class_name, method_name = action.split(".")
            global_cfg = config.get("module_defaults", {}).get(module_name, {})
            step_cfg = input_data
            merged_input = merge_module_config(global_cfg, step_cfg)

            cls = self._load_module(module_name, class_name)
            instance = cls(self.context, **merged_input)

        method = getattr(instance, method_name)

        # Filter input args for the method signature
        from inspect import signature
        sig = signature(method)
        accepted_args = set(sig.parameters.keys())
        safe_input = {k: v for k, v in merged_input.items() if k in accepted_args}

        logger.debug(f"[STEP] Executing {action} with args: {safe_input}")
        result = self._maybe_async(method)(**safe_input)

        if isinstance(result, dict) and result.get("status") == "fail":
            logger.error(f"[STEP FAIL] Module returned failure status at step {step['id']}: {result.get('message')}")
            self.context.set("workflow_failed", True)
            self.context.set("failed_step_id", step["id"])
            self.context.set("failed_reason", result.get("message", "Module reported failure."))
            raise Exception(f"Step '{step['id']}' failed according to module result: {result.get('message')}")

        if step.get("register_output"):
            self.context.set(step["register_output"], result)
            self._persist_lifetime("register_output")

        for var in step.get("register_vars", []):
            self._register_variable(var)

        return result




    def _run_approval_step(self, step):
        step_id = step["id"]
        timeout = min(int(step.get("timeout_minutes", 30)), 1440)
        message = step.get("message", "Approval required")

        # Generate approval link
        approval_link = f"{BASE_URL}/api/approve/{self.workflow_uid}/{step_id}"
        self.context.set("approval_link", approval_link)

        # Run delivery_step first (optional)
        delivery = step.get("delivery_step")
        if delivery:
            self._run_action_step(delivery)

        # Send to Flask
        future = self.approval_manager.request_approval(
            uid=self.workflow_uid,
            step_id=step_id,
            message=message,
            timeout_minutes=timeout,
            approval_link=approval_link,
            delivery_step=step.get("delivery_step"),
            context_snapshot=self.context.get_all()
        )

        result = self.approval_manager.wait_for_approval(self.workflow_uid, step_id)
        self._persist_lifetime("approval_result")
        self.controller.register_step_result(step_id, result)

        logger.info(f"[WF] Approval step '{step_id}' completed with result: {result}")

        return result

    def _register_variable(self, var):
        name = var["name"]
        absent_action = var.get("absent_action", "fail")

        if "value" in var:
            try:
                val = Template(var["value"]).render(context=self.context.get_all())
                self.context.set(name, val)
            except Exception as e:
                if absent_action == "fail":
                    raise ValueError(f"Failed to render value for var '{name}': {e}")
        elif "conditional" in var:
            for case in var["conditional"]:
                try:
                    if "if" in case and eval(Template(case["if"]).render(context=self.context.get_all())):
                        self.context.set(name, case["value"])
                        return
                    elif "elif" in case and eval(Template(case["elif"]).render(context=self.context.get_all())):
                        self.context.set(name, case["value"])
                        return
                except Exception as e:
                    if absent_action == "fail":
                        raise ValueError(f"Error in conditional for var '{name}': {e}")
            default = next((c["default"] for c in var["conditional"] if "default" in c), None)
            if default:
                self.context.set(name, default)
            elif absent_action == "fail":
                raise ValueError(f"No condition matched and no default for variable '{name}'")

        self._persist_lifetime("register_var")

    def _render_input(self, input_dict):
        rendered = {}
        for k, v in input_dict.items():
            if isinstance(v, str):
                rendered[k] = Template(v).render(context=self.context.get_all())
            elif isinstance(v, list):
                rendered[k] = [Template(str(item)).render(context=self.context.get_all()) for item in v]
            else:
                rendered[k] = v
        return rendered

    def _load_module(self, module_name, class_name):
        mod_path = os.path.join(self.modules_base_path, module_name, f"{class_name.lower()}.py")
        spec = importlib.util.spec_from_file_location(class_name, mod_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        cls = getattr(mod, class_name)
        return cls  # Return the class, not instance


    def _maybe_async(self, func):
        if inspect.iscoroutinefunction(func):
            return func
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper

    def _persist_lifetime(self, reason=None):
        self.lifetime_map["context"] = self.context.get_all()
        self.lifetime_map["last_updated"] = datetime.utcnow().isoformat()
        self.lifetime_map["reason"] = reason
        lifetime_manager.update(self.workflow_uid, self.lifetime_map)


    def rehydrate_pending_approval(self, step_id):
        step = self.controller.get_step(step_id)
        if not step or step["type"] not in ["approval", "webform"]:
            logger.info(f"[RECOVERY] Step '{step_id}' is not an approval/webform step, skipping rehydration.")
            return

        logger.info(f"[RECOVERY] Rehydrating approval step: {step_id}")
        timeout = min(int(step.get("timeout_minutes", 30)), 1440)

        if step["type"] == "approval":
            approval_link = f"{BASE_URL}/api/approve/{self.workflow_uid}/{step_id}"
        elif step["type"] == "webform":
            module = step.get("module")
            config_file = step.get("config_file", "configs/reference_config.js")
            approval_link = f"{BASE_URL}/{module}/{self.workflow_uid}/{step_id}/t.webform.html?config_file={config_file}"
        else:
            raise Exception(f"Unknown step type for rehydration: {step['type']}")

        # Set in context for future access
        self.context.set("approval_link", approval_link)

        # Re-register approval
        self.approval_manager.request_approval(
            uid=self.workflow_uid,
            step_id=step_id,
            message=f"Recovered approval: {step_id}",
            timeout_minutes=timeout,
            approval_link=approval_link,
            context_snapshot=self.context.get_all()
        )

        logger.info(f"[RECOVERY] Approval route re-registered for {self.workflow_uid}/{step_id}")


    def _archive_completed_workflow(self):
        completed_dir = os.path.join(config["directories"]["lifetimes"], "completed")
        os.makedirs(completed_dir, exist_ok=True)

        src_path = os.path.join(config["directories"]["lifetimes"], f"{self.workflow_uid}.yaml")
        dst_path = os.path.join(completed_dir, f"{self.workflow_uid}.yaml")

        try:
            if os.path.exists(src_path):
                os.rename(src_path, dst_path)
                logger.info(f"[WF] Archived completed workflow to: {dst_path}")
            else:
                logger.warning(f"[WF] Could not archive: source not found {src_path}")
        except Exception as e:
            logger.error(f"[WF] Archiving failed: {e}")

