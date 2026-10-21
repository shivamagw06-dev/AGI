"""Optional Redis cache with in-memory fallback."""

from __future__ import annotations

import json
import time
from typing import Any


class AilCache:
    def __init__(self, *, redis_enabled: bool = False, ttl_seconds: int = 120) -> None:
        self.ttl = ttl_seconds
        self._mem: dict[str, tuple[float, Any]] = {}
        self.redis = None
        self.redis_enabled = False
        if redis_enabled:
            try:
                import redis  # type: ignore

                url = __import__("os").environ.get("REDIS_URL") or "redis://localhost:6379/0"
                client = redis.Redis.from_url(url, socket_connect_timeout=0.4)
                client.ping()
                self.redis = client
                self.redis_enabled = True
            except Exception:
                self.redis = None
                self.redis_enabled = False

    def get(self, key: str) -> Any | None:
        if self.redis_enabled and self.redis is not None:
            try:
                raw = self.redis.get(f"ail:{key}")
                if raw:
                    return json.loads(raw)
            except Exception:
                pass
        row = self._mem.get(key)
        if not row:
            return None
        exp, val = row
        if time.time() > exp:
            self._mem.pop(key, None)
            return None
        return val

    def set(self, key: str, value: Any) -> None:
        if self.redis_enabled and self.redis is not None:
            try:
                self.redis.setex(f"ail:{key}", self.ttl, json.dumps(value, default=str))
            except Exception:
                pass
        self._mem[key] = (time.time() + self.ttl, value)

    def stats(self) -> dict[str, Any]:
        return {
            "redis_enabled": self.redis_enabled,
            "memory_keys": len(self._mem),
            "ttl_seconds": self.ttl,
        }
