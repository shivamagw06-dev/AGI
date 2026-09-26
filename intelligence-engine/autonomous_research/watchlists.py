"""P6.4 Watchlist Manager — dynamic institutional watchlists from Opportunity Intelligence."""

from __future__ import annotations

from typing import Any

from autonomous_research.schema import WATCHLIST_BUCKETS
from autonomous_research.util import as_float, delta_of, oie_of, priority_rank


def build_watchlists(
    company_packs: list[dict[str, Any]],
    *,
    holdings: list[str] | None = None,
) -> dict[str, Any]:
    holdings_set = {h.upper() for h in (holdings or [])}
    buckets: dict[str, list[dict[str, Any]]] = {b: [] for b in WATCHLIST_BUCKETS}

    for p in company_packs:
        if not p.get("ok"):
            continue
        oie = oie_of(p)
        kd = delta_of(p)
        row = {
            "company": p.get("display") or p.get("entity"),
            "entity": p.get("entity"),
            "score": oie.get("score"),
            "research_priority": oie.get("research_priority"),
            "why_now": oie.get("why_now"),
            "delta_status": kd.get("status"),
        }
        pr = oie.get("research_priority") or "Monitor"
        if pr in {"Critical", "High"}:
            buckets["high_priority"].append(row)
        elif pr == "Medium":
            buckets["medium_priority"].append(row)
        else:
            buckets["low_priority"].append(row)

        if any(c.get("importance") == "High" for c in (oie.get("catalysts") or [])):
            buckets["event_driven"].append(row)
        themes = (p.get("knowledge_graph") or {}).get("themes") or []
        sector = (p.get("knowledge_graph") or {}).get("sector_key") or (
            (p.get("memory") or {}).get("sector_history") or {}
        ).get("sector_key")
        if themes or sector in {"banks", "auto", "cement", "power"}:
            buckets["macro_sensitive"].append(row)
        if (p.get("display") or "").upper() in holdings_set or (p.get("entity") or "") in holdings_set:
            buckets["portfolio_critical"].append(row)

    for b in buckets:
        buckets[b] = sorted(
            _dedupe(buckets[b]),
            key=lambda r: (-(as_float(r.get("score")) or 0), priority_rank(r.get("research_priority")), r.get("entity") or ""),
        )

    return {
        "watchlists": buckets,
        "counts": {k: len(v) for k, v in buckets.items()},
        "reprioritised_by": "opportunity_intelligence+knowledge_delta+catalysts+portfolio",
        "issues_recommendations": False,
    }


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    out = []
    for r in rows:
        k = r.get("entity")
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out
