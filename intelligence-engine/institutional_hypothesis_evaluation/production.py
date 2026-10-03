"""Production façade — Institutional Hypothesis Evaluation Engine (IHE)."""

from __future__ import annotations

from typing import Any

from institutional_hypothesis_evaluation import store as ihe_store
from institutional_hypothesis_evaluation.dashboard.board import build_board
from institutional_hypothesis_evaluation.engine import evaluate_hypotheses
from institutional_hypothesis_evaluation.schema import (
    COMPANY,
    EVALUATION_VERSION,
    FREEZE_LOCKS,
    IHE_VERSION,
    MODULE_CODE,
    PROGRAMME,
)


def status() -> dict[str, Any]:
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "version": IHE_VERSION,
        "evaluation_version": EVALUATION_VERSION,
        "programme": PROGRAMME,
        "status": "ready",
        "freeze_locks": dict(FREEZE_LOCKS),
        "institutional_guarantee": (
            "Hypotheses are evaluated on support, conflict, coverage, history, "
            "framework fit, and missing evidence — without forcing a single winner "
            "or modifying frozen IEW/IHG/reasoning."
        ),
        "api_prefix": "/v1/hypothesis-evaluation",
        "observability": "langsmith_mandatory",
        "fabricated": False,
        "llm_used": False,
        "forced_single_winner": False,
    }


def dashboard() -> dict[str, Any]:
    return build_board()


def telemetry() -> dict[str, Any]:
    return ihe_store.telemetry_snapshot()


def history(limit: int = 20) -> dict[str, Any]:
    return {"n": limit, "runs": ihe_store.latest_runs(limit=limit)}


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    out = apply_hypothesis_evaluation(
        question=str(payload.get("question") or ""),
        hypothesis_generation=payload.get("hypothesis_generation")
        or {"hypotheses": payload.get("hypotheses") or []},
        evidence_weighting=payload.get("evidence_weighting")
        or {"weighted_evidence": payload.get("weighted_evidence") or []},
        institutional_memory=payload.get("institutional_memory"),
        framework_selection=payload.get("framework_selection"),
        framework_ids=list(payload.get("framework_ids") or []),
        playbook_selection=payload.get("playbook_selection") or payload.get("playbook"),
        evidence_graph=payload.get("evidence_graph"),
        as_of=payload.get("as_of"),
        metadata=payload.get("metadata") or {},
    )
    pack = out.get("pack") or {}
    pack["_report"] = out.get("report")
    return pack


def report(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    if payload.get("question") or payload.get("hypotheses") or payload.get("hypothesis_generation"):
        pack = evaluate(payload)
        return pack.get("report") or {}
    runs = ihe_store.latest_runs(limit=1)
    if not runs:
        return {"outcome": "empty", "forced_single_winner": False}
    return runs[0].get("report") or {"outcome": runs[0].get("outcome")}


def ranking(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    if payload.get("question") or payload.get("hypothesis_generation"):
        pack = evaluate(payload)
        return {
            "evaluated_hypotheses": pack.get("evaluated_hypotheses"),
            "outcome": pack.get("outcome"),
            "preferred_hypothesis": (pack.get("report") or {}).get("preferred_hypothesis"),
            "forced_single_winner": False,
        }
    runs = ihe_store.latest_runs(limit=1)
    if not runs:
        return {"evaluated_hypotheses": [], "outcome": "empty"}
    return {
        "evaluated_hypotheses": runs[0].get("evaluated_hypotheses") or [],
        "outcome": runs[0].get("outcome"),
        "source": "latest_run",
        "forced_single_winner": False,
    }


def apply_hypothesis_evaluation(
    *,
    question: str,
    hypothesis_generation: dict[str, Any] | None = None,
    evidence_weighting: dict[str, Any] | None = None,
    institutional_memory: dict[str, Any] | None = None,
    framework_selection: dict[str, Any] | None = None,
    framework_ids: list[str] | None = None,
    playbook_selection: dict[str, Any] | None = None,
    evidence_graph: dict[str, Any] | None = None,
    as_of: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Soft-wire entrypoint after IHG."""
    pack = evaluate_hypotheses(
        question=question,
        hypothesis_generation=hypothesis_generation,
        evidence_weighting=evidence_weighting,
        institutional_memory=institutional_memory,
        framework_selection=framework_selection,
        framework_ids=framework_ids,
        playbook_selection=playbook_selection,
        evidence_graph=evidence_graph,
        as_of=as_of,
        metadata=metadata,
    )

    evaluated = pack.get("evaluated_hypotheses") or []
    confs = [float(h.get("confidence") or 0) for h in evaluated]
    conf_dist = {
        "low": sum(1 for c in confs if c < 0.4),
        "medium": sum(1 for c in confs if 0.4 <= c < 0.7),
        "high": sum(1 for c in confs if c >= 0.7),
    }
    coverages = [float(h.get("coverage_score") or 0) for h in evaluated]
    summary = {
        "question": question,
        "outcome": pack.get("outcome"),
        "n_evaluated": pack.get("n_evaluated"),
        "n_preferred": pack.get("n_preferred"),
        "n_rejected": pack.get("n_rejected"),
        "n_indeterminate": pack.get("n_indeterminate"),
        "average_support": pack.get("average_support"),
        "average_conflict_raw": pack.get("average_conflict_raw"),
        "average_confidence": pack.get("average_confidence"),
        "average_coverage": round(sum(coverages) / len(coverages), 2) if coverages else 0.0,
        "missing_evidence_frequency": pack.get("missing_evidence_frequency"),
        "preferred_ids": [
            h.get("hypothesis_id") for h in evaluated if h.get("status") == "Preferred"
        ],
        "rejected_ids": [
            h.get("hypothesis_id") for h in evaluated if h.get("status") == "Rejected"
        ],
        "confidence_distribution": conf_dist,
        "plural": pack.get("plural"),
        "report": pack.get("report"),
        "evaluated_hypotheses": [
            {
                "hypothesis_id": h.get("hypothesis_id"),
                "status": h.get("status"),
                "evaluation_score": h.get("evaluation_score"),
                "confidence": h.get("confidence"),
            }
            for h in evaluated
        ],
        "evaluation_version": EVALUATION_VERSION,
    }
    ihe_store.record_run(summary)

    report = {
        "ihe_version": IHE_VERSION,
        "evaluation_version": EVALUATION_VERSION,
        "outcome": pack.get("outcome"),
        "n_evaluated": pack.get("n_evaluated"),
        "n_preferred": pack.get("n_preferred"),
        "n_rejected": pack.get("n_rejected"),
        "plural": pack.get("plural"),
        "forced_single_winner": False,
        "preferred_hypothesis_id": ((pack.get("report") or {}).get("preferred_hypothesis") or {}).get(
            "hypothesis_id"
        ),
        "reasoning_changed": False,
        "framework_changed": False,
        "llm_used": False,
    }
    return {"pack": pack, "report": report}
