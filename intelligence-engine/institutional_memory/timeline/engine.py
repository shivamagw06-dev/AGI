"""Institutional timeline across thesis / committee / forecast / lessons."""

from __future__ import annotations

from typing import Any

from institutional_memory.store.corpus import get_company


def institutional_timeline(ticker: str) -> dict[str, Any]:
    company = get_company(ticker)
    if not company:
        return {"found": False, "ticker": (ticker or "").upper(), "events": []}
    events: list[dict[str, Any]] = []
    for t in company.get("theses") or []:
        events.append({"date": t.get("date"), "kind": "thesis", "summary": f"v{t.get('version')} {t.get('stance')}"})
    for d in company.get("committee_decisions") or []:
        events.append({"date": d.get("date"), "kind": "committee", "summary": d.get("consensus")})
    for f in company.get("forecasts") or []:
        events.append(
            {
                "date": f.get("date"),
                "kind": "forecast",
                "summary": f"most_likely={f.get('most_likely')} actual={f.get('actual_outcome')}",
            }
        )
    for l in company.get("lessons") or []:
        events.append({"date": l.get("date"), "kind": "lesson", "summary": l.get("lesson")})
    for m in company.get("mistakes") or []:
        events.append({"date": m.get("date"), "kind": "mistake", "summary": f"{m.get('error_type')}: {m.get('example')}"})
    events.sort(key=lambda e: str(e.get("date") or ""))
    return {"found": True, "ticker": company["ticker"], "events": events, "count": len(events)}
