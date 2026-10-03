"""Structured failure object constructor."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from root_cause_intelligence.schema import CAUSE_OWNERS, RCI_VERSION


def _severity(root_cause: str, overall: float) -> str:
    if root_cause in {"future_leakage", "fabricated_or_invented", "quality_gate_fail"}:
        return "critical"
    if root_cause in {"framework_mismatch", "intent_mismatch"} and overall < 55:
        return "high"
    if root_cause in {"framework_mismatch", "intent_mismatch", "playbook_mismatch"}:
        return "high"
    if overall < 55:
        return "high"
    if overall < 70:
        return "medium"
    return "low"


def _evidence_missing(expected: list[str], present: dict[str, Any] | None) -> list[str]:
    blob = " ".join(
        str(x)
        for x in (
            (present or {}).get("entities"),
            (present or {}).get("surface_bullets"),
        )
    ).lower()
    missing = []
    for e in expected or []:
        if e and e.lower() not in blob:
            missing.append(e)
    return missing


def build_failure(row: dict[str, Any]) -> dict[str, Any]:
    """Convert one IEL scored failure row into an RCI failure record."""
    causes = list(row.get("root_causes") or ["unspecified"])
    primary = str(causes[0])
    dims = row.get("dimensions") or {}
    overall = float(row.get("overall") or 0.0)
    expected_ev = list(row.get("expected_evidence") or [])
    present = row.get("evidence_present") if isinstance(row.get("evidence_present"), dict) else {}
    missing = _evidence_missing(expected_ev, present)

    # Diagnostic chain for engineers
    chain = [
        "question_failed",
        primary,
    ]
    if "playbook_mismatch" in causes:
        chain.append("wrong_playbook")
    if any(c.startswith("evidence") or c == "empty_evidence_graph" for c in causes):
        chain.append("evidence_incomplete")
    if (row.get("reasoning_path") or {}).get("mode") == "soft":
        chain.append("reasoning_soft_probe_only")
    else:
        path = (row.get("reasoning_path") or {}).get("governance_path")
        chain.append(f"reasoning_path:{path or 'unknown'}")
    comm = row.get("communication") or {}
    if comm.get("template") or row.get("probe_mode") == "soft":
        chain.append("communication_ok_or_not_run")
    chain.append("suggested_fix")

    return {
        "failure_id": f"fail-{uuid4().hex[:12]}",
        "question_id": row.get("question_id"),
        "question": row.get("question"),
        "expected_intent": list(row.get("expected_intent") or []),
        "actual_intent": row.get("actual_intent") or row.get("intent_observed"),
        "expected_framework": list(row.get("expected_framework") or []),
        "actual_framework": list(row.get("actual_framework") or row.get("framework_ids") or []),
        "expected_playbook": list(row.get("expected_playbook") or []),
        "actual_playbook": row.get("actual_playbook") or row.get("playbook_id"),
        "evidence_present": present,
        "evidence_missing": missing,
        "reasoning_path": row.get("reasoning_path") or {},
        "communication": comm,
        "severity": _severity(primary, overall),
        "root_cause": primary,
        "all_root_causes": causes,
        "confidence": round(min(0.95, 0.55 + 0.08 * len(causes)), 2),
        "cluster": None,  # filled by clustering engine
        "category": row.get("category"),
        "sector": row.get("sector"),
        "difficulty": row.get("difficulty"),
        "ticker_hint": row.get("ticker_hint"),
        "overall_score": overall,
        "verdict": row.get("verdict"),
        "dimension_scores": {
            k: (v or {}).get("score") for k, v in dims.items() if isinstance(v, dict)
        },
        "diagnostic_chain": chain,
        "owner": CAUSE_OWNERS.get(primary, "quality_programme"),
        "status": "open",
        "version": RCI_VERSION,
        "fabricated": False,
    }
