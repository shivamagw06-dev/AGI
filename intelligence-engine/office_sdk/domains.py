"""Application domains — natural homes for offices."""

from __future__ import annotations

from typing import Any

from office_sdk.schema import (
    DOMAIN_EXECUTION,
    DOMAIN_KNOWLEDGE,
    DOMAIN_LABELS,
    DOMAIN_MARKET,
    DOMAIN_PORTFOLIO,
    DOMAIN_RESEARCH,
    DOMAINS,
)

# Planned + live offices by domain (catalog only — not instantiation)
DOMAIN_OFFICES: dict[str, tuple[dict[str, Any], ...]] = {
    DOMAIN_RESEARCH: (
        {
            "office_id": "io-01",
            "workstream_id": "IO-01",
            "name": "Investment Office",
            "status": "live",
            "module": "investment_office.production",
            "role": "single_company_research_orchestration",
        },
        {
            "office_id": "cio-01",
            "workstream_id": "CIO-01",
            "name": "Comparative Intelligence Office",
            "status": "live",
            "module": "comparative_intelligence.production",
            "role": "cross_company_comparison_orchestration",
        },
    ),
    DOMAIN_PORTFOLIO: (
        {
            "office_id": "po-01",
            "workstream_id": "PO-01",
            "name": "Portfolio Office",
            "status": "live",
            "module": "portfolio_office.production",
            "role": "canonical_portfolio_state_no_optimisation",
        },
        {
            "office_id": "wo-01",
            "workstream_id": "WO-01",
            "name": "Watchlist Office",
            "status": "live",
            "module": "watchlist_office.production",
            "role": "research_queue_event_driven_watchlist",
        },
        {
            "office_id": "so-01",
            "workstream_id": "SO-01",
            "name": "Screening Office",
            "status": "planned",
            "module": None,
            "role": "universe_screens_over_fire_io_cio",
        },
        {
            "office_id": "vo-01",
            "workstream_id": "VO-01",
            "name": "Valuation Office",
            "status": "planned",
            "module": None,
            "role": "valuation_context_no_buy_sell",
        },
        {
            "office_id": "ito-01",
            "workstream_id": "ITO-01",
            "name": "Investment Thesis Office",
            "status": "planned",
            "module": None,
            "role": "thesis_assembly_from_evidence",
        },
    ),
    DOMAIN_MARKET: (
        {
            "office_id": "mkt-01",
            "workstream_id": "MKT-01",
            "name": "Market Office",
            "status": "planned",
            "module": None,
            "role": "market_context_orchestration",
        },
        {
            "office_id": "macro-01",
            "workstream_id": "MACRO-01",
            "name": "Macro Office",
            "status": "planned",
            "module": None,
            "role": "macro_context_orchestration",
        },
        {
            "office_id": "news-01",
            "workstream_id": "NEWS-01",
            "name": "News Office",
            "status": "planned",
            "module": None,
            "role": "news_context_orchestration",
        },
    ),
    DOMAIN_EXECUTION: (
        {
            "office_id": "alert-01",
            "workstream_id": "ALERT-01",
            "name": "Alerts Office",
            "status": "planned",
            "module": None,
            "role": "alert_orchestration",
        },
        {
            "office_id": "mon-01",
            "workstream_id": "MON-01",
            "name": "Monitoring Office",
            "status": "planned",
            "module": None,
            "role": "monitoring_orchestration",
        },
        {
            "office_id": "notify-01",
            "workstream_id": "NOTIFY-01",
            "name": "Notification Office",
            "status": "planned",
            "module": None,
            "role": "notification_orchestration",
        },
    ),
    DOMAIN_KNOWLEDGE: (
        {
            "office_id": "notes-01",
            "workstream_id": "NOTES-01",
            "name": "Research Notes",
            "status": "planned",
            "module": None,
            "role": "research_notes_workspace",
        },
        {
            "office_id": "docs-01",
            "workstream_id": "DOCS-01",
            "name": "Documents",
            "status": "planned",
            "module": None,
            "role": "document_workspace",
        },
        {
            "office_id": "session-01",
            "workstream_id": "SESSION-01",
            "name": "Session Desk",
            "status": "planned",
            "module": None,
            "role": "session_desk_workspace",
        },
    ),
}


def list_domains() -> list[dict[str, Any]]:
    out = []
    for domain in DOMAINS:
        offices = list(DOMAIN_OFFICES.get(domain) or ())
        out.append(
            {
                "domain": domain,
                "label": DOMAIN_LABELS.get(domain, domain),
                "office_count": len(offices),
                "live_count": sum(1 for o in offices if o.get("status") == "live"),
                "planned_count": sum(1 for o in offices if o.get("status") == "planned"),
                "offices": offices,
            }
        )
    return out


def offices_for_domain(domain: str) -> list[dict[str, Any]]:
    key = (domain or "").strip().lower()
    return [dict(o) for o in (DOMAIN_OFFICES.get(key) or ())]
