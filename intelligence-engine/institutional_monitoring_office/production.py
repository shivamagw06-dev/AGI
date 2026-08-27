"""Production façade — Institutional Monitoring Office (IMO)."""

from __future__ import annotations

from typing import Any

from institutional_monitoring_office import store as event_store
from institutional_monitoring_office.dashboard.board import build_board
from institutional_monitoring_office.engine import run_monitoring_office
from institutional_monitoring_office.schema import (
    COMPANY,
    EVENT_SCHEMA_VERSION,
    FREEZE_LOCKS,
    IMO_VERSION,
    MODULE_CODE,
    MONITOR_DOMAINS,
    PRODUCT_LINE,
    PROGRAMME,
)


def status() -> dict[str, Any]:
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "product_line": PRODUCT_LINE,
        "version": IMO_VERSION,
        "schema_version": EVENT_SCHEMA_VERSION,
        "programme": PROGRAMME,
        "release": "AGI v4.0",
        "status": "ready",
        "freeze_locks": dict(FREEZE_LOCKS),
        "institutional_guarantee": (
            "IMO answers 'What changed?' via MonitoringEvents that recommend review. "
            "Never mutates thesis, decision, portfolio idea, or emits positions/orders."
        ),
        "api_prefix": "/v1/monitoring",
        "observability": "langsmith_mandatory",
        "domains": list(MONITOR_DOMAINS),
        "positions": False,
        "orders": False,
        "execution": False,
        "mutates_thesis": False,
        "judgment_stack_modified": False,
        "llm_used": False,
        "fabricated": False,
    }


def dashboard() -> dict[str, Any]:
    return build_board()


def telemetry() -> dict[str, Any]:
    return event_store.get_monitoring_store().telemetry_snapshot()


def history(limit: int = 20) -> dict[str, Any]:
    store = event_store.get_monitoring_store()
    return {"n": limit, "recent_runs": store.latest_runs(limit=limit), "recent_events": store.list_recent(limit=limit)}


def create_api(payload: dict[str, Any]) -> dict[str, Any]:
    out = apply_monitoring_office(
        question=str(payload.get("question") or ""),
        portfolio_office=payload.get("portfolio_office") or {"idea": payload.get("idea")},
        investment_thesis=payload.get("investment_thesis") or {"thesis": payload.get("thesis")},
        decision_office=payload.get("decision_office") or {"decision": payload.get("decision")},
        confidence_calibration=payload.get("confidence_calibration"),
        hypothesis_evaluation=payload.get("hypothesis_evaluation"),
        committee_reasoning=payload.get("committee_reasoning"),
        as_of=payload.get("as_of"),
        metadata=payload.get("metadata") or {},
        persist=True,
    )
    return out.get("pack") or {}


def get_event(event_id: str) -> dict[str, Any]:
    doc = event_store.get_monitoring_store().get(event_id)
    if not doc:
        return {"found": False, "event_id": event_id}
    return {"found": True, "event": doc}


def list_api(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    store = event_store.get_monitoring_store()
    idea_id = payload.get("portfolio_idea") or payload.get("idea_id")
    thesis_id = payload.get("thesis_id") or payload.get("affected_thesis")
    decision_id = payload.get("decision_id") or payload.get("affected_decision")
    limit = int(payload.get("limit") or 50)
    if idea_id:
        rows = store.list_for_idea(str(idea_id), limit=limit)
    elif thesis_id:
        rows = store.list_for_thesis(str(thesis_id), limit=limit)
    elif decision_id:
        rows = store.list_for_decision(str(decision_id), limit=limit)
    elif payload.get("requires_review"):
        rows = store.list_requiring_review(limit=limit)
    else:
        rows = store.list_recent(limit=limit)
    return {
        "n": len(rows),
        "events": rows,
        "query": payload,
        "mutates_thesis": False,
        "positions": False,
    }


def review_queue_api(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    limit = int(payload.get("limit") or 50)
    rows = event_store.get_monitoring_store().list_requiring_review(limit=limit)
    return {
        "n": len(rows),
        "review_queue": rows,
        "note": "Events recommend review — they do not modify thesis/decision/portfolio",
    }


def apply_monitoring_office(
    *,
    question: str,
    portfolio_office: dict[str, Any] | None = None,
    investment_thesis: dict[str, Any] | None = None,
    decision_office: dict[str, Any] | None = None,
    confidence_calibration: dict[str, Any] | None = None,
    hypothesis_evaluation: dict[str, Any] | None = None,
    committee_reasoning: dict[str, Any] | None = None,
    as_of: str | None = None,
    metadata: dict[str, Any] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Soft-wire entrypoint after IPO — consumes idea/thesis/decision; emits MonitoringEvents."""
    pack = run_monitoring_office(
        question=question,
        portfolio_office=portfolio_office,
        investment_thesis=investment_thesis,
        decision_office=decision_office,
        confidence_calibration=confidence_calibration,
        hypothesis_evaluation=hypothesis_evaluation,
        committee_reasoning=committee_reasoning,
        as_of=as_of,
        metadata=metadata,
        persist=persist,
    )
    thin = {
        "imo_version": IMO_VERSION,
        "portfolio_idea": pack.get("portfolio_idea"),
        "n_events": pack.get("n_events"),
        "requires_review": pack.get("requires_review"),
        "event_ids": pack.get("event_ids"),
        "mutates_thesis": False,
        "mutates_decision": False,
        "mutates_portfolio": False,
        "positions_emitted": False,
        "orders_emitted": False,
        "reasoning_changed": False,
        "judgment_changed": False,
    }
    return {"pack": pack, "report": thin}
