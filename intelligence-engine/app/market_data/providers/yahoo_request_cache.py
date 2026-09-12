"""Request-scoped + process TTL cache for Yahoo symbol resolution and enrich packs.

Ask often fans out to CID / DVC / YFP / company_memory — each historically
re-resolved META→META.NS and re-hit Yahoo. Resolve once per Ask request and reuse.
"""

from __future__ import annotations

import os
import threading
import time
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any, Dict, Iterator, Optional, Tuple

_SCOPE: ContextVar[Optional[Dict[str, Any]]] = ContextVar("yahoo_ask_scope", default=None)
_TTL_LOCK = threading.Lock()
_TTL: Dict[str, Tuple[float, Any]] = {}
_TTL_SEC = float(os.environ.get("YAHOO_CACHE_TTL_SEC", "300") or "300")


def begin_request_scope() -> Token:
    """Start a fresh per-Ask cache (call at UiService.search entry)."""
    return _SCOPE.set({})


def end_request_scope(token: Token) -> None:
    try:
        _SCOPE.reset(token)
    except Exception:
        pass


@contextmanager
def yahoo_request_scope() -> Iterator[Dict[str, Any]]:
    token = begin_request_scope()
    try:
        yield _SCOPE.get() or {}
    finally:
        end_request_scope(token)


def scope_get(key: str) -> Any:
    scope = _SCOPE.get()
    if not isinstance(scope, dict):
        return None
    return scope.get(key)


def scope_set(key: str, value: Any) -> None:
    scope = _SCOPE.get()
    if isinstance(scope, dict):
        scope[key] = value


def ttl_get(key: str) -> Any:
    now = time.monotonic()
    with _TTL_LOCK:
        row = _TTL.get(key)
        if not row:
            return None
        exp, val = row
        if exp < now:
            del _TTL[key]
            return None
        return val


def ttl_set(key: str, value: Any, *, ttl_sec: float | None = None) -> None:
    budget = _TTL_SEC if ttl_sec is None else max(1.0, float(ttl_sec))
    with _TTL_LOCK:
        _TTL[key] = (time.monotonic() + budget, value)
        # Soft bound — drop oldest-ish if huge
        if len(_TTL) > 512:
            for k in list(_TTL.keys())[:64]:
                _TTL.pop(k, None)


def cached_get(key: str) -> Any:
    """Prefer request scope, then process TTL."""
    hit = scope_get(key)
    if hit is not None:
        return hit
    hit = ttl_get(key)
    if hit is not None:
        scope_set(key, hit)
    return hit


def cached_set(key: str, value: Any, *, ttl_sec: float | None = None) -> Any:
    scope_set(key, value)
    ttl_set(key, value, ttl_sec=ttl_sec)
    return value
