"""In-memory 24h cache for identical editorial recommendation requests."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any

CACHE_TTL_SECONDS = 24 * 60 * 60


class EditorialCache:
    def __init__(self, ttl_seconds: int = CACHE_TTL_SECONDS) -> None:
        self.ttl = ttl_seconds
        self._lock = threading.Lock()
        self._store: dict[str, tuple[float, dict[str, Any]]] = {}

    @staticmethod
    def make_key(mode: str, structured: dict[str, Any], question: str | None = None) -> str:
        payload = {
            "mode": mode,
            "question": (question or "").strip().lower(),
            "structured": structured,
        }
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> dict[str, Any] | None:
        now = time.time()
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            expires_at, value = item
            if expires_at < now:
                self._store.pop(key, None)
                return None
            return dict(value)

    def set(self, key: str, value: dict[str, Any]) -> None:
        with self._lock:
            self._store[key] = (time.time() + self.ttl, dict(value))
            if len(self._store) > 2048:
                # Drop expired / oldest half under lock
                expired = [k for k, (exp, _) in self._store.items() if exp < time.time()]
                for k in expired:
                    self._store.pop(k, None)
                if len(self._store) > 2048:
                    for k in list(self._store.keys())[:512]:
                        self._store.pop(k, None)


_GLOBAL_CACHE = EditorialCache()


def get_cache() -> EditorialCache:
    return _GLOBAL_CACHE
