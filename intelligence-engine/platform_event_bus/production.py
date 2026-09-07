"""PEB-01 Mission Control / API façades — infrastructure only."""

from __future__ import annotations

from typing import Any

from platform_event_bus.dispatcher import get_dispatcher
from platform_event_bus.flags import flags_dict, is_enabled
from platform_event_bus import metrics as bus_metrics
from platform_event_bus import registry as event_registry
from platform_event_bus.schema import (
    PEB01_LAYER,
    PEB01_PRODUCT,
    PEB01_SPEC,
    PEB01_SUBSYSTEM,
    PEB01_VERSION,
    PEB01_WORKSTREAM_ID,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": PEB01_WORKSTREAM_ID,
        "product": PEB01_PRODUCT,
        "subsystem": PEB01_SUBSYSTEM,
        "version": PEB01_VERSION,
        "layer": PEB01_LAYER,
        "role": "platform_event_bus",
        "infrastructure_only": True,
        "business_logic": False,
        "modifies_intelligence": False,
        "persistence": False,
        "retries": False,
        "broker": "in_process_sync",
        "delivery": "at_most_once",
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": PEB01_SPEC,
        "as_of": now_iso(),
    }


def dashboard() -> dict[str, Any]:
    stats = bus_metrics.statistics()
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": PEB01_WORKSTREAM_ID,
        "version": PEB01_VERSION,
        "panels": stats.get("panels") or {},
        "statistics": stats,
        "subscribers": get_dispatcher().list_subscribers(),
        "event_types_n": len(event_registry.list_event_types()),
        "spec": PEB01_SPEC,
        "as_of": now_iso(),
    }


def list_events(limit: int = 50) -> dict[str, Any]:
    return {
        "ok": True,
        "workstream_id": PEB01_WORKSTREAM_ID,
        "version": PEB01_VERSION,
        "events": bus_metrics.recent_events(limit=limit),
        "n": min(limit, len(bus_metrics.recent_events(limit=limit))),
        "note": "Recent in-process events only; no persistence.",
    }


def list_types() -> dict[str, Any]:
    return {
        "ok": True,
        "workstream_id": PEB01_WORKSTREAM_ID,
        "version": PEB01_VERSION,
        "types": event_registry.list_event_types(include_reserved=True),
    }


def statistics() -> dict[str, Any]:
    return {
        "ok": True,
        "workstream_id": PEB01_WORKSTREAM_ID,
        "version": PEB01_VERSION,
        "statistics": bus_metrics.statistics(),
        "subscribers": get_dispatcher().list_subscribers(),
        "failures": bus_metrics.recent_failures(limit=20),
    }


def soft_slice_mission_control() -> dict[str, Any]:
    stats = bus_metrics.statistics()
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": PEB01_WORKSTREAM_ID,
        "product": PEB01_PRODUCT,
        "version": PEB01_VERSION,
        "infrastructure_only": True,
        "panels": stats.get("panels") or {},
        "statistics": stats,
    }


def admin_page() -> str:
    h = health()
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>PEB-01 Platform Event Bus</title></head>
<body>
<h1>PEB-01 — Platform Event Bus</h1>
<pre>{h}</pre>
<p>In-process typed pub/sub. No business logic. No persistence. No broker.</p>
</body></html>"""
