"""Production façade — Institutional Confidence Calibration (ICC)."""

from __future__ import annotations

from typing import Any

from institutional_confidence_calibration import store as icc_store
from institutional_confidence_calibration.dashboard.board import build_board
from institutional_confidence_calibration.engine import calibrate
from institutional_confidence_calibration.schema import (
    COMPANY,
    CONFIDENCE_VERSION,
    FREEZE_LOCKS,
    ICC_VERSION,
    MODULE_CODE,
    PROGRAMME,
)


def status() -> dict[str, Any]:
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "version": ICC_VERSION,
        "confidence_version": CONFIDENCE_VERSION,
        "programme": PROGRAMME,
        "status": "ready",
        "freeze_locks": dict(FREEZE_LOCKS),
        "institutional_guarantee": (
            "Confidence is an emergent, deterministic explanation of judgment trustworthiness "
            "from IEW→IHG→IHE→ICR — never a manual label, never raised by an LLM."
        ),
        "api_prefix": "/v1/confidence",
        "observability": "langsmith_mandatory",
        "phase4_complete": True,
        "llm_used": False,
        "manually_assigned": False,
        "fabricated": False,
    }


def dashboard() -> dict[str, Any]:
    return build_board()


def telemetry() -> dict[str, Any]:
    return icc_store.telemetry_snapshot()


def history(limit: int = 20) -> dict[str, Any]:
    return {"n": limit, "runs": icc_store.latest_runs(limit=limit)}


def calculate_api(payload: dict[str, Any]) -> dict[str, Any]:
    out = apply_confidence_calibration(
        question=str(payload.get("question") or ""),
        evidence_weighting=payload.get("evidence_weighting"),
        hypothesis_generation=payload.get("hypothesis_generation"),
        hypothesis_evaluation=payload.get("hypothesis_evaluation"),
        committee_reasoning=payload.get("committee_reasoning"),
        institutional_memory=payload.get("institutional_memory"),
        framework_selection=payload.get("framework_selection"),
        temporal_integrity=payload.get("temporal_integrity"),
        replay_integrity=payload.get("replay_integrity"),
        as_of=payload.get("as_of"),
        metadata=payload.get("metadata") or {},
    )
    pack = out.get("pack") or {}
    pack["_report"] = out.get("report")
    return pack


def report(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    if payload.get("question") or payload.get("hypothesis_evaluation") or payload.get("committee_reasoning"):
        pack = calculate_api(payload)
        return pack.get("report") or {}
    runs = icc_store.latest_runs(limit=1)
    if not runs:
        return {"outcome": "empty", "manually_assigned": False}
    return {
        "overall_confidence": runs[0].get("overall_confidence"),
        "confidence_level": runs[0].get("confidence_level"),
        "confidence_reason": runs[0].get("confidence_reason"),
        "source": "latest_run",
    }


def apply_confidence_calibration(
    *,
    question: str,
    evidence_weighting: dict[str, Any] | None = None,
    hypothesis_generation: dict[str, Any] | None = None,
    hypothesis_evaluation: dict[str, Any] | None = None,
    committee_reasoning: dict[str, Any] | None = None,
    institutional_memory: dict[str, Any] | None = None,
    framework_selection: dict[str, Any] | None = None,
    temporal_integrity: dict[str, Any] | None = None,
    replay_integrity: bool | None = None,
    as_of: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Soft-wire entrypoint after ICR."""
    pack = calibrate(
        question=question,
        evidence_weighting=evidence_weighting,
        hypothesis_generation=hypothesis_generation,
        hypothesis_evaluation=hypothesis_evaluation,
        committee_reasoning=committee_reasoning,
        institutional_memory=institutional_memory,
        framework_selection=framework_selection,
        temporal_integrity=temporal_integrity,
        replay_integrity=replay_integrity,
        as_of=as_of,
        metadata=metadata,
    )
    report_obj = pack.get("report") or {}
    drivers = []
    for item in report_obj.get("why_decreased") or []:
        drivers.append(str(item)[:120])
    for item in report_obj.get("missing_evidence_that_would_raise") or []:
        drivers.append(f"missing:{item}"[:120])

    summary = {
        "question": question,
        "overall_confidence": report_obj.get("overall_confidence"),
        "confidence_level": report_obj.get("confidence_level"),
        "confidence_reason": report_obj.get("confidence_reason"),
        "evidence_quality": report_obj.get("evidence_quality"),
        "coverage_score": report_obj.get("coverage_score"),
        "hypothesis_strength": report_obj.get("hypothesis_strength"),
        "committee_agreement": report_obj.get("committee_agreement"),
        "historical_score": report_obj.get("historical_score"),
        "framework_consistency": report_obj.get("framework_consistency"),
        "missing_evidence_penalty": report_obj.get("missing_evidence_penalty"),
        "penalties": report_obj.get("penalties"),
        "missing_evidence_that_would_raise": report_obj.get("missing_evidence_that_would_raise"),
        "uncertainty_drivers": drivers[:8],
        "temporal_integrity": report_obj.get("temporal_integrity"),
        "replay_integrity": report_obj.get("replay_integrity"),
        "confidence_version": CONFIDENCE_VERSION,
    }
    icc_store.record_run(summary)

    thin_report = {
        "icc_version": ICC_VERSION,
        "confidence_version": CONFIDENCE_VERSION,
        "overall_confidence": report_obj.get("overall_confidence"),
        "confidence_level": report_obj.get("confidence_level"),
        "confidence_reason": report_obj.get("confidence_reason"),
        "penalties": report_obj.get("penalties"),
        "reasoning_changed": False,
        "framework_changed": False,
        "llm_used": False,
        "manually_assigned": False,
    }
    return {"pack": pack, "report": thin_report}
