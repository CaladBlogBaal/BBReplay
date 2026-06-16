import time
from collections import OrderedDict


class ReplayCache:
    __slots__ = ("cache", "capacity", "ttl")

    def __init__(self, capacity=3000, ttl=60):
        self.cache = OrderedDict()
        self.capacity = capacity
        self.ttl = ttl

    @staticmethod
    def _generate_key(params):
        return frozenset(params.items())

    def get(self, params):
        key = self._generate_key(params)
        if key in self.cache:
            expires_at, value = self.cache[key]
            if time.monotonic() > expires_at:
                del self.cache[key]
                return

            self.cache.move_to_end(key)
            return value
        return

    def set(self, params, data):
        key = self._generate_key(params)
        self.cache[key] = (float("inf") if self.ttl is None else time.monotonic() + self.ttl, data)
        self.cache.move_to_end(key)
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

    def clear(self):
        self.cache.clear()


cache = ReplayCache()
