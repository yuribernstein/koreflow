# match_engine.py

import ast
from jinja2 import Template

from commons.logs import get_logger
logger = get_logger(__name__)


def extract_json_path(data, path):
    logger.debug(f"extract_json_path: path={path}")
    logger.debug(f"extract_json_path: data={data}")
    """Supports dot notation and wildcard access like payload.labels[*].name"""
    try:
        parts = path.split(".")
        for part in parts:
            if "[" in part and part.endswith("]"):
                key = part.split("[")[0]
                data = data.get(key, [])
                if "*" in part:
                    # Flatten and simplify wildcard for now
                    if isinstance(data, list):
                        data = [item for item in data if item]
            else:
                data = data.get(part)
        return data
    except Exception as e:
        logger.debug(f"extract_json_path failed on path={path}: {e}")
        return None

def evaluate_operator(operator, actual, expected):
    try:
        if operator == "equals":
            return actual == expected
        elif operator == "not_equals":
            return actual != expected
        elif operator == "present":
            return actual is not None
        elif operator == "absent":
            return actual is None
        elif operator == "is_in":
            return actual in expected
        elif operator == "not_in":
            return actual not in expected
        elif operator == "contains":
            return expected in actual if isinstance(actual, str) else False
        elif operator == "not_contains":
            return expected not in actual if isinstance(actual, str) else False
        elif operator == "starts_with":
            return actual.startswith(expected) if isinstance(actual, str) else False
        elif operator == "length":
            return len(actual) == expected if isinstance(actual, (list, str)) else False
        else:
            raise ValueError(f"Unsupported operator: {operator}")
    except Exception as e:
        logger.debug(f"evaluate_operator failed for op={operator}: {e}")
        return False

def safe_eval_logic_expr(expr: str) -> bool:
    try:
        tree = ast.parse(expr, mode="eval")
        allowed_nodes = (
            ast.Expression, ast.BoolOp, ast.UnaryOp, ast.NameConstant,
            ast.Name, ast.Load, ast.And, ast.Or, ast.Not, ast.Compare,
            ast.Eq, ast.NotEq, ast.Call, ast.Constant
        )

        for node in ast.walk(tree):
            if not isinstance(node, allowed_nodes):
                raise ValueError(f"Unsafe logic expression: {expr}")

        return eval(compile(tree, filename="<string>", mode="eval"))
    except Exception as e:
        logger.error(f"Failed to evaluate match condition logic: {e}")
        return False

def match(workflow_dict, payload, debug=False):
    try:
        wf_meta = workflow_dict.get("workflow", {})
        
        # ✅ Skip match checks for ad-hoc
        if wf_meta.get("trigger", {}).get("type") in ["ad-hoc", "aiagent"]:
            if debug:
                logger.info("[MATCH] Skipping match checks for ad-hoc workflow")
            return True

        match_block = wf_meta.get("match", {})
        logic = match_block.get("condition_logic")
        conditions = match_block.get("conditions", [])

        if not logic or not conditions:
            return False

        condition_results = {}
        for cond in conditions:
            cid = cond["id"]
            actual = extract_json_path(payload, cond["path"])
            op = cond["operator"]
            expected = cond.get("value")

            result = evaluate_operator(op, actual, expected)
            condition_results[cid] = result

            if debug:
                logger.info(f"[MATCH] {cid}: path={cond['path']} actual={actual}, op={op}, expected={expected} → {result}")

        # Build and safely evaluate expression
        logic_expr = logic
        for cid, result in condition_results.items():
            logic_expr = logic_expr.replace(cid, str(result))

        if debug:
            logger.info(f"[MATCH LOGIC] {logic} → {logic_expr}")

        return safe_eval_logic_expr(logic_expr)

    except Exception as e:
        logger.error(f"match() failed: {e}")
        return False

