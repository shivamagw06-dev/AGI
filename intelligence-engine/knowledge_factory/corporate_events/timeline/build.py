"""Timeline Intelligence — chronological, point-in-time, immutable."""

from __future__ import annotations

from typing import Any

from knowledge_factory.corporate_events.schema import ICEI_VERSION


def timeline_order_ok(events: list[dict[str, Any]]) -> bool:
    prev = ""
    for e in events:
        d = str(e.get("announcement_date") or e.get("date") or "")
        if prev and d < prev:
            return False
        prev = d or prev
    return True


def build_timeline(ticker: str, events: list[dict[str, Any]], *, sector: str | None = None) -> dict[str, Any]:
    ordered = sorted(
        events,
        key=lambda e: (
            str(e.get("announcement_date") or ""),
            str(e.get("effective_date") or ""),
            str(e.get("event_id") or ""),
        ),
    )
    by_year: dict[str, list[str]] = {}
    for e in ordered:
        y = str(e.get("announcement_date") or "")[:4] or "unknown"
        by_year.setdefault(y, []).append(e["event_id"])

    return {
        "kind": "company_event_timeline",
        "icei_version": ICEI_VERSION,
        "ticker": ticker.upper(),
        "sector": sector,
        "events": ordered,
        "event_ids": [e["event_id"] for e in ordered],
        "event_count": len(ordered),
        "by_year": by_year,
        "chronological": True,
        "order_valid": timeline_order_ok(ordered),
        "immutable": True,
        "point_in_time": True,
        "linked_evidence": sorted({ev for e in ordered for ev in (e.get("evidence") or [])}),
        "relationships": {
            "company": ticker.upper(),
            "sector": sector,
            "portfolio": "institutional_reasoning.ipi",
            "decision_quality": "decision_quality",
            "company_intelligence": f"knowledge_factory.company_intelligence:{ticker.upper()}",
        },
        "fabricated": False,
    }


def replay_as_of(timeline: dict[str, Any], as_of: str) -> dict[str, Any]:
    """Historical replay — never include events available after as_of."""
    cutoff = str(as_of or "")[:10]
    events = list(timeline.get("events") or [])
    visible = [
        e
        for e in events
        if str(e.get("available_from") or e.get("announcement_date") or "")[:10] <= cutoff
    ]
    return {
        "kind": "company_event_timeline_replay",
        "icei_version": ICEI_VERSION,
        "ticker": timeline.get("ticker"),
        "as_of": cutoff,
        "events": visible,
        "event_count": len(visible),
        "excluded_future_count": len(events) - len(visible),
        "future_leakage": False,
        "rule": "available_from <= as_of",
        "fabricated": False,
        "immutable": True,
    }
