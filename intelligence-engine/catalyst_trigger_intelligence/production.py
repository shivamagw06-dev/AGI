"""CTI production façade — Catalyst & Trigger Intelligence (Sprint 9.3)."""

from __future__ import annotations

from typing import Any

from catalyst_trigger_intelligence.catalysts import company_catalysts, market_catalysts, sector_catalysts
from catalyst_trigger_intelligence.evaluation import (
    evaluate_company,
    evaluate_trigger,
    trigger_matrix_report,
)
from catalyst_trigger_intelligence.monitoring import emit_to_imo, monitoring_pack
from catalyst_trigger_intelligence.schema import (
    ARCHITECTURE_STATUS,
    CTI_VERSION,
    FREEZE_LOCKS,
    LANGSMITH_TRACES,
    NO_REDESIGN,
    PRIMARY_QUESTION,
    PROGRAMME,
    PROGRAMME_SHORT,
    TRIGGER_STATES,
)
from catalyst_trigger_intelligence.store import get_store
from catalyst_trigger_intelligence.triggers import build_company_triggers
from catalyst_trigger_intelligence import traces


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": CTI_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "primary_question": PRIMARY_QUESTION,
        "institutional_rule": "We are Base Case unless X happens.",
        "does_not_forecast": True,
        "auto_rewrites_thesis": False,
        "trigger_states": list(TRIGGER_STATES),
        "langsmith_traces": list(LANGSMITH_TRACES),
        "freeze_locks": dict(FREEZE_LOCKS),
        "no_redesign": list(NO_REDESIGN),
        "api_prefix": "/v1",
        "endpoints": [
            "/v1/catalysts/company/{ticker}",
            "/v1/catalysts/sector/{sector}",
            "/v1/catalysts/market",
            "/v1/triggers/company/{ticker}",
            "/v1/triggers/report",
            "/v1/triggers/evaluate",
            "/admin/catalyst-trigger-intelligence",
        ],
    }


def dashboard() -> dict[str, Any]:
    store = get_store()
    # Seed a few institutional names for Mission Control
    for t in ("INFY", "HDFCBANK", "TCS"):
        build_company_triggers(t, persist=True)
    all_triggers = store.list_all(limit=200)
    by_state: dict[str, int] = {}
    for t in all_triggers:
        by_state[str(t.get("state"))] = by_state.get(str(t.get("state")), 0) + 1
    high = [t for t in all_triggers if t.get("priority") in {"Critical", "High"}]
    upcoming = [
        {
            "entity": t.get("entity"),
            "event": t.get("event"),
            "expected_date": t.get("expected_date"),
            "priority": t.get("priority"),
            "state": t.get("state"),
            "impact": t.get("impact_label"),
        }
        for t in high
    ][:20]
    return {
        "programme": PROGRAMME,
        "cti_version": CTI_VERSION,
        "primary_question": PRIMARY_QUESTION,
        "upcoming_catalysts": upcoming,
        "active_triggers": [t for t in all_triggers if t.get("state") == "Watching"][:30],
        "trigger_status_counts": by_state,
        "high_priority_events": high[:20],
        "scenario_impact_rule": "Activations update scenario assessments — never auto-rewrite theses",
        "event_calendar_focus": ["Upcoming earnings", "Budget", "RBI", "Corporate actions", "Catalysts"],
        "langsmith_traces": traces.recent(30),
        "freeze_locks": dict(FREEZE_LOCKS),
        "website_surfaces": ["/admin/catalyst-trigger-intelligence"],
    }


def company_catalysts_api(ticker: str) -> dict[str, Any]:
    return {"enabled": True, "cti_version": CTI_VERSION, **company_catalysts(ticker)}


def sector_catalysts_api(sector: str) -> dict[str, Any]:
    return {"enabled": True, "cti_version": CTI_VERSION, **sector_catalysts(sector)}


def market_catalysts_api() -> dict[str, Any]:
    return {"enabled": True, "cti_version": CTI_VERSION, **market_catalysts()}


def company_triggers_api(ticker: str) -> dict[str, Any]:
    return {"enabled": True, **build_company_triggers(ticker, persist=True)}


def triggers_report_api(ticker: str | None = None) -> dict[str, Any]:
    if ticker:
        build_company_triggers(ticker, persist=True)
    return {"enabled": True, **trigger_matrix_report(ticker)}


def evaluate_api(payload: dict[str, Any]) -> dict[str, Any]:
    ticker = payload.get("ticker") or payload.get("entity")
    if payload.get("trigger_id"):
        return evaluate_trigger(
            str(payload["trigger_id"]),
            observation=payload.get("observation") or {},
            confirm=bool(payload.get("confirm")),
            apply=bool(payload.get("apply")),
        )
    if not ticker:
        return {"enabled": True, "error": "ticker_or_trigger_id_required"}
    return evaluate_company(
        str(ticker),
        observations=payload.get("observations") or {},
        auto_confirm=bool(payload.get("confirm")),
    )


def monitoring_api(ticker: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    if payload.get("emit_imo"):
        return emit_to_imo(ticker, observations=payload.get("observations"))
    return monitoring_pack(ticker, observations=payload.get("observations"))


def admin_page() -> dict[str, Any]:
    return {
        "title": "Catalyst & Trigger Intelligence",
        "programme": PROGRAMME,
        "dashboard": dashboard(),
        "health": health(),
    }
