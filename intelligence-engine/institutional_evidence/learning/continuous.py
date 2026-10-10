"""Continuous Learning — evidence learning via KIL (not model training).

CGL gathers. KIL integrates. This module triggers KIL on evidence events.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


def learning_pipeline() -> List[str]:
    return [
        "CGL Acquire",
        "KIL Normalize",
        "Publish Canonical Evidence",
        "Update Company Memory",
        "Recompute Knowledge Graph",
        "Refresh Financial Intelligence",
        "Update Decision Eligibility",
        "Refresh Research Readiness",
        "Invalidate stale research",
        "Notify analysts",
    ]


def on_evidence_event(
    ticker: str,
    *,
    event_type: str = "new_filing",
    force_ingest: bool = False,
) -> Dict[str, Any]:
    from ..integration.layer import integrate_company
    from ..integration.events.bus import emit_cgl_events
    from ..entity.resolve import resolve_entity

    t = str(ticker or "").upper().strip()
    resolved = resolve_entity(t)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Optional: nudge CGL/FSE gather first
    cgl_nudge = None
    if force_ingest:
        try:
            from continuous_gather_learn.knowledge_extract import extract_from_hd_series

            cgl_nudge = extract_from_hd_series(t)
        except Exception as exc:
            cgl_nudge = {"ok": False, "error": str(exc)[:160]}

    fake_run = {
        "ok": True,
        "run_id": f"evt_{event_type}_{t}",
        "slot": "event",
        "volumes": {"knowledge_extracts": 1 if cgl_nudge else 0},
        "phases": [{"name": event_type}],
    }
    events = emit_cgl_events(fake_run, companies_updated=[t])
    integ = integrate_company(t, events=events, trigger_repair=True)

    notify = {
        "channel": "analyst_notifications",
        "message": (
            f"{t}: {event_type} — knowledge version "
            f"{integ.get('knowledge_version')} — "
            f"coverage={((integ.get('coverage_state') or {}).get('coverage_state'))}"
        ),
        "entity_id": resolved.get("entity_id"),
        "queued": True,
        "delivered": False,
    }

    return {
        "ok": True,
        "ticker": t,
        "entity_id": resolved.get("entity_id"),
        "event_type": event_type,
        "at": now,
        "pipeline": learning_pipeline(),
        "events": events,
        "integration": integ,
        "notification": notify,
        "rule": "Evidence learning via KIL — CGL gathers, KIL integrates, IEP preserves",
    }
