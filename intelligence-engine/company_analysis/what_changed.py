"""Step 8 — What changed vs prior quarter / house view / history."""

from __future__ import annotations

from typing import Any


def analyse_what_changed(
    *,
    cid: dict[str, Any] | None = None,
    leo_pkg: dict[str, Any] | None = None,
    financial: dict[str, Any] | None = None,
    market_events: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cid = cid or {}
    fin = financial or {}
    improved = list(fin.get("what_improved") or [])
    deteriorated = list(fin.get("what_deteriorated") or [])
    unchanged: list[str] = []

    timeline = list(cid.get("evidence_timeline") or [])[-5:]
    events = []
    if isinstance(market_events, dict):
        company = market_events.get("company") or {}
        for e in (company.get("events") or market_events.get("events") or [])[:5]:
            if isinstance(e, dict):
                events.append(e.get("title") or e.get("summary") or e.get("event_type"))

    leo_fresh = []
    for obj in (leo_pkg or {}).get("evidence_objects") or []:
        if isinstance(obj, dict):
            leo_fresh.append(obj.get("type") or obj.get("title"))

    if not improved and not deteriorated:
        unchanged.append("No structured trend deltas in financial_history yet")
    if timeline:
        unchanged.append("Dossier timeline present — compare latest evidence stamps")

    return {
        "improved": improved,
        "deteriorated": deteriorated,
        "unchanged": unchanged,
        "recent_timeline": timeline,
        "market_events": [e for e in events if e][:5],
        "fresh_evidence_types": [x for x in leo_fresh if x][:8],
        "sources": ["cid.evidence_timeline", "financial_intelligence", "leo", "market_events"],
    }
