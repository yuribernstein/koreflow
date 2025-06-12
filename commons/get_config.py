import yaml
from pathlib import Path
import sys
import os

def get_config():
    # Always resolves to the folder where the binary is launched from
    runtime_base = Path(os.getcwd())
    config_path = runtime_base / "configuration/config.yaml"

    if not config_path.exists():
        print(f"[ERROR] Missing config file: {config_path}")
        sys.exit(1)

    with open(config_path, 'r') as f:
        _config_cache = yaml.safe_load(f)

    return _config_cache
