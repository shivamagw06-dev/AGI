"""Production façade — Institutional Hypothesis Generation Engine (IHG)."""

from __future__ import annotations

from typing import Any

from institutional_hypothesis_generation import store as ihg_store
from institutional_hypothesis_generation.catalog import active_catalog_id, load_catalog
from institutional_hypothesis_generation.dashboard.board import build_board
from institutional_hypothesis_generation.engine import generate_hypotheses
from institutional_hypothesis_generation.schema import (
    COMPANY,
    FREEZE_LOCKS,
    HYPOTHESIS_VERSION,
    IHG_VERSION,
    MODULE_CODE,
    PROGRAMME,
)


def status() -> dict[str, Any]:
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "version": IHG_VERSION,
        "hypothesis_version": active_catalog_id(),
        "programme": PROGRAMME,
        "status": "ready",
        "freeze_locks": dict(FREEZE_LOCKS),
        "institutional_guarantee": (
            "Analytical questions pass through an evidence-backed Hypothesis Space "
            "before reasoning; no LLM generation; no forced single winner."
        ),
        "api_prefix": "/v1/hypothesis",
        "observability": "langsmith_mandatory",
        "fabricated": False,
        "llm_used": False,
        "forced_single_winner": False,
    }


def dashboard() -> dict[str, Any]:
    return build_board()


def telemetry() -> dict[str, Any]:
    return ihg_store.telemetry_snapshot()


def history(limit: int = 20) -> dict[str, Any]:
    return {"n": limit, "runs": ihg_store.latest_runs(limit=limit)}


def configuration() -> dict[str, Any]:
    cat = load_catalog()
    return {
        "hypothesis_version": active_catalog_id(),
        "catalog_id": cat.get("catalog_id"),
        "version": cat.get("version"),
        "n_families": len(cat.get("families") or []),
        "deterministic": True,
        "llm_used": False,
        "no_forced_single_winner": True,
    }


def generate(payload: dict[str, Any]) -> dict[str, Any]:
    """API: generate hypotheses from question + weighted evidence list."""
    out = apply_hypothesis_generation(
        question=str(payload.get("question") or ""),
        evidence_weighting=payload.get("evidence_weighting")
        or {"weighted_evidence": payload.get("weighted_evidence") or payload.get("evidence") or []},
        framework_ids=list(payload.get("framework_ids") or []),
        intent=payload.get("intent"),
        playbook_id=payload.get("playbook_id") or payload.get("playbook"),
        as_of=payload.get("as_of"),
        weight_version=payload.get("weight_version"),
        catalog_id=payload.get("catalog_id") or payload.get("hypothesis_version"),
        metadata=payload.get("metadata") or {},
    )
    pack = out.get("pack") or {}
    pack["_report"] = out.get("report")
    return pack


def rank(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    if payload.get("question") or payload.get("weighted_evidence") or payload.get("evidence_weighting"):
        pack = generate(payload)
        return {
            "hypotheses": pack.get("hypotheses"),
            "outcome": pack.get("outcome"),
            "winning_hypothesis_ids": pack.get("winning_hypothesis_ids"),
            "plural": pack.get("plural"),
            "forced_single_winner": False,
        }
    runs = ihg_store.latest_runs(limit=1)
    if not runs:
        return {"hypotheses": [], "outcome": "empty", "forced_single_winner": False}
    latest = runs[0]
    return {
        "hypotheses": latest.get("hypotheses") or [],
        "outcome": latest.get("outcome"),
        "winning_hypothesis_ids": latest.get("winning_hypothesis_ids"),
        "plural": latest.get("plural"),
        "source": "latest_run",
        "forced_single_winner": False,
    }


def explain(payload: dict[str, Any]) -> dict[str, Any]:
    pack = generate(payload) if payload.get("question") else rank(payload)
    hyps = pack.get("hypotheses") or []
    hid = payload.get("hypothesis_id")
    chosen = None
    if hid:
        for h in hyps:
            if h.get("hypothesis_id") == hid:
                chosen = h
                break
    if chosen is None and hyps:
        chosen = hyps[0]
    if not chosen:
        return {"explanation": "No hypothesis available", "fabricated": False}
    return {
        "hypothesis_id": chosen.get("hypothesis_id"),
        "hypothesis": chosen.get("hypothesis"),
        "status": chosen.get("status"),
        "share": chosen.get("share"),
        "support_score": chosen.get("support_score"),
        "conflict_score": chosen.get("conflict_score"),
        "overall_score": chosen.get("overall_score"),
        "confidence": chosen.get("confidence"),
        "reason": chosen.get("reason"),
        "supporting_evidence": chosen.get("supporting_evidence"),
        "contradicting_evidence": chosen.get("contradicting_evidence"),
        "citations": chosen.get("citations"),
        "forced_single_winner": False,
        "deterministic": True,
        "llm_used": False,
    }


def apply_hypothesis_generation(
    *,
    question: str,
    evidence_weighting: dict[str, Any] | None = None,
    framework_ids: list[str] | None = None,
    intent: str | None = None,
    playbook_id: str | None = None,
    as_of: str | None = None,
    weight_version: str | None = None,
    catalog_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Soft-wire entrypoint after IEW."""
    iew = evidence_weighting or {}
    weighted = list(iew.get("weighted_evidence") or iew.get("ordered_evidence") or [])
    # ordered_evidence is compact — prefer full weighted_evidence
    pack = generate_hypotheses(
        question=question,
        weighted_evidence=weighted,
        framework_ids=framework_ids,
        intent=intent,
        playbook_id=playbook_id,
        weight_version=weight_version or iew.get("weight_version"),
        catalog_id=catalog_id,
        as_of=as_of,
        metadata=metadata,
    )

    top = (pack.get("hypotheses") or [None])[0] or {}
    summary = {
        "question": question,
        "outcome": pack.get("outcome"),
        "n_hypotheses": pack.get("n_hypotheses"),
        "n_rejected": pack.get("n_rejected") or 0,
        "n_contested": pack.get("n_contested") or 0,
        "average_confidence": pack.get("average_confidence") or top.get("confidence") or 0.0,
        "winning_hypothesis_ids": pack.get("winning_hypothesis_ids"),
        "plural": pack.get("plural"),
        "insufficient_evidence": pack.get("insufficient_evidence"),
        "top_support_score": top.get("support_score"),
        "top_conflict_score": top.get("conflict_score"),
        "hypotheses": [
            {
                "hypothesis_id": h.get("hypothesis_id"),
                "hypothesis": h.get("hypothesis"),
                "status": h.get("status"),
                "share": h.get("share"),
                "overall_score": h.get("overall_score"),
                "confidence": h.get("confidence"),
            }
            for h in (pack.get("hypotheses") or [])
        ],
        "hypothesis_version": pack.get("hypothesis_version") or HYPOTHESIS_VERSION,
    }
    ihg_store.record_run(summary)

    report = {
        "ihg_version": IHG_VERSION,
        "hypothesis_version": pack.get("hypothesis_version"),
        "outcome": pack.get("outcome"),
        "n_hypotheses": pack.get("n_hypotheses"),
        "n_rejected": pack.get("n_rejected"),
        "plural": pack.get("plural"),
        "forced_single_winner": False,
        "insufficient_evidence": pack.get("insufficient_evidence"),
        "winning_hypothesis_ids": pack.get("winning_hypothesis_ids"),
        "reasoning_changed": False,
        "llm_used": False,
    }
    return {"pack": pack, "report": report}
