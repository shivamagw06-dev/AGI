"""Research queue — today's institutional work list (knowledge only)."""

from __future__ import annotations

from typing import Any

from research_office import store
from research_office.templates import knowledge as kn


def build_research_queue(*, publications: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    pubs = publications or store.list_publications(limit=50)
    coverage = kn.read_coverage()
    events = kn.read_corporate_events()
    gov = kn.read_government()
    macro = kn.read_macro()
    industry = kn.read_industry()
    company = kn.read_company_intelligence()

    missing = []
    for p in pubs:
        fails = (p.get("validation") or {}).get("failures") or []
        if fails:
            missing.append(
                {
                    "publication_id": p.get("id"),
                    "title": p.get("title"),
                    "failures": fails,
                    "recommendation": None,
                }
            )

    queue = {
        "as_of": store.utc_now(),
        "todays_companies": _items_from(company, "company"),
        "todays_events": _items_from(events, "event"),
        "todays_government_changes": _items_from(gov, "government"),
        "todays_macro_topics": _items_from(macro, "macro"),
        "todays_sector_reviews": [{"topic": "sector_intelligence_report", "priority": "normal"}],
        "todays_industry_reviews": _items_from(industry, "industry"),
        "todays_follow_ups": [
            {"item": p.get("title"), "publication_id": p.get("id"), "status": p.get("status")}
            for p in pubs
            if p.get("status") != "institutionally_ready"
        ],
        "todays_missing_evidence": missing,
        "coverage_snapshot": {
            "unavailable": bool(coverage.get("unavailable")),
            "keys": list(coverage.keys())[:20],
        },
        "recommendation": None,
        "knowledge_only": True,
        "fabricated": False,
    }
    store.put_queue(queue)
    return queue


def _items_from(payload: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    if payload.get("unavailable"):
        return [{"kind": kind, "status": "unavailable", "priority": "high", "recommendation": None}]
    return [
        {
            "kind": kind,
            "status": "review",
            "priority": "normal",
            "observed_keys": [k for k in payload.keys() if k != "fabricated"][:8],
            "recommendation": None,
        }
    ]
