"""Research Office dashboard."""

from __future__ import annotations

from typing import Any

from research_office import store
from research_office.schema import PROGRAMME, RO_VERSION
from research_office.workflows.morning import MORNING_WORKFLOW


def research_dashboard() -> dict[str, Any]:
    pubs = store.list_publications(limit=100)
    today = store.utc_now()[:10]
    todays = [p for p in pubs if str(p.get("created") or "").startswith(today)]
    queue = store.get_queue()
    watchlists = store.get_watchlists()
    status = store.get_status()
    missing = queue.get("todays_missing_evidence") or []
    outstanding = queue.get("todays_follow_ups") or []
    ready_n = sum(1 for p in todays if p.get("status") == "institutionally_ready")
    return {
        "programme": PROGRAMME,
        "version": RO_VERSION,
        "north_star": "morning_research_ready_for_users",
        "status": status,
        "todays_publications": [
            {
                "id": p.get("id"),
                "title": p.get("title"),
                "type": p.get("publication_type"),
                "status": p.get("status"),
                "created": p.get("created"),
            }
            for p in todays
        ],
        "research_queue": queue,
        "watchlists": {k: len(v) for k, v in watchlists.items()},
        "watchlists_detail": watchlists,
        "coverage": queue.get("coverage_snapshot"),
        "outstanding_reviews": outstanding,
        "missing_evidence": missing,
        "validation": {
            "institutionally_ready": ready_n,
            "total_today": len(todays),
            "ready_pct": round(100.0 * ready_n / len(todays), 2) if todays else None,
        },
        "freshness": {
            "last_run_id": status.get("last_run_id"),
            "state": status.get("state"),
        },
        "workflow": MORNING_WORKFLOW,
        "ready_for_users": status.get("ready_for_users"),
        "fabricated": False,
        "knowledge_only": True,
    }
