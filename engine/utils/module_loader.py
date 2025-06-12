# module_loader.py
import importlib.util
import os
from commons.get_config import get_config
from commons.logs import get_logger
logger = get_logger(__name__)

config = get_config()
MODULES_BASE = config["directories"]["modules"]

def load_class(module_name, class_name):
    logger.debug(f"Loading class {class_name} from module {module_name}")
    # Check if the module exists
    try:
        mod_path = os.path.join(MODULES_BASE, module_name, f"{class_name.lower()}.py")
        spec = importlib.util.spec_from_file_location(class_name, mod_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        cls = getattr(mod, class_name)
        return cls
    except FileNotFoundError:
        logger.error(f"Module {mod_path} not found.")
        raise
    except AttributeError:
        logger.error(f"Class {class_name} not found in module {mod_path}.")
        raise
    except Exception as e:
        logger.error(f"Error loading class {class_name} from module {mod_path}: {e}")
        raise
    finally:
        logger.debug(f"Class {class_name} loaded successfully from module {module_name}")
