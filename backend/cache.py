"""Minimal in-memory, hash-keyed, TTL cache.

Avoids re-running the (paid, slower) LLM pass when the exact same code was
already reviewed recently. Not distributed / not persisted — swap for Redis
if running multiple instances.
"""
import hashlib
import time
from threading import Lock
from typing import Any, Optional

from backend.config import settings


class TTLCache:
    def __init__(self, ttl_seconds: int):
        self.ttl = ttl_seconds
        self._store: dict[str, tuple[float, Any]] = {}
        self._lock = Lock()

    @staticmethod
    def make_key(*parts: str) -> str:
        h = hashlib.sha256()
        for p in parts:
            h.update(p.encode("utf-8", errors="ignore"))
            h.update(b"\x00")
        return h.hexdigest()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if not entry:
                return None
            expires_at, value = entry
            if time.time() > expires_at:
                del self._store[key]
                return None
            return value

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            self._store[key] = (time.time() + self.ttl, value)

    def stats(self) -> dict:
        with self._lock:
            return {"entries": len(self._store), "ttl_seconds": self.ttl}


review_cache = TTLCache(settings.CACHE_TTL_SECONDS)
