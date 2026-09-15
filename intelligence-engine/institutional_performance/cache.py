"""PRP-01 distributed cache — Redis when available, in-memory fallback.

Namespaces: query · object · workspace · publication · graph
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from typing import Any, Optional

from institutional_performance.flags import redis_enabled
from institutional_performance.schema import CACHE_NAMESPACES, DEFAULT_TTLS

_LOCK = threading.RLock()
_MEM: dict[str, tuple[float, Any]] = {}
_HITS = 0
_MISSES = 0
_SETS = 0
_REDIS = None
_REDIS_OK = False
_REDIS_TRIED = False


def reset_for_tests() -> None:
    global _HITS, _MISSES, _SETS, _REDIS, _REDIS_OK, _REDIS_TRIED
    with _LOCK:
        _MEM.clear()
        _HITS = 0
        _MISSES = 0
        _SETS = 0
        _REDIS = None
        _REDIS_OK = False
        _REDIS_TRIED = False


def _client():
    global _REDIS, _REDIS_OK, _REDIS_TRIED
    if _REDIS_TRIED:
        return _REDIS if _REDIS_OK else None
    _REDIS_TRIED = True
    if not redis_enabled():
        _REDIS_OK = False
        return None
    try:
        import os

        import redis  # type: ignore

        url = os.environ.get("REDIS_URL") or "redis://localhost:6379/0"
        client = redis.Redis.from_url(url, socket_connect_timeout=0.35, socket_timeout=0.5)
        client.ping()
        _REDIS = client
        _REDIS_OK = True
        return client
    except Exception:
        _REDIS = None
        _REDIS_OK = False
        return None


def cache_key(namespace: str, *parts: Any) -> str:
    ns = str(namespace or "object")
    if ns not in CACHE_NAMESPACES:
        ns = "object"
    raw = "|".join(str(p) for p in parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"prp:{ns}:{digest}"


def get(namespace: str, *parts: Any) -> Any | None:
    global _HITS, _MISSES
    key = cache_key(namespace, *parts)
    client = _client()
    if client is not None:
        try:
            raw = client.get(key)
            if raw:
                with _LOCK:
                    _HITS += 1
                return json.loads(raw)
        except Exception:
            pass
    with _LOCK:
        row = _MEM.get(key)
        if not row:
            _MISSES += 1
            return None
        exp, val = row
        if time.time() > exp:
            _MEM.pop(key, None)
            _MISSES += 1
            return None
        _HITS += 1
        return val


def set(namespace: str, *parts: Any, value: Any, ttl: Optional[int] = None) -> str:
    global _SETS
    key = cache_key(namespace, *parts)
    ns = namespace if namespace in CACHE_NAMESPACES else "object"
    ttl_s = int(ttl if ttl is not None else DEFAULT_TTLS.get(ns, 120))
    client = _client()
    if client is not None:
        try:
            client.setex(key, ttl_s, json.dumps(value, default=str))
        except Exception:
            pass
    with _LOCK:
        _MEM[key] = (time.time() + ttl_s, value)
        _SETS += 1
    return key


def invalidate(namespace: str, *parts: Any) -> bool:
    key = cache_key(namespace, *parts)
    client = _client()
    if client is not None:
        try:
            client.delete(key)
        except Exception:
            pass
    with _LOCK:
        return _MEM.pop(key, None) is not None


def stats() -> dict[str, Any]:
    with _LOCK:
        total = _HITS + _MISSES
        hit_rate = round(_HITS / total, 4) if total else 0.0
        return {
            "redis_enabled": bool(_REDIS_OK),
            "redis_attempted": bool(_REDIS_TRIED),
            "memory_keys": len(_MEM),
            "hits": _HITS,
            "misses": _MISSES,
            "sets": _SETS,
            "hit_rate": hit_rate,
            "namespaces": list(CACHE_NAMESPACES),
            "ttls": dict(DEFAULT_TTLS),
        }


class NamespaceCache:
    """Thin OO façade over namespaced get/set/invalidate."""

    def __init__(self, namespace: str) -> None:
        self.namespace = namespace if namespace in CACHE_NAMESPACES else "object"

    def get(self, *parts: Any) -> Any | None:
        return get(self.namespace, *parts)

    def set(self, *parts: Any, value: Any = None, ttl_seconds: Optional[int] = None) -> str:
        # Support set(key, value, ttl_seconds=…) and set(*parts, value=…, ttl_seconds=…)
        if value is None and len(parts) >= 2:
            key_parts = parts[:-1]
            value = parts[-1]
            return set(self.namespace, *key_parts, value=value, ttl=ttl_seconds)
        return set(self.namespace, *parts, value=value, ttl=ttl_seconds)

    def delete(self, *parts: Any) -> bool:
        return invalidate(self.namespace, *parts)


def query_cache() -> NamespaceCache:
    return NamespaceCache("query")


def object_cache() -> NamespaceCache:
    return NamespaceCache("object")


def workspace_cache() -> NamespaceCache:
    return NamespaceCache("workspace")


def publication_cache() -> NamespaceCache:
    return NamespaceCache("publication")


def graph_cache() -> NamespaceCache:
    return NamespaceCache("graph")
