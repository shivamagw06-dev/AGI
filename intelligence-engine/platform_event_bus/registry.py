"""EventRegistry — known event types, schema versions, producers, descriptions."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any, Optional

from platform_event_bus.schema import BUILTIN_EVENT_TYPES, EVENT_SCHEMA_VERSION


_LOCK = Lock()
_TYPES: dict[str, dict[str, Any]] = {}


def _seed_builtins() -> None:
    descriptions = {
        "company.research.completed": "IO-01 finished assembling an Institutional Research Package",
        "business_quality.updated": "FIRE-06 quality pack available / refreshed for a company",
        "management_execution.updated": "FIRE-05 execution pack available / refreshed for a company",
        "portfolio.snapshot.created": "PO-01 created an immutable portfolio snapshot",
        "portfolio.updated": "PO-01 live portfolio state changed",
        "watchlist.company.added": "WO-01 (future) company added to a watchlist",
        "watchlist.company.removed": "WO-01 (future) company removed from a watchlist",
        "comparison.completed": "CIO-01 finished an Institutional Comparison Report",
        "office.request.completed": "Any office completed an Office SDK request",
        "office.error": "Any office reported a structured error",
    }
    producers = {
        "company.research.completed": "io-01",
        "business_quality.updated": "fire-06",
        "management_execution.updated": "fire-05",
        "portfolio.snapshot.created": "po-01",
        "portfolio.updated": "po-01",
        "watchlist.company.added": "wo-01",
        "watchlist.company.removed": "wo-01",
        "comparison.completed": "cio-01",
        "office.request.completed": "office_sdk",
        "office.error": "office_sdk",
    }
    for et in BUILTIN_EVENT_TYPES:
        _TYPES[et] = {
            "event_type": et,
            "schema_version": EVENT_SCHEMA_VERSION,
            "producer": producers.get(et),
            "description": descriptions.get(et, ""),
            "builtin": True,
            "status": "active",
        }


_seed_builtins()


def register_event_type(
    event_type: str,
    *,
    description: str = "",
    producer: Optional[str] = None,
    schema_version: str = EVENT_SCHEMA_VERSION,
    status: str = "active",
) -> dict[str, Any]:
    et = str(event_type or "").strip()
    if not et or "*" in et or et.endswith("."):
        raise ValueError(f"invalid event_type: {event_type!r}")
    with _LOCK:
        existing = _TYPES.get(et)
        if existing and existing.get("builtin") and existing.get("event_type") == et:
            # Allow metadata enrichment but keep builtin flag
            row = {
                **existing,
                "description": description or existing.get("description"),
                "producer": producer or existing.get("producer"),
                "schema_version": schema_version or existing.get("schema_version"),
                "status": status or existing.get("status"),
            }
            _TYPES[et] = row
            return deepcopy(row)
        row = {
            "event_type": et,
            "schema_version": schema_version,
            "producer": producer,
            "description": description,
            "builtin": False,
            "status": status,
        }
        _TYPES[et] = row
        return deepcopy(row)


def get_event_type(event_type: str) -> Optional[dict[str, Any]]:
    with _LOCK:
        row = _TYPES.get(str(event_type or "").strip())
        return deepcopy(row) if row else None


def list_event_types(*, include_reserved: bool = True) -> list[dict[str, Any]]:
    with _LOCK:
        rows = [deepcopy(v) for v in _TYPES.values()]
    if not include_reserved:
        rows = [r for r in rows if r.get("status") != "reserved"]
    rows.sort(key=lambda r: r["event_type"])
    return rows


def is_known(event_type: str) -> bool:
    return get_event_type(event_type) is not None


def reset_for_tests() -> None:
    with _LOCK:
        _TYPES.clear()
    _seed_builtins()
