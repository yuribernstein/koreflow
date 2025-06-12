# engine/utils/config_merge.py

def merge_module_config(global_config, step_config):
    """
    Recursively merges global module config and step-level override.
    Workflow step values take precedence.
    """
    if not global_config:
        return step_config or {}
    if not step_config:
        return global_config

    merged = global_config.copy()
    for key, value in step_config.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_module_config(merged[key], value)
        else:
            merged[key] = value
    return merged
