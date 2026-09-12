"""Compile immutable company event timeline."""

from __future__ import annotations

from typing import Any

from knowledge_factory.corporate_events import store as icei_store
from knowledge_factory.corporate_events.collectors.soft import collect_event_context
from knowledge_factory.corporate_events.producers.core import produce_events
from knowledge_factory.corporate_events.schema import FREEZE_LOCKS, ICEI_VERSION, PROGRAMME, LAYER
from knowledge_factory.corporate_events.timeline.build import build_timeline
from knowledge_factory.corporate_events.validators.gates import validate_timeline


def compile_company_timeline(ticker: str, *, persist: bool = True) -> dict[str, Any]:
    t = str(ticker or "").upper()
    ctx = collect_event_context(t)
    events = produce_events(ctx)
    timeline = build_timeline(t, events, sector=ctx.get("sector"))
    quality = validate_timeline(timeline)

    obj = {
        **timeline,
        "programme": PROGRAMME,
        "layer": LAYER,
        "quality": quality,
        "institutional_ready": bool(quality.get("institutional_ready")),
        "has_institutional_seed": bool(ctx.get("has_seed")),
        "coverage": {
            "event_count": len(events),
            "categories": sorted({e.get("category") for e in events if e.get("category")}),
            "critical_count": sum(1 for e in events if e.get("importance") == "Critical"),
            "timeline_completeness": min(100.0, round(100.0 * len(events) / 8.0, 2)),  # soft heuristic vs depth target
            "unknown_events": 0,  # we never invent; unknowns are absences, not rows
        },
        "freeze_locks": FREEZE_LOCKS,
        "architecture_status": "SOFT_CORPORATE_EVENT_INTELLIGENCE",
        "not_a_reasoning_engine": True,
        "icei_version": ICEI_VERSION,
        "fabricated": False,
    }
    if persist:
        for e in events:
            icei_store.put_event(e)
        icei_store.put_timeline(t, obj)
    return obj
