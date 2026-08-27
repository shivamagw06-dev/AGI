"""Correlation ID — flows across security, orchestration, performance, audit (PRP-02)."""

from __future__ import annotations

import secrets
import threading
from contextvars import ContextVar
from typing import Any, Optional

_CORRELATION: ContextVar[str] = ContextVar("prp02_correlation_id", default="")
_local = threading.local()


def new_correlation_id() -> str:
    return f"corr_{secrets.token_hex(10)}"


def ensure_correlation_id(raw: Optional[str] = None) -> str:
    cid = str(raw or "").strip()
    if not cid:
        cid = new_correlation_id()
    _CORRELATION.set(cid)
    _local.correlation_id = cid
    return cid


def get_correlation_id() -> str:
    cid = _CORRELATION.get()
    if cid:
        return cid
    return str(getattr(_local, "correlation_id", "") or "")


def attach_correlation(payload: Optional[dict[str, Any]] = None) -> str:
    body = dict(payload or {})
    return ensure_correlation_id(
        body.get("correlation_id")
        or body.get("x_correlation_id")
        or body.get("X-Correlation-Id")
    )
