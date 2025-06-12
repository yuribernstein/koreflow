# context_manager.py

class ContextManager:
    def __init__(self):
        self._context = {}

    def set(self, key, value):
        self._context[key] = value

    def get(self, key, default=None):
        return self._context.get(key, default)

    def get_all(self):
        return self._context

    def update(self, new_data: dict):
        self._context.update(new_data)

    def __contains__(self, key):
        return key in self._context

    def __getitem__(self, key):
        return self._context[key]

    def __setitem__(self, key, value):
        self._context[key] = value
