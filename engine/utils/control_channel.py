from queue import Queue, Empty

class WorkflowControlChannel:
    def __init__(self):
        self.queue = Queue()
        self.status = {
            "paused": False,
            "cancelled": False,
            "skip": [],
            "jump_to": None,
        }

    def send(self, command: dict):
        self.queue.put(command)

    def fetch_and_apply(self):
        while True:
            try:
                cmd = self.queue.get_nowait()
                self._apply(cmd)
            except Empty:
                break

    def _apply(self, cmd):
        ctype = cmd.get("type")
        if ctype == "pause":
            self.status["paused"] = True
        elif ctype == "resume":
            self.status["paused"] = False
        elif ctype == "cancel":
            self.status["cancelled"] = True
        elif ctype == "skip":
            self.status["skip"].append(cmd["step_id"])
        elif ctype == "jump":
            self.status["jump_to"] = cmd["step_id"]
