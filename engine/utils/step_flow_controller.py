# step_fllow_controller.py

from jinja2 import Template
from engine.utils.match_engine import evaluate_operator, extract_json_path, safe_eval_logic_expr
from commons.logs import get_logger
logger = get_logger(__name__)


class StepFlowController:
    def __init__(self, workflow_dict, context):
        logger.debug(f"[SFC] Initializing StepFlowController with workflow_dict: {workflow_dict}")
        self.workflow = workflow_dict
        self.context = context
        self.steps = {step["id"]: step for step in self.workflow.get("steps", [])}
        self.execution_log = {}  # Tracks outputs and statuses


    def should_run_step(self, step_id):
        step = self.steps.get(step_id)
        if not step:
            raise ValueError(f"Step '{step_id}' not found")

        terms_block = step.get("terms")

        # No terms defined → default to True
        if not terms_block:
            return True

        # Structured terms: expect 'rules' and 'logic'
        if isinstance(terms_block, dict) and "rules" in terms_block and "logic" in terms_block:
            rules = terms_block.get("rules", [])
            logic = terms_block.get("logic", "")

            if not rules or not logic:
                return True

            rule_results = {}

            for rule in rules:
                rid = rule["id"]
                path = rule["path"]
                operator = rule["operator"]
                expected = rule.get("value")

                actual = extract_json_path(
                    {"context": self.context.get_all(), "step_results": self.execution_log},
                    path
                )
                result = evaluate_operator(operator, actual, expected)
                rule_results[rid] = result

            # Replace ids with True/False in logic string
            logic_expr = logic
            for rid, val in rule_results.items():
                logic_expr = logic_expr.replace(rid, str(val))

            return safe_eval_logic_expr(logic_expr)

        # Fallback: no terms/rules
        return True



    def register_step_result(self, step_id, result):
        logger.info(f"[SFC] Step '{step_id}' result registered: {result}")
        self.execution_log[step_id] = result
        # Set under context.step_results.<step_id>
        all_results = self.context.get("step_results", {})
        all_results[step_id] = result
        self.context.set("step_results", all_results)


    def get_next_step(self, current_step_id):
        keys = list(self.steps.keys())
        try:
            current_index = keys.index(current_step_id)
            next_step = keys[current_index + 1] if current_index + 1 < len(keys) else None
            logger.info(f"[SFC] Next step after '{current_step_id}' is '{next_step}'")
            return next_step
        except ValueError:
            logger.error(f"[SFC] Current step '{current_step_id}' not found in steps")
            return None


    def get_step(self, step_id):
        return self.steps.get(step_id)
