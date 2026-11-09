"""
Run expensive work once per key, even when several threads ask at once.

If a request for a key is already running, other callers wait for it
instead of starting the same work again (e.g. the browser asking for a
song's AI facts while the server is already preparing them).
"""

import threading

from collections import defaultdict
from contextlib import contextmanager
from typing import Hashable, Iterator


class SingleFlight:
    def __init__(self):
        self._guard = threading.Lock()
        self._locks: dict[Hashable, threading.Lock] = {}
        self._users: defaultdict[Hashable, int] = defaultdict(int)

    @contextmanager
    def lock(self, key: Hashable) -> Iterator[None]:
        with self._guard:
            key_lock = self._locks.setdefault(key, threading.Lock())
            self._users[key] += 1
        try:
            with key_lock:
                yield
        finally:
            with self._guard:
                self._users[key] -= 1
                if self._users[key] == 0:
                    del self._users[key]
                    del self._locks[key]
