"""Watchlist engine — knowledge triggers only; no portfolio actions."""

from __future__ import annotations

from typing import Any

from research_office import store
from research_office.schema import WATCHLIST_TYPES
from research_office.templates import knowledge as kn


def build_watchlists(*, publications: list[dict[str, Any]] | None = None) -> dict[str, list[dict[str, Any]]]:
    pubs = publications or store.list_publications(limit=50)
    now = store.utc_now()
    lists: dict[str, list[dict[str, Any]]] = {w: [] for w in WATCHLIST_TYPES}

    def add(kind: str, *, reason: str, evidence: Any, priority: str = "normal", status: str = "open") -> None:
        lists[kind].append(
            {
                "reason": reason,
                "evidence": evidence,
                "priority": priority,
                "timestamp": now,
                "status": status,
                "recommendation": None,
                "knowledge_only": True,
            }
        )

    for p in pubs:
        ptype = p.get("publication_type")
        ready = p.get("status") == "institutionally_ready"
        if not ready:
            add(
                "research",
                reason=f"Publication not institutionally ready: {p.get('title')}",
                evidence={"publication_id": p.get("id"), "failures": (p.get("validation") or {}).get("failures")},
                priority="high",
            )
        if ptype == "corporate_events_report":
            add("corporate_events", reason="Morning corporate events report", evidence={"publication_id": p.get("id")})
        if ptype == "macro_intelligence_brief":
            add("macro", reason="Macro brief generated", evidence={"publication_id": p.get("id")})
        if ptype == "government_intelligence_brief":
            add("government", reason="Government brief generated", evidence={"publication_id": p.get("id")})
        if ptype == "alternative_data_report":
            add("alternative_data", reason="Alt-data trends report", evidence={"publication_id": p.get("id")})
        if ptype == "market_expectations_report":
            add("expectation", reason="Expectation changes report", evidence={"publication_id": p.get("id")})
        if ptype in {"sector_intelligence_report", "company_research_note"}:
            add("valuation", reason="Valuation context review (knowledge only)", evidence={"publication_id": p.get("id")})
            add("risk", reason="Risk context follow-up (knowledge only)", evidence={"publication_id": p.get("id")})

    # Soft coverage gaps
    cov = kn.read_coverage()
    if cov.get("unavailable"):
        add(
            "research",
            reason="Coverage dashboard unavailable",
            evidence={"coverage": cov},
            priority="high",
        )

    store.put_watchlists(lists)
    return lists
