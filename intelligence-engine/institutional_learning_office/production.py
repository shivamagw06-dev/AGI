"""Production façade — Institutional Learning Office (ILO)."""

from __future__ import annotations

from typing import Any

from institutional_learning_office import store as learning_store
from institutional_learning_office.dashboard.board import build_board
from institutional_learning_office.engine import construct_investment_learning
from institutional_learning_office.schema import (
    COMPANY,
    FREEZE_LOCKS,
    ILO_VERSION,
    LEARNING_CATEGORIES,
    LEARNING_SCHEMA_VERSION,
    MODULE_CODE,
    PRODUCT_LINE,
    PROGRAMME,
)


def status() -> dict[str, Any]:
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "product_line": PRODUCT_LINE,
        "version": ILO_VERSION,
        "schema_version": LEARNING_SCHEMA_VERSION,
        "programme": PROGRAMME,
        "release": "AGI v4.0",
        "status": "ready",
        "final_office_module": True,
        "no_sprint_5_6": True,
        "freeze_locks": dict(FREEZE_LOCKS),
        "institutional_guarantee": (
            "ILO stores InvestmentLearning as process memory. "
            "Does not update Knowledge Factory; does not rewrite thesis/decision/portfolio history."
        ),
        "api_prefix": "/v1/learning",
        "observability": "langsmith_mandatory",
        "categories": list(LEARNING_CATEGORIES),
        "knowledge_factory_updated": False,
        "process_memory": True,
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
    return learning_store.get_learning_store().telemetry_snapshot()


def history(limit: int = 20) -> dict[str, Any]:
    store = learning_store.get_learning_store()
    return {
        "n": limit,
        "recent_runs": store.latest_runs(limit=limit),
        "recent_learnings": store.list_recent(limit=limit),
    }


def create_api(payload: dict[str, Any]) -> dict[str, Any]:
    out = apply_learning_office(
        question=str(payload.get("question") or ""),
        investment_thesis=payload.get("investment_thesis") or {"thesis": payload.get("thesis")},
        decision_office=payload.get("decision_office") or {"decision": payload.get("decision")},
        portfolio_office=payload.get("portfolio_office") or {"idea": payload.get("idea")},
        monitoring_office=payload.get("monitoring_office")
        or {"events": payload.get("events"), "portfolio_idea": payload.get("portfolio_idea")},
        confidence_calibration=payload.get("confidence_calibration"),
        as_of=payload.get("as_of"),
        metadata=payload.get("metadata") or {},
        persist=True,
    )
    return out.get("pack") or {}


def get_learning(learning_id: str) -> dict[str, Any]:
    doc = learning_store.get_learning_store().get(learning_id)
    if not doc:
        return {"found": False, "learning_id": learning_id}
    return {"found": True, "learning": doc}


def list_api(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    store = learning_store.get_learning_store()
    limit = int(payload.get("limit") or 50)
    if payload.get("thesis_id"):
        rows = store.list_for_thesis(str(payload["thesis_id"]), limit=limit)
    elif payload.get("decision_id"):
        rows = store.list_for_decision(str(payload["decision_id"]), limit=limit)
    elif payload.get("portfolio_id") or payload.get("idea_id"):
        rows = store.list_for_portfolio(str(payload.get("portfolio_id") or payload.get("idea_id")), limit=limit)
    elif payload.get("category"):
        rows = store.list_by_category(str(payload["category"]), limit=limit)
    else:
        rows = store.list_recent(limit=limit)
    return {
        "n": len(rows),
        "learnings": rows,
        "query": payload,
        "knowledge_factory_updated": False,
        "process_memory": True,
    }


def apply_learning_office(
    *,
    question: str,
    investment_thesis: dict[str, Any] | None = None,
    decision_office: dict[str, Any] | None = None,
    portfolio_office: dict[str, Any] | None = None,
    monitoring_office: dict[str, Any] | None = None,
    confidence_calibration: dict[str, Any] | None = None,
    as_of: str | None = None,
    metadata: dict[str, Any] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Soft-wire entrypoint after IMO — emits InvestmentLearning process memory."""
    pack = construct_investment_learning(
        question=question,
        investment_thesis=investment_thesis,
        decision_office=decision_office,
        portfolio_office=portfolio_office,
        monitoring_office=monitoring_office,
        confidence_calibration=confidence_calibration,
        as_of=as_of,
        metadata=metadata,
        persist=persist,
    )
    learning = pack.get("learning") or {}
    thin = {
        "ilo_version": ILO_VERSION,
        "learning_id": learning.get("learning_id"),
        "outcome": learning.get("outcome"),
        "category": learning.get("category") or pack.get("category"),
        "root_cause": learning.get("root_cause"),
        "knowledge_factory_updated": False,
        "process_memory": True,
        "mutates_thesis": False,
        "positions_emitted": False,
        "orders_emitted": False,
        "reasoning_changed": False,
        "judgment_changed": False,
    }
    return {"pack": pack, "report": thin}
