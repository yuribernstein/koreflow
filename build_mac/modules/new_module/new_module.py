class New_module:
    def __init__(self, context, **module_config):
        self.context = context
        self.config = module_config or {}

    def run(self, param1, param2=None):
        return {
            "status": "ok",
            "message": "Echoing input",
            "data": {"param1": param1, "param2": param2}
        }
