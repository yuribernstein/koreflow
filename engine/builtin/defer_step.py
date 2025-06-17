# engine/builtin/defer_step.py

from datetime import datetime, timedelta
from dateutil import parser as dtparser

def resolve_defer_time(step_def, context):
    if "time" in step_def:
        ts_raw = context.render(step_def["time"])
        return dtparser.parse(ts_raw)
    elif "minutes_from_now" in step_def:
        minutes = int(context.render(step_def["minutes_from_now"]))
        return datetime.utcnow() + timedelta(minutes=minutes)
    else:
        raise ValueError("Defer step must include 'time' or 'minutes_from_now'")
