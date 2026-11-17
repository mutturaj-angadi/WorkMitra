from collections import OrderedDict
from threading import Lock
from time import monotonic


class TTLCache:
    def __init__(self, max_items=256, ttl_seconds=30):
        self.max_items = max_items
        self.ttl = ttl_seconds
        self.data = OrderedDict()
        self.lock = Lock()

    def get(self, key):
        with self.lock:
            value = self.data.get(key)
            if not value:
                return None
            expires, payload = value
            if expires < monotonic():
                self.data.pop(key, None)
                return None
            self.data.move_to_end(key)
            return payload

    def set(self, key, value):
        with self.lock:
            self.data[key] = (monotonic() + self.ttl, value)
            self.data.move_to_end(key)
            while len(self.data) > self.max_items:
                self.data.popitem(last=False)


class CircuitBreaker:
    def __init__(self, threshold=3, reset_seconds=20):
        self.threshold = threshold
        self.reset = reset_seconds
        self.failures = 0
        self.opened_at = None

    @property
    def is_open(self):
        if self.opened_at is None:
            return False
        if monotonic() - self.opened_at >= self.reset:
            self.opened_at = None
            self.failures = 0
            return False
        return True

    def success(self):
        self.failures = 0
        self.opened_at = None

    def failure(self):
        self.failures += 1
        if self.failures >= self.threshold:
            self.opened_at = monotonic()
