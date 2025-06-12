import os
import yaml
from commons.logs import get_logger
from commons.get_config import get_config

logger = get_logger(__name__)
config = get_config()

class Preflight:
    def __init__(self, context):
        self.context = context
        self.modules_subpath = config["directories"]["modules"]
        logger.info(f"Preflight initialized with modules subpath: {self.modules_subpath}")

    def validate_manifest(self, module_name):
        module_path = os.path.join(self.modules_subpath, module_name)
        manifest_path = os.path.join(module_path, "module.yaml")
        
        if not os.path.exists(manifest_path):
            return {"valid": False, "error": f"module.yaml not found in {module_path}"}

        try:
            with open(manifest_path, "r") as f:
                manifest = yaml.safe_load(f)
        except Exception as e:
            return {"valid": False, "error": f"Failed to parse YAML: {str(e)}"}

        required_fields = ["name", "class", "methods"]
        for field in required_fields:
            if field not in manifest:
                return {"valid": False, "error": f"Missing required field: '{field}'"}

        if not isinstance(manifest["methods"], list):
            return {"valid": False, "error": "Expected 'methods' to be a list"}

        for method in manifest["methods"]:
            if "name" not in method:
                return {"valid": False, "error": "Method missing 'name' field"}
            if "arguments" in method and not isinstance(method["arguments"], list):
                return {"valid": False, "error": f"Arguments for method '{method['name']}' should be a list"}
            if "arguments" in method:
                for arg in method["arguments"]:
                    if "name" not in arg or "type" not in arg:
                        return {"valid": False, "error": f"Each argument in method '{method['name']}' must have 'name' and 'type'"}

        return {"valid": True, "module": manifest.get("name")}
