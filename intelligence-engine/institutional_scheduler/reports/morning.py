"""Morning reports — knowledge only; no investment recommendations."""

from __future__ import annotations

from typing import Any

from institutional_scheduler import store


def generate_morning_reports(ctx: dict[str, Any]) -> dict[str, Any]:
    results = ctx.get("results") or {}
    completed = ctx.get("completed") or {}
    coverage = ((results.get("coverage_validation") or {}).get("payload") or {})
    daily = ((results.get("daily_health") or {}).get("payload") or {})
    mc = ((results.get("mission_control") or {}).get("payload") or {})
    queue = ((results.get("research_queue") or {}).get("payload") or {})
    gates = ((results.get("quality_gates") or {}).get("payload") or {})

    def _layer(wid: str) -> dict[str, Any]:
        r = results.get(wid) or {}
        return {
            "workflow": wid,
            "status": completed.get(wid) or r.get("status"),
            "retries": r.get("retries"),
            "unavailable": bool(r.get("dataset_unavailable")),
            "error": r.get("error"),
            "recommendation": None,
        }

    reports = {
        "market_morning_brief": {
            "title": "Market Morning Brief",
            "as_of": store.utc_now(),
            "system_state": store.get_status().get("state"),
            "layers": {k: _layer(k) for k in (
                "universe_update",
                "company_intelligence",
                "market_expectations",
            )},
            "recommendation": None,
            "knowledge_only": True,
        },
        "macro_summary": {
            "title": "Macro Summary",
            "source_workflow": "historical_update",
            "status": completed.get("historical_update"),
            "recommendation": None,
            "knowledge_only": True,
        },
        "government_update": {
            "title": "Government Update",
            **_layer("government_intelligence"),
            "knowledge_only": True,
        },
        "corporate_events_summary": {
            "title": "Corporate Events Summary",
            **_layer("corporate_events"),
            "knowledge_only": True,
        },
        "alternative_data_summary": {
            "title": "Alternative Data Summary",
            **_layer("alternative_data"),
            "insufficiency_transparent": True,
            "knowledge_only": True,
        },
        "expectation_changes": {
            "title": "Expectation Changes",
            **_layer("market_expectations"),
            "knowledge_only": True,
        },
        "coverage_report": {
            "title": "Coverage Report",
            "coverage": coverage,
            "recommendation": None,
            "knowledge_only": True,
        },
        "validation_report": {
            "title": "Validation Report",
            "gates": gates,
            "recommendation": None,
            "knowledge_only": True,
        },
        "mission_control_summary": {
            "title": "Mission Control Summary",
            "keys": list(mc.keys())[:40] if isinstance(mc, dict) else [],
            "recommendation": None,
            "knowledge_only": True,
        },
        "research_queue": {
            "title": "Research Queue",
            "queue": queue,
            "recommendation": None,
            "knowledge_only": True,
        },
        "portfolio_watchlist": {
            "title": "Portfolio Watchlist",
            "note": "Knowledge snapshot only — no buy/sell recommendations",
            "items": [],
            "daily_health_keys": list(daily.keys())[:20] if isinstance(daily, dict) else [],
            "recommendation": None,
            "knowledge_only": True,
        },
    }
    return reports
