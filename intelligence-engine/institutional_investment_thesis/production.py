"""Production façade — Institutional Investment Thesis Engine (ITE)."""

from __future__ import annotations

from typing import Any

from institutional_investment_thesis import store as thesis_store
from institutional_investment_thesis.dashboard.board import build_board
from institutional_investment_thesis.engine import construct_thesis
from institutional_investment_thesis.schema import (
    COMPANY,
    FREEZE_LOCKS,
    ITE_VERSION,
    MODULE_CODE,
    PRODUCT_LINE,
    PROGRAMME,
    THESIS_SCHEMA_VERSION,
)


def status() -> dict[str, Any]:
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "product_line": PRODUCT_LINE,
        "version": ITE_VERSION,
        "schema_version": THESIS_SCHEMA_VERSION,
        "programme": PROGRAMME,
        "release": "AGI v4.0",
        "status": "ready",
        "freeze_locks": dict(FREEZE_LOCKS),
        "institutional_guarantee": (
            "ITE persists living Investment Theses from frozen v3.6 judgment packs. "
            "Analysis only — no BUY/SELL. Decision Engine is Sprint 5.2."
        ),
        "api_prefix": "/v1/thesis",
        "observability": "langsmith_mandatory",
        "buy_sell": False,
        "judgment_stack_modified": False,
        "llm_used": False,
        "fabricated": False,
    }


def dashboard() -> dict[str, Any]:
    return build_board()


def telemetry() -> dict[str, Any]:
    return thesis_store.telemetry_snapshot()


def history(limit: int = 20) -> dict[str, Any]:
    return {"n": limit, "recent": thesis_store.latest_runs(limit=limit)}


def create_api(payload: dict[str, Any]) -> dict[str, Any]:
    out = apply_investment_thesis(
        question=str(payload.get("question") or ""),
        company=payload.get("company"),
        ticker=payload.get("ticker"),
        evidence_weighting=payload.get("evidence_weighting"),
        hypothesis_generation=payload.get("hypothesis_generation"),
        hypothesis_evaluation=payload.get("hypothesis_evaluation"),
        committee_reasoning=payload.get("committee_reasoning"),
        confidence_calibration=payload.get("confidence_calibration"),
        institutional_memory=payload.get("institutional_memory"),
        evidence_graph=payload.get("evidence_graph"),
        framework_selection=payload.get("framework_selection"),
        as_of=payload.get("as_of"),
        metadata=payload.get("metadata") or {},
        persist=True,
    )
    return out.get("pack") or {}


def get_thesis(thesis_id: str) -> dict[str, Any]:
    doc = thesis_store.get(thesis_id)
    if not doc:
        return {"found": False, "thesis_id": thesis_id}
    return {"found": True, "thesis": doc}


def list_api(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    rows = thesis_store.list_theses(
        status=payload.get("status"),
        lifecycle=payload.get("lifecycle"),
        decision_status=payload.get("decision_status"),
        min_confidence=payload.get("min_confidence"),
        max_confidence=payload.get("max_confidence"),
        waiting_for=payload.get("waiting_for"),
        confidence_drop_gt=payload.get("confidence_drop_gt"),
        limit=int(payload.get("limit") or 50),
    )
    return {"n": len(rows), "theses": rows, "query": payload}


def versions_api(thesis_id: str) -> dict[str, Any]:
    return {"thesis_id": thesis_id, "versions": thesis_store.versions(thesis_id)}


def apply_investment_thesis(
    *,
    question: str,
    company: str | None = None,
    ticker: str | None = None,
    evidence_weighting: dict[str, Any] | None = None,
    hypothesis_generation: dict[str, Any] | None = None,
    hypothesis_evaluation: dict[str, Any] | None = None,
    committee_reasoning: dict[str, Any] | None = None,
    confidence_calibration: dict[str, Any] | None = None,
    institutional_memory: dict[str, Any] | None = None,
    evidence_graph: dict[str, Any] | None = None,
    framework_selection: dict[str, Any] | None = None,
    as_of: str | None = None,
    metadata: dict[str, Any] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Soft-wire entrypoint after ICC — consumes frozen judgment, persists thesis."""
    pack = construct_thesis(
        question=question,
        company=company,
        ticker=ticker,
        evidence_weighting=evidence_weighting,
        hypothesis_generation=hypothesis_generation,
        hypothesis_evaluation=hypothesis_evaluation,
        committee_reasoning=committee_reasoning,
        confidence_calibration=confidence_calibration,
        institutional_memory=institutional_memory,
        evidence_graph=evidence_graph,
        framework_selection=framework_selection,
        as_of=as_of,
        metadata=metadata,
        persist=persist,
    )
    thesis = pack.get("thesis") or {}
    thin = {
        "ite_version": ITE_VERSION,
        "thesis_id": thesis.get("thesis_id"),
        "company": thesis.get("company"),
        "lifecycle": thesis.get("lifecycle"),
        "decision_status": thesis.get("decision_status"),
        "confidence": thesis.get("confidence"),
        "version": thesis.get("version"),
        "buy_sell_emitted": False,
        "reasoning_changed": False,
        "judgment_changed": False,
    }
    return {"pack": pack, "report": thin}
