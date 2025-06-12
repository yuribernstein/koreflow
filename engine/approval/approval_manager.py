# approval_manager.py

import threading
from commons.logs import get_logger

logger = get_logger("approval_manager")


class ApprovalManager:
    def __init__(self, approval_request_q, approval_result_q):
        self.approval_request_q = approval_request_q
        self.approval_result_q = approval_result_q
        self._events = {}  # key: (uid, step_id) → threading.Event
        self._results = {}  # key: (uid, step_id) → result dict
        self._lock = threading.Lock()
        logger.debug("ApprovalManager initialized")

    def start_listener(self):
        thread = threading.Thread(target=self._listen_for_results, daemon=True)
        thread.start()

    def request_approval(self, uid, step_id, message, timeout_minutes, approval_link, delivery_step=None, context_snapshot={}):
        logger.info(f"[APPROVAL] Registering approval {uid}/{step_id} with link {approval_link}")
        key = (uid, step_id)
        with self._lock:
            if key in self._events:
                logger.warning(f"[APPROVAL] Duplicate approval requested for {key}, overwriting event")
            event = threading.Event()
            self._events[key] = event

        # Inject approval_link into delivery_step input if needed
        if delivery_step and 'input' in delivery_step:
            for k, v in delivery_step['input'].items():
                if isinstance(v, str) and "{{ context.approval_link }}" in v:
                    delivery_step['input'][k] = v.replace("{{ context.approval_link }}", approval_link)

        self.approval_request_q.put({
            "action": "register",
            "uid": uid,
            "step_id": step_id,
            "timeout_minutes": timeout_minutes,
            "message": message,
            "approval_link": approval_link,
            "delivery_step": delivery_step,
            "context_snapshot": context_snapshot or {}
        })

        return event


    def wait_for_approval(self, uid, step_id, timeout_seconds=36000):
        key = (uid, step_id)
        logger.info(f"[APPROVAL] Blocking for approval {key}")
        event = self._events.get(key)
        if not event:
            raise RuntimeError(f"No approval event registered for {key}")

        event.wait(timeout=timeout_seconds)
        with self._lock:
            result = self._results.pop(key, {"status": "timeout"})
            if key in self._events:
                del self._events[key]
        logger.info(f"[APPROVAL] Approval result for {key} → {result}")
        return result

    def resolve(self, uid, step_id, status):
        logger.info(f"resolve is called with uid={uid}, step_id={step_id}, status={status}")
        key = (uid, step_id)
        with self._lock:
            event = self._events.get(key)
            if event:
                self._results[key] = {"status": status}
                event.set()
                logger.info(f"[APPROVAL] Resolved approval for {key} with status={status}")
            else:
                logger.warning(f"[APPROVAL] No pending event found for {key}")

    def _listen_for_results(self):
        while True:
            result = self.approval_result_q.get()
            self.resolve(result["uid"], result["step_id"], result["status"])
