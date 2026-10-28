"""Production façade — Institutional Committee Reasoning (ICR)."""

from __future__ import annotations

from typing import Any

from institutional_committee_reasoning import store as icr_store
from institutional_committee_reasoning.dashboard.board import build_board
from institutional_committee_reasoning.engine import deliberate
from institutional_committee_reasoning.schema import (
    COMMITTEE_VERSION,
    COMPANY,
    FREEZE_LOCKS,
    ICR_VERSION,
    MODULE_CODE,
    PROGRAMME,
)


def status() -> dict[str, Any]:
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "version": ICR_VERSION,
        "committee_version": COMMITTEE_VERSION,
        "programme": PROGRAMME,
        "status": "ready",
        "freeze_locks": dict(FREEZE_LOCKS),
        "institutional_guarantee": (
            "Committee constructs evidence-backed Bull/Base/Bear roles from IHE — "
            "not a voting engine; no fabricated consensus; probabilities are relative support."
        ),
        "api_prefix": "/v1/committee",
        "observability": "langsmith_mandatory",
        "voting_engine": False,
        "fabricated": False,
        "llm_used": False,
    }


def dashboard() -> dict[str, Any]:
    return build_board()


def telemetry() -> dict[str, Any]:
    return icr_store.telemetry_snapshot()


def history(limit: int = 20) -> dict[str, Any]:
    return {"n": limit, "runs": icr_store.latest_runs(limit=limit)}


def deliberate_api(payload: dict[str, Any]) -> dict[str, Any]:
    out = apply_committee_reasoning(
        question=str(payload.get("question") or ""),
        hypothesis_evaluation=payload.get("hypothesis_evaluation")
        or {"evaluated_hypotheses": payload.get("evaluated_hypotheses") or []},
        institutional_memory=payload.get("institutional_memory"),
        framework_selection=payload.get("framework_selection"),
        framework_ids=list(payload.get("framework_ids") or []),
        evidence_weighting=payload.get("evidence_weighting"),
        as_of=payload.get("as_of"),
        metadata=payload.get("metadata") or {},
    )
    pack = out.get("pack") or {}
    pack["_report"] = out.get("report")
    return pack


def report(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    if payload.get("question") or payload.get("hypothesis_evaluation") or payload.get("evaluated_hypotheses"):
        pack = deliberate_api(payload)
        return pack.get("report") or {}
    runs = icr_store.latest_runs(limit=1)
    if not runs:
        return {"outcome": "empty", "voting_engine": False}
    return runs[0].get("report") or {"outcome": runs[0].get("outcome")}


def cases(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    if payload.get("question") or payload.get("hypothesis_evaluation"):
        pack = deliberate_api(payload)
        return {"cases": pack.get("cases"), "probability_distribution": pack.get("probability_distribution")}
    runs = icr_store.latest_runs(limit=1)
    if not runs:
        return {"cases": {}, "source": "empty"}
    return {
        "cases": runs[0].get("cases") or {},
        "probability_distribution": runs[0].get("probability_distribution"),
        "source": "latest_run",
    }


def apply_committee_reasoning(
    *,
    question: str,
    hypothesis_evaluation: dict[str, Any] | None = None,
    institutional_memory: dict[str, Any] | None = None,
    framework_selection: dict[str, Any] | None = None,
    framework_ids: list[str] | None = None,
    evidence_weighting: dict[str, Any] | None = None,
    as_of: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Soft-wire entrypoint after IHE."""
    pack = deliberate(
        question=question,
        hypothesis_evaluation=hypothesis_evaluation,
        institutional_memory=institutional_memory,
        framework_selection=framework_selection,
        framework_ids=framework_ids,
        evidence_weighting=evidence_weighting,
        as_of=as_of,
        metadata=metadata,
    )
    report_obj = pack.get("report") or {}
    cases_obj = pack.get("cases") or {}
    assumptions: list[str] = []
    n_analogues = 0
    for role in ("bull", "base", "bear"):
        c = cases_obj.get(role)
        if not c:
            continue
        assumptions.extend(list(c.get("underlying_assumptions") or [])[:2])
        n_analogues += len(c.get("historical_analogues") or [])

    summary = {
        "question": question,
        "outcome": report_obj.get("outcome"),
        "n_cases": pack.get("n_cases"),
        "has_bull": bool(cases_obj.get("bull")),
        "has_base": bool(cases_obj.get("base")),
        "has_bear": bool(cases_obj.get("bear")),
        "preferred_case": pack.get("preferred_case"),
        "probability_distribution": pack.get("probability_distribution"),
        "confidence": report_obj.get("confidence"),
        "n_disagreements": len(report_obj.get("key_disagreements") or []),
        "n_missing": len(report_obj.get("missing_evidence") or []),
        "n_analogues": n_analogues,
        "dominant_assumptions": assumptions[:6],
        "cases": {
            r: {
                "hypothesis_id": (cases_obj.get(r) or {}).get("hypothesis_id"),
                "probability_pct": (cases_obj.get(r) or {}).get("probability_pct"),
                "confidence": (cases_obj.get(r) or {}).get("confidence"),
            }
            for r in ("bull", "base", "bear")
            if cases_obj.get(r)
        },
        "report": {
            "preferred_case": report_obj.get("preferred_case"),
            "committee_summary": report_obj.get("committee_summary"),
            "probability_distribution": report_obj.get("probability_distribution"),
        },
        "committee_version": COMMITTEE_VERSION,
    }
    icr_store.record_run(summary)

    thin_report = {
        "icr_version": ICR_VERSION,
        "committee_version": COMMITTEE_VERSION,
        "outcome": report_obj.get("outcome"),
        "n_cases": pack.get("n_cases"),
        "preferred_case": pack.get("preferred_case"),
        "probability_sum": pack.get("probability_sum"),
        "voting_engine": False,
        "reasoning_changed": False,
        "framework_changed": False,
        "llm_used": False,
    }
    return {"pack": pack, "report": thin_report}
