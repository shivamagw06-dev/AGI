"""LangSmith-oriented CMKTP traces."""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

_TRACES: list[dict[str, Any]] = []

TRACE_NAMES = (
    "market_collection",
    "market_validation",
    "market_normalization",
    "market_materiality",
    "market_learning",
    "market_publication",
    "market_retrieval",
)


def begin(name: str, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "trace_id": str(uuid4()),
        "name": name,
        "started_mono": time.perf_counter(),
        "meta": meta or {},
        "status": "running",
    }


def end(span: dict[str, Any], *, ok: bool = True, output: dict[str, Any] | None = None) -> dict[str, Any]:
    span["status"] = "ok" if ok else "error"
    span["duration_ms"] = round((time.perf_counter() - float(span["started_mono"])) * 1000, 2)
    span["output"] = output or {}
    persisted = {k: v for k, v in span.items() if k != "started_mono"}
    _TRACES.append(persisted)
    if len(_TRACES) > 500:
        del _TRACES[:-500]
    return persisted


def recent(limit: int = 80) -> list[dict[str, Any]]:
    return list(_TRACES[-limit:])


def clear() -> None:
    _TRACES.clear()
