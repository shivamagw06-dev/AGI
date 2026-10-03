"""Feature value cache with dependency invalidation."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any

from app.features.models import FeatureValue


@dataclass
class _Entry:
    value: FeatureValue
    expires_at: float


class FeatureCache:
    def __init__(self) -> None:
        self._store: dict[str, _Entry] = {}
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0

    @staticmethod
    def key(feature_id: str, symbol: str | None, as_of: str, formula_version: str) -> str:
        return f"{feature_id}|{symbol or ''}|{as_of}|{formula_version}"

    def get(self, key: str) -> FeatureValue | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self.misses += 1
                return None
            if time.monotonic() >= entry.expires_at:
                del self._store[key]
                self.misses += 1
                return None
            self.hits += 1
            return entry.value

    def set(self, key: str, value: FeatureValue, ttl_s: float) -> None:
        with self._lock:
            self._store[key] = _Entry(value=value, expires_at=time.monotonic() + ttl_s)

    def invalidate_prefix(self, feature_id: str) -> int:
        with self._lock:
            keys = [k for k in self._store if k.startswith(f"{feature_id}|")]
            for k in keys:
                del self._store[k]
            return len(keys)

    def clear(self) -> None:
        with self._lock:
            self._store.clear()

    def stats(self) -> dict[str, Any]:
        total = self.hits + self.misses
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_ratio": (self.hits / total) if total else 0.0,
            "size": len(self._store),
        }
