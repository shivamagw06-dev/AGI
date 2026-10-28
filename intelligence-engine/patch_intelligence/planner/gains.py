"""Estimate expected score gains from fixing a cluster (deterministic heuristic)."""

from __future__ import annotations

from typing import Any


def estimate_gains(
    cluster: dict[str, Any],
    *,
    n_questions: int,
    current_pass_pct: float | None,
    current_framework_pct: float | None,
    current_intent_pct: float | None,
) -> dict[str, Any]:
    """
    Conservative expected gain if cluster is fully fixed.

    Never claims certainty — used for ROI prioritisation only.
    """
    n = max(1, int(n_questions or 1000))
    count = int(cluster.get("count") or 0)
    cause = str(cluster.get("root_cause") or "")
    # Fraction of suite affected
    frac = count / n
    # Framework/intent accuracy gains if that dimension is the root cause
    fw_gain = round(100.0 * frac, 2) if cause == "framework_mismatch" else 0.0
    intent_gain = round(100.0 * frac, 2) if cause == "intent_mismatch" else 0.0
    # Overall pass rate: only hard-fail portion converts; dimension misses convert partially
    # Assume ~35% of cluster members are hard fails that flip to pass
    pass_gain = round(100.0 * frac * 0.35, 2)
    # Cap optimistic gains
    fw_gain = min(fw_gain, 8.0)
    intent_gain = min(intent_gain, 8.0)
    pass_gain = min(pass_gain, 3.0)

    return {
        "affected_questions": count,
        "suite_n": n,
        "framework_accuracy_pp": fw_gain,
        "intent_accuracy_pp": intent_gain,
        "overall_benchmark_pp": pass_gain,
        "projected_framework_accuracy": (
            round(float(current_framework_pct) + fw_gain, 2)
            if current_framework_pct is not None and fw_gain
            else current_framework_pct
        ),
        "projected_intent_accuracy": (
            round(float(current_intent_pct) + intent_gain, 2)
            if current_intent_pct is not None and intent_gain
            else current_intent_pct
        ),
        "projected_pass_pct": (
            round(float(current_pass_pct) + pass_gain, 2)
            if current_pass_pct is not None
            else None
        ),
        "confidence": "low_heuristic",
        "note": "Estimates assume full cluster resolution; validate via IEL re-run.",
    }
