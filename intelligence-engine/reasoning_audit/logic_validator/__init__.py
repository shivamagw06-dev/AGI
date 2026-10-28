"""Logic validation — circularity, unsupported inference, missing steps and inconsistency."""

from __future__ import annotations

from typing import Any


def validate_logic(
    trace: dict[str, Any],
    evidence_trace: dict[str, Any],
) -> dict[str, Any]:
    data = trace["stage_data"]
    thesis = data.get("Investment Thesis") or {}
    decision = data.get("Decision Readiness") or {}
    belief = data.get("Belief Update") or {}
    edges = trace.get("edges") or []

    # The canonical chain must move strictly forward through unique node IDs.
    seen = set()
    circular = False
    for edge in edges:
        if edge["to"] in seen:
            circular = True
        seen.add(edge["from"])

    unsupported = list(evidence_trace.get("orphan_conclusions") or [])
    missing_steps = list(trace.get("missing_stages") or [])
    inconsistencies = []
    thesis_status = str(thesis.get("status") or "")
    decision_status = str(
        decision.get("decision_status")
        or (decision.get("decision_readiness") or {}).get("status")
        or ""
    )
    if thesis_status in ("Broken", "Rejected") and decision_status in (
        "READY",
        "READY WITH CONDITIONS",
    ):
        inconsistencies.append(
            "Broken/rejected thesis cannot be decision-ready"
        )
    beliefs = belief.get("beliefs") or []
    negative_beliefs = sum(
        1
        for b in beliefs
        if b.get("belief_state")
        in ("Challenged", "Contradicted", "Rejected")
    )
    if beliefs and negative_beliefs > len(beliefs) / 2 and thesis_status in (
        "Strong",
        "Very Strong",
    ):
        inconsistencies.append(
            "Strong thesis conflicts with majority-negative beliefs"
        )

    checks = {
        "no_circular_reasoning": not circular,
        "no_unsupported_inference": not unsupported,
        "no_missing_reasoning_step": not missing_steps,
        "no_inconsistent_conclusions": not inconsistencies,
    }
    score = sum(1 for passed in checks.values() if passed) / len(checks)
    return {
        "score": round(score, 4),
        "score_pct": round(score * 100),
        "passed": all(checks.values()),
        "checks": checks,
        "circular_paths": [] if not circular else ["Canonical chain repeats a node"],
        "unsupported_inferences": unsupported,
        "missing_steps": missing_steps,
        "inconsistent_conclusions": inconsistencies,
    }
