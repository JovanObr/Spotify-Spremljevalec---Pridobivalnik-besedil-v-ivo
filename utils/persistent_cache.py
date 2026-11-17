"""
A small SQLite cache that survives restarts, for answers that cost quota or
time to get again: lyrics, AI facts/translations/explanations and
MusicAtlas results.

It's off unless the app's entry points turn it on (python -m api and
python -m grpc_api call enable_default()), so tests and scripts never touch
the real file. Both servers can share the file at the same time.

Anything going wrong with the file (locked, disk full, corrupt) is logged
and ignored: the cache is only ever a shortcut, never required.
"""

import hashlib
import json
import logging
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Callable


logger = logging.getLogger(__name__)

PATH_ENV = "PERSISTENT_CACHE_PATH"
SWITCH_ENV = "PERSISTENT_CACHE"  # "off" disables it

DAY = 24 * 3600

MISSING = object()  # "not cached" (None is a valid cached value)


class PersistentCache:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self._lock = threading.Lock()
        self._db: sqlite3.Connection | None = None
        self._broken = False

    def _connect(self) -> sqlite3.Connection | None:
        if self._db is not None or self._broken:
            return self._db
        try:
            if self.path != ":memory:":
                Path(self.path).parent.mkdir(parents=True, exist_ok=True)
            db = sqlite3.connect(self.path, timeout=5, check_same_thread=False)
            db.execute("PRAGMA journal_mode=WAL")  # the two servers can share it
            db.execute(
                "CREATE TABLE IF NOT EXISTS cache ("
                " namespace TEXT NOT NULL,"
                " key TEXT NOT NULL,"
                " value TEXT NOT NULL,"
                " expires_at REAL NOT NULL,"
                " PRIMARY KEY (namespace, key))"
            )
            db.execute("DELETE FROM cache WHERE expires_at < ?", (time.time(),))
            db.commit()
            self._db = db
        except (sqlite3.Error, OSError) as error:
            logger.warning("Persistent cache disabled (%s): %s", self.path, error)
            self._broken = True
        return self._db

    @staticmethod
    def _key(key: Any) -> str:
        # Keys can be long (a song's lyrics); store a fixed-size digest
        text = json.dumps(key, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def get(self, namespace: str, key: Any) -> Any:
        """The stored value, or MISSING."""
        with self._lock:
            db = self._connect()
            if db is None:
                return MISSING
            try:
                row = db.execute(
                    "SELECT value, expires_at FROM cache WHERE namespace = ? AND key = ?",
                    (namespace, self._key(key)),
                ).fetchone()
            except sqlite3.Error as error:
                logger.warning("Persistent cache read failed: %s", error)
                return MISSING
        if row is None or row[1] < time.time():
            return MISSING
        try:
            return json.loads(row[0])
        except ValueError:
            return MISSING

    def set(self, namespace: str, key: Any, value: Any, ttl_seconds: float) -> None:
        try:
            text = json.dumps(value, ensure_ascii=False)
        except (TypeError, ValueError) as error:
            logger.warning("Not caching %s: %s", namespace, error)
            return
        with self._lock:
            db = self._connect()
            if db is None:
                return
            try:
                db.execute(
                    "INSERT OR REPLACE INTO cache (namespace, key, value, expires_at) VALUES (?, ?, ?, ?)",
                    (namespace, self._key(key), text, time.time() + ttl_seconds),
                )
                db.commit()
            except sqlite3.Error as error:
                logger.warning("Persistent cache write failed: %s", error)

    def clear(self, namespace: str | None = None) -> None:
        with self._lock:
            db = self._connect()
            if db is None:
                return
            if namespace is None:
                db.execute("DELETE FROM cache")
            else:
                db.execute("DELETE FROM cache WHERE namespace = ?", (namespace,))
            db.commit()

    def close(self) -> None:
        with self._lock:
            if self._db is not None:
                self._db.close()
                self._db = None


class _Disabled:
    """Stands in when the cache is off."""

    def get(self, namespace, key):
        return MISSING

    def set(self, namespace, key, value, ttl_seconds):
        pass

    def clear(self, namespace=None):
        pass


_store: PersistentCache | _Disabled | None = None
_store_lock = threading.Lock()


def store() -> PersistentCache | _Disabled:
    """The shared cache, opened on first use (from PERSISTENT_CACHE_PATH)."""
    global _store
    with _store_lock:
        if _store is None:
            path = os.getenv(PATH_ENV)
            off = os.getenv(SWITCH_ENV, "").strip().lower() in ("off", "0", "false", "no")
            _store = PersistentCache(path) if path and not off else _Disabled()
        return _store


def configure(path: str | Path | None) -> None:
    """Use this file (None: turn the cache off). For tests and tools."""
    global _store
    with _store_lock:
        if isinstance(_store, PersistentCache):
            _store.close()
        _store = PersistentCache(path) if path else _Disabled()


def enable_default(base_dir: Path) -> None:
    """
    Called by the servers' entry points. Uses .data/cache.sqlite3 in the
    project unless PERSISTENT_CACHE_PATH or PERSISTENT_CACHE=off says
    otherwise. Set as an environment variable so uvicorn's reload worker
    inherits it.
    """
    os.environ.setdefault(PATH_ENV, str(base_dir / ".data" / "cache.sqlite3"))


def remember(
    namespace: str,
    key: Any,
    ttl_seconds: float,
    compute: Callable[[], Any],
    encode: Callable[[Any], Any] = lambda value: value,
    decode: Callable[[Any], Any] = lambda value: value,
):
    """The stored answer, or compute it, store it and return it."""
    cache = store()
    hit = cache.get(namespace, key)
    if hit is not MISSING:
        try:
            return decode(hit)
        except Exception as error:  # an old or unexpected shape: compute again
            logger.info("Ignoring stale %s cache entry: %s", namespace, error)
    value = compute()
    cache.set(namespace, key, encode(value), ttl_seconds)
    return value
