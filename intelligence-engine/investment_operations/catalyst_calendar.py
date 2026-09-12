"""P5.7 Catalyst Calendar — continuously aggregated from Opportunity / CompanyMemory."""

from __future__ import annotations

from typing import Any


def build_catalyst_calendar(company_packs: list[dict[str, Any]]) -> dict[str, Any]:
    rows = []
    for p in company_packs:
        oie = p.get("opportunity") or {}
        mem = p.get("memory") or {}
        for c in oie.get("catalysts") or []:
            rows.append(
                {
                    "ticker": p.get("display") or p.get("entity"),
                    "entity": p.get("entity"),
                    "name": c.get("name"),
                    "expected_window": c.get("expected_window"),
                    "importance": c.get("importance"),
                    "confidence": c.get("confidence"),
                    "evidence": c.get("evidence"),
                    "memory_version": mem.get("memory_version") or (oie.get("freshness") or {}).get("memory_version"),
                    "linked_to_company_memory": True,
                }
            )
        # Also surface event timeline breadcrumbs
        for e in ((mem.get("event_timeline") or {}).get("events") or [])[-5:]:
            rows.append(
                {
                    "ticker": p.get("display") or p.get("entity"),
                    "entity": p.get("entity"),
                    "name": e.get("title") or "Event",
                    "expected_window": "observed",
                    "importance": "Low",
                    "confidence": 0.5,
                    "evidence": {"source": "event_timeline", "date": e.get("date")},
                    "memory_version": mem.get("memory_version"),
                    "linked_to_company_memory": True,
                    "observed": True,
                }
            )

    imp = {"High": 0, "Medium": 1, "Low": 2}
    # Deduplicate by ticker+name
    seen = set()
    uniq = []
    for r in rows:
        key = (r.get("entity"), str(r.get("name") or "").lower())
        if key in seen:
            continue
        seen.add(key)
        uniq.append(r)
    uniq.sort(
        key=lambda r: (
            imp.get(r.get("importance") or "", 9),
            0 if r.get("expected_window") != "observed" else 1,
            r.get("ticker") or "",
            r.get("name") or "",
        )
    )
    return {
        "n": len(uniq),
        "catalysts": uniq,
        "by_importance": {
            k: [r for r in uniq if r.get("importance") == k] for k in ("High", "Medium", "Low")
        },
    }
