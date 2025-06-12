from commons.logs import get_logger

logger = get_logger("logger_module")

class Logger:
    def __init__(self, context, **module_config):
        self.context = context
        self.config = module_config or {}

    def run(self, message):
        rendered = str(message)
        logger.info(f"[LOGGER] {rendered}")
        return {
            "status": "ok",
            "message": rendered
        }
