from collections import OrderedDict


class ReplayCache:
    __slots__ = ("cache", "capacity")

    def __init__(self, capacity=3000):
        self.cache = OrderedDict()
        self.capacity = capacity

    @staticmethod
    def _generate_key(params):
        return frozenset(params.items())

    def get(self, params):
        key = self._generate_key(params)
        if key in self.cache:
            self.cache.move_to_end(key)
            return self.cache[key]
        return

    def set(self, params, data):
        key = self._generate_key(params)
        self.cache[key] = data
        self.cache.move_to_end(key)
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

    def clear(self):
        self.cache.clear()


cache = ReplayCache()
