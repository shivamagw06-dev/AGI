"""LangSmith-oriented HRI traces for Sprint 8.3."""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

# Share process-local ring with timeline traces when available
try:
    from app.timeline import traces as _shared

    def begin(name: str, *, meta: dict[str, Any] | None = None) -> dict[str, Any]:
        return _shared.begin(name, meta=meta)

    def end(span: dict[str, Any], *, ok: bool = True, output: dict[str, Any] | None = None) -> dict[str, Any]:
        return _shared.end(span, ok=ok, output=output)

    def recent(limit: int = 50) -> list[dict[str, Any]]:
        return _shared.recent(limit)

except Exception:  # pragma: no cover
    _TRACES: list[dict[str, Any]] = []

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
        if len(_TRACES) > 300:
            del _TRACES[:-300]
        return persisted

    def recent(limit: int = 50) -> list[dict[str, Any]]:
        return list(_TRACES[-limit:])
