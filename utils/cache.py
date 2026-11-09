"""A tiny thread-safe in-memory cache whose entries expire."""

import threading
import time

from collections import OrderedDict
from typing import Any, Callable, Hashable


class TTLCache:
    def __init__(self, ttl_seconds: float, max_size: int = 256):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._data: OrderedDict[Hashable, tuple[float, Any]] = OrderedDict()
        self._lock = threading.Lock()

    def get_or_set(self, key: Hashable, factory: Callable[[], Any]) -> Any:
        """Return the cached value for key, or compute, store and return it."""

        now = time.monotonic()

        with self._lock:
            entry = self._data.get(key)
            if entry and entry[0] > now:
                self._data.move_to_end(key)
                return entry[1]

        # Computed outside the lock so slow API calls don't block other keys
        value = factory()

        with self._lock:
            self._data[key] = (time.monotonic() + self.ttl_seconds, value)
            self._data.move_to_end(key)
            while len(self._data) > self.max_size:
                self._data.popitem(last=False)

        return value

    _MISSING = object()

    def get(self, key: Hashable, default: Any = None) -> Any:
        with self._lock:
            entry = self._data.get(key)
            if entry and entry[0] > time.monotonic():
                self._data.move_to_end(key)
                return entry[1]
        return default

    def has(self, key: Hashable) -> bool:
        return self.get(key, self._MISSING) is not self._MISSING

    def set(self, key: Hashable, value: Any) -> None:
        with self._lock:
            self._data[key] = (time.monotonic() + self.ttl_seconds, value)
            self._data.move_to_end(key)
            while len(self._data) > self.max_size:
                self._data.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()
