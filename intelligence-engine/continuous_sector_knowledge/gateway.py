"""Read-only Sector Knowledge Retrieval Gateway — never builds on Ask."""

from __future__ import annotations

from typing import Any

from continuous_sector_knowledge import traces
from continuous_sector_knowledge.schema import canonicalize
from continuous_sector_knowledge.store import STORE


def retrieve_all(*, limit: int = 100) -> dict[str, Any]:
    span = traces.begin("sector_refresh", meta={"scope": "list"})  # retrieval soft span
    rows = STORE.list_all(limit=limit)
    out = {
        "n": len(rows),
        "sectors": [r.to_public_dict() for r in rows],
        "coverage": STORE.coverage(),
        "providers_queried": [],
        "collected_on_request": False,
        "ask_triggers_collection": False,
        "constructed_on_request": False,
        "gateway": "CSKP_KRIG",
    }
    traces.end(span, output={"n": out["n"]})
    return out


def retrieve_sector(sector: str) -> dict[str, Any]:
    key = canonicalize(sector) or sector.lower().replace(" ", "_")
    span = traces.begin("sector_refresh", meta={"scope": "sector", "sector": key})
    tip = STORE.latest(key)
    if not tip:
        out = {
            "found": False,
            "sector": key,
            "collected_on_request": False,
            "ask_triggers_collection": False,
            "constructed_on_request": False,
            "reason": "not_published_in_sector_knowledge_store",
            "gateway": "CSKP_KRIG",
            "providers_queried": [],
        }
        traces.end(span, ok=False, output=out)
        return out
    versions = STORE.versions(key)
    out = {
        "found": True,
        "sector": key,
        "latest": tip.to_public_dict(),
        "versions": [v.to_public_dict() for v in versions],
        "collected_on_request": False,
        "ask_triggers_collection": False,
        "constructed_on_request": False,
        "gateway": "CSKP_KRIG",
        "providers_queried": [],
    }
    traces.end(span, output={"found": True, "version": tip.version})
    return out


def retrieve_leaders(*, limit: int = 50) -> dict[str, Any]:
    rows = STORE.list_all(limit=200)
    leaders = []
    for r in rows:
        leaders.append(
            {
                "sector_key": r.sector_key,
                "label": r.label,
                "outlook": r.current_outlook,
                "leading_companies": r.leading_companies[:8],
                "sector_confidence": r.sector_confidence,
            }
        )
    leaders.sort(key=lambda x: (-(x.get("sector_confidence") or 0), x["label"]))
    return {
        "n": min(limit, len(leaders)),
        "leaders": leaders[:limit],
        "providers_queried": [],
        "collected_on_request": False,
        "gateway": "CSKP_KRIG",
    }


def retrieve_comparison(*, sectors: list[str] | None = None) -> dict[str, Any]:
    rows = STORE.list_all(limit=200)
    if sectors:
        keys = {canonicalize(s) or s.lower().replace(" ", "_") for s in sectors}
        rows = [r for r in rows if r.sector_key in keys]
    matrix = [
        {
            "sector_key": r.sector_key,
            "label": r.label,
            "outlook": r.current_outlook,
            "revenue_trend": r.revenue_trend,
            "margin_trend": r.margin_trend,
            "valuation": r.valuation,
            "confidence": r.sector_confidence,
            "macro_sensitivity": r.macro_sensitivity,
            "leaders": r.leading_companies[:5],
        }
        for r in rows
    ]
    return {
        "n": len(matrix),
        "comparison": matrix,
        "providers_queried": [],
        "collected_on_request": False,
        "gateway": "CSKP_KRIG",
    }
