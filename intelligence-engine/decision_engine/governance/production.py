"""Assemble IROS governance package for Ask / Decision Engine."""

from __future__ import annotations

from typing import Any

from decision_engine.governance.audit import (
    build_audit_record,
    get_audit_record,
    load_previous_snapshot,
)
from decision_engine.governance.drift import compute_recommendation_delta, compute_thesis_drift
from decision_engine.governance.engine_confidence import build_engine_confidence, rank_critical_missing
from decision_engine.governance.lineage import build_evidence_lineage
from decision_engine.governance.reeval_queue import enqueue_reevaluation, list_reeval_queue
from decision_engine.governance.schema import (
    ARCHITECTURE_STATUS,
    CONSTITUTION_VERSION,
    GOVERNANCE_VERSION,
    PROGRAMME,
)


def package_governance(
    *,
    query: str = "",
    ticker: str | None = None,
    company_name: str | None = None,
    readiness_gate: dict[str, Any] | None = None,
    decision: dict[str, Any] | None = None,
    layers: dict[str, Any] | list[Any] | None = None,
    company_analysis: dict[str, Any] | None = None,
    cid: dict[str, Any] | None = None,
    live_evidence: dict[str, Any] | None = None,
    valuation_pack: dict[str, Any] | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Full governance bundle: lineage, engine confidence, drift, delta, audit, re-eval."""
    gate = readiness_gate if isinstance(readiness_gate, dict) else {}
    decision = decision if isinstance(decision, dict) else {}
    ca = company_analysis if isinstance(company_analysis, dict) else {}
    cid = cid if isinstance(cid, dict) else {}
    leo = live_evidence if isinstance(live_evidence, dict) else {}

    layers_by_id: dict[str, Any]
    if isinstance(layers, dict) and "company_quality" in layers:
        layers_by_id = layers
    elif isinstance(layers, list):
        layers_by_id = {str(r.get("id")): r for r in layers if isinstance(r, dict) and r.get("id")}
    else:
        layers_by_id = {}

    previous = load_previous_snapshot(ticker)
    lineage = build_evidence_lineage(
        readiness_gate=gate,
        company_analysis=ca,
        cid=cid,
        live_evidence=leo,
        valuation_pack=valuation_pack,
    )
    engine_confidence = build_engine_confidence(
        readiness_gate=gate,
        layers=layers_by_id,
        company_analysis=ca,
    )
    critical_missing = rank_critical_missing(readiness_gate=gate)
    thesis_drift = compute_thesis_drift(
        previous=previous,
        current_gate=gate,
        current_decision=decision,
        company_analysis=ca,
    )
    recommendation_delta = compute_recommendation_delta(previous=previous, current_gate=gate)

    price_snapshot = None
    if isinstance(leo.get("quote"), dict):
        price_snapshot = leo["quote"].get("price") or leo["quote"].get("last") or leo["quote"].get("close")
    if price_snapshot is None and isinstance(ca.get("valuation_intelligence"), dict):
        price_snapshot = ca["valuation_intelligence"].get("price")

    audit = None
    reeval = None
    if persist and (ticker or gate):
        audit = build_audit_record(
            ticker=ticker,
            company_name=company_name,
            query=query,
            readiness_gate=gate,
            decision=decision,
            engine_confidence=engine_confidence,
            lineage=lineage,
            thesis_drift=thesis_drift,
            recommendation_delta=recommendation_delta,
            critical_missing=critical_missing,
            price_snapshot=price_snapshot,
            knowledge_snapshot_at=ca.get("generated_at") or leo.get("generated_at"),
        )
        reeval = enqueue_reevaluation(
            ticker=ticker,
            company_name=company_name,
            readiness_gate=gate,
            critical_missing=critical_missing,
            recommendation_id=(audit or {}).get("recommendation_id"),
        )

    return {
        "enabled": True,
        "programme": PROGRAMME,
        "version": GOVERNANCE_VERSION,
        "constitution": CONSTITUTION_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "layers": {
            "evidence": "lineage + critical missing",
            "intelligence": "per-engine confidence",
            "governance": "readiness gate / freshness",
            "decision": "IDE conclusion / withhold",
            "audit": "reproducible recommendation record",
        },
        "evidence_lineage": lineage,
        "engine_confidence": engine_confidence,
        "critical_missing_evidence": critical_missing,
        "thesis_drift": thesis_drift,
        "recommendation_delta": recommendation_delta,
        "audit": audit,
        "reevaluation": reeval,
        "previous_analysis": previous,
        "never_recommend_on_stale_data": True,
        "never_conflate_data_with_quality": True,
        "note": (
            "IROS governance: trust (lineage/confidence), explain (drift/delta/critical missing), "
            "reproduce (audit), heal (re-eval queue)."
        ),
    }


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "version": GOVERNANCE_VERSION,
        "constitution": CONSTITUTION_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
    }


def get_recommendation_audit(recommendation_id: str) -> dict[str, Any] | None:
    return get_audit_record(recommendation_id)


def reevaluation_queue(*, limit: int = 50) -> dict[str, Any]:
    return list_reeval_queue(limit=limit)
