"""Distributed tracing — observe spans; never alter execution (PRP-03)."""

from __future__ import annotations

import secrets
import threading
import time
from typing import Any, Dict, List, Optional

from institutional_observability.models import InstitutionalSpan, InstitutionalTrace

_LOCK = threading.Lock()
_TRACES: Dict[str, dict[str, Any]] = {}
_ACTIVE: Dict[str, dict[str, Any]] = {}
_ORDER: List[str] = []


def reset_for_tests() -> None:
    with _LOCK:
        _TRACES.clear()
        _ACTIVE.clear()
        _ORDER.clear()


def new_trace_id() -> str:
    return f"tr_{secrets.token_hex(10)}"


def new_span_id() -> str:
    return f"sp_{secrets.token_hex(6)}"


def start_trace(
    *,
    correlation_id: str = "",
    request_source: str = "api",
    name: str = "request",
) -> dict[str, Any]:
    tid = new_trace_id()
    now = time.perf_counter()
    root = {
        "span_id": new_span_id(),
        "name": name,
        "parent_span_id": "",
        "start": now,
        "end": None,
        "outcome": "ok",
        "attributes": {"request_source": request_source},
    }
    row = {
        "trace_id": tid,
        "correlation_id": correlation_id or "",
        "request_source": request_source,
        "start": now,
        "end": None,
        "outcome": "ok",
        "spans": [root],
        "diagnostics": {},
    }
    with _LOCK:
        _ACTIVE[tid] = row
        _ORDER.append(tid)
        if len(_ORDER) > 2000:
            old = _ORDER.pop(0)
            _ACTIVE.pop(old, None)
            _TRACES.pop(old, None)
    return {"trace_id": tid, "root_span_id": root["span_id"], "correlation_id": correlation_id}


def start_span(
    trace_id: str,
    name: str,
    *,
    parent_span_id: str = "",
    attributes: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    with _LOCK:
        row = _ACTIVE.get(trace_id)
        if not row:
            return None
        parent = parent_span_id or (row["spans"][0]["span_id"] if row["spans"] else "")
        span = {
            "span_id": new_span_id(),
            "name": name,
            "parent_span_id": parent,
            "start": time.perf_counter(),
            "end": None,
            "outcome": "ok",
            "attributes": dict(attributes or {}),
        }
        row["spans"].append(span)
        return span["span_id"]


def end_span(trace_id: str, span_id: str, *, outcome: str = "ok") -> None:
    with _LOCK:
        row = _ACTIVE.get(trace_id) or _TRACES.get(trace_id)
        if not row:
            return
        for span in row["spans"]:
            if span["span_id"] == span_id:
                span["end"] = time.perf_counter()
                span["outcome"] = outcome
                break


def end_trace(trace_id: str, *, outcome: str = "ok") -> Optional[InstitutionalTrace]:
    with _LOCK:
        row = _ACTIVE.pop(trace_id, None)
        if not row:
            row = _TRACES.get(trace_id)
            if not row:
                return None
        now = time.perf_counter()
        row["end"] = now
        row["outcome"] = outcome
        for span in row["spans"]:
            if span.get("end") is None:
                span["end"] = now
                span["outcome"] = outcome
        spans = tuple(
            InstitutionalSpan(
                span_id=s["span_id"],
                name=s["name"],
                parent_span_id=s.get("parent_span_id") or "",
                start_ms=round((s["start"] - row["start"]) * 1000.0, 3),
                end_ms=round(((s.get("end") or now) - row["start"]) * 1000.0, 3),
                outcome=s.get("outcome") or "ok",
                attributes=dict(s.get("attributes") or {}),
            )
            for s in row["spans"]
        )
        trace = InstitutionalTrace(
            trace_id=trace_id,
            correlation_id=str(row.get("correlation_id") or ""),
            spans=spans,
            duration_ms=round((now - row["start"]) * 1000.0, 3),
            outcome=outcome,
            diagnostics=dict(row.get("diagnostics") or {}),
        )
        _TRACES[trace_id] = {
            **row,
            "frozen": trace.to_dict(),
        }
        return trace


def get_trace(trace_id: str) -> Optional[dict[str, Any]]:
    with _LOCK:
        row = _TRACES.get(trace_id) or _ACTIVE.get(trace_id)
        if not row:
            return None
        if "frozen" in row:
            return dict(row["frozen"])
        # Live snapshot
        now = time.perf_counter()
        spans = []
        for s in row["spans"]:
            end = s.get("end") or now
            spans.append(
                {
                    "span_id": s["span_id"],
                    "name": s["name"],
                    "parent_span_id": s.get("parent_span_id") or None,
                    "start_ms": round((s["start"] - row["start"]) * 1000.0, 3),
                    "end_ms": round((end - row["start"]) * 1000.0, 3),
                    "duration_ms": round((end - s["start"]) * 1000.0, 3),
                    "outcome": s.get("outcome") or "ok",
                    "attributes": dict(s.get("attributes") or {}),
                    "active": s.get("end") is None,
                }
            )
        return {
            "trace_id": trace_id,
            "correlation_id": row.get("correlation_id"),
            "spans": spans,
            "duration_ms": round((now - row["start"]) * 1000.0, 3),
            "outcome": row.get("outcome") or "ok",
            "active": True,
            "span_count": len(spans),
        }


def active_trace_count() -> int:
    with _LOCK:
        return len(_ACTIVE)


def recent_traces(limit: int = 20) -> list[dict[str, Any]]:
    with _LOCK:
        ids = list(reversed(_ORDER))[:limit]
    out = []
    for tid in ids:
        t = get_trace(tid)
        if t:
            out.append(t)
    return out


def validate_span_hierarchy(trace: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    spans = {s["span_id"]: s for s in trace.get("spans") or []}
    if not spans:
        errors.append("trace has no spans")
        return errors
    roots = [s for s in spans.values() if not s.get("parent_span_id")]
    if len(roots) != 1:
        errors.append(f"expected 1 root span, found {len(roots)}")
    for s in spans.values():
        parent = s.get("parent_span_id")
        if parent and parent not in spans:
            errors.append(f"orphan span parent: {parent}")
    if not trace.get("correlation_id"):
        errors.append("trace missing correlation ID")
    return errors
