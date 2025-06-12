import time
from commons.logs import get_logger

logger = get_logger("aiagent_input")

class Aiagent_input:
    def __init__(self, context, **module_config):
        self.context = context
        self.config = module_config or {}

        self.uid = self.context.get("workflow_uid")
        self.step_id = self.context.get("current_step_id")
        self.shared_dict = self.context.get("_aiagent_inputs", {})

    def wait_for_input(self, expected_keys=None, timeout_seconds=900):
        logger.info(f"[AIAGENT] Waiting for agent input at {self.uid}/{self.step_id}...")

        start = time.time()
        while True:
            if self.step_id in self.shared_dict:
                input_data = self.shared_dict.pop(self.step_id)
                logger.info(f"[AIAGENT] Received input: {input_data}")
                self.context.set(f"ai_input_{self.step_id}", input_data)

                # Optional: unpack into context
                for k, v in input_data.items():
                    self.context.set(k, v)

                return {
                    "status": "received",
                    "data": input_data
                }

            if time.time() - start > timeout_seconds:
                raise TimeoutError(f"Timeout waiting for agent input at {self.uid}/{self.step_id}")
            time.sleep(1)
