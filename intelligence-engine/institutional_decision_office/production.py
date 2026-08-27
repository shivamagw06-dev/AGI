"""Production façade — Institutional Decision Office (IDO)."""

from __future__ import annotations

from typing import Any

from institutional_decision_office import store as decision_store
from institutional_decision_office.dashboard.board import build_board
from institutional_decision_office.engine import deliberate_decision
from institutional_decision_office.schema import (
    COMPANY,
    DECISION_SCHEMA_VERSION,
    FREEZE_LOCKS,
    IDO_VERSION,
    MODULE_CODE,
    PRODUCT_LINE,
    PROGRAMME,
)


def status() -> dict[str, Any]:
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "product_line": PRODUCT_LINE,
        "version": IDO_VERSION,
        "schema_version": DECISION_SCHEMA_VERSION,
        "programme": PROGRAMME,
        "release": "AGI v4.0",
        "status": "ready",
        "freeze_locks": dict(FREEZE_LOCKS),
        "institutional_guarantee": (
            "IDO separates Analysis from Decision. Emits institutional process decisions "
            "(Wait/Monitor/Increase Research/Reject/Escalate/Approve/Review After …) — "
            "never orders or BUY/SELL execution."
        ),
        "api_prefix": "/v1/decision",
        "observability": "langsmith_mandatory",
        "orders": False,
        "buy_sell": False,
        "execution": False,
        "judgment_stack_modified": False,
        "llm_used": False,
        "fabricated": False,
    }


def dashboard() -> dict[str, Any]:
    return build_board()


def telemetry() -> dict[str, Any]:
    return decision_store.telemetry_snapshot()


def history(limit: int = 20) -> dict[str, Any]:
    return {"n": limit, "recent": decision_store.latest_runs(limit=limit)}


def deliberate_api(payload: dict[str, Any]) -> dict[str, Any]:
    out = apply_decision_office(
        question=str(payload.get("question") or ""),
        investment_thesis=payload.get("investment_thesis") or {"thesis": payload.get("thesis")},
        committee_reasoning=payload.get("committee_reasoning"),
        confidence_calibration=payload.get("confidence_calibration"),
        hypothesis_evaluation=payload.get("hypothesis_evaluation"),
        as_of=payload.get("as_of"),
        metadata=payload.get("metadata") or {},
        persist=True,
    )
    return out.get("pack") or {}


def get_decision(decision_id: str) -> dict[str, Any]:
    doc = decision_store.get(decision_id)
    if not doc:
        return {"found": False, "decision_id": decision_id}
    return {"found": True, "decision": doc}


def list_api(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    rows = decision_store.list_decisions(
        decision=payload.get("decision"),
        status=payload.get("status"),
        thesis_id=payload.get("thesis_id"),
        review_trigger=payload.get("review_trigger"),
        min_confidence=payload.get("min_confidence"),
        limit=int(payload.get("limit") or 50),
    )
    return {"n": len(rows), "decisions": rows, "query": payload}


def versions_api(decision_id: str) -> dict[str, Any]:
    return {"decision_id": decision_id, "versions": decision_store.versions(decision_id)}


def apply_decision_office(
    *,
    question: str,
    investment_thesis: dict[str, Any] | None = None,
    committee_reasoning: dict[str, Any] | None = None,
    confidence_calibration: dict[str, Any] | None = None,
    hypothesis_evaluation: dict[str, Any] | None = None,
    as_of: str | None = None,
    metadata: dict[str, Any] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Soft-wire entrypoint after ITE — consumes thesis + frozen judgment."""
    pack = deliberate_decision(
        question=question,
        investment_thesis=investment_thesis,
        committee_reasoning=committee_reasoning,
        confidence_calibration=confidence_calibration,
        hypothesis_evaluation=hypothesis_evaluation,
        as_of=as_of,
        metadata=metadata,
        persist=persist,
    )
    d = pack.get("decision") or {}
    thin = {
        "ido_version": IDO_VERSION,
        "decision_id": d.get("decision_id"),
        "thesis_id": d.get("thesis_id"),
        "decision": d.get("decision"),
        "status": d.get("status"),
        "review_trigger": d.get("review_trigger"),
        "confidence": d.get("confidence"),
        "version": d.get("version"),
        "orders_emitted": False,
        "buy_sell_emitted": False,
        "reasoning_changed": False,
        "judgment_changed": False,
        "thesis_changed": False,
    }
    return {"pack": pack, "report": thin}
