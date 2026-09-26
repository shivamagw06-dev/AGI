"""Uncertainty engine — quantify residual doubt around the posterior belief."""

from __future__ import annotations

from typing import Any


def build_uncertainty(
    *,
    prior: float,
    posterior: float,
    support_count: int,
    contradiction_count: int,
    missing_count: int,
    tested_uncertainty: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tested_uncertainty = tested_uncertainty or {}
    # Epistemic uncertainty rises with conflict + missingness + large updates
    conflict = abs(support_count - contradiction_count) / max(support_count + contradiction_count, 1)
    conflict_intensity = float(tested_uncertainty.get("conflict_intensity") or (1.0 - conflict))
    if support_count and contradiction_count:
        conflict_intensity = max(conflict_intensity, min(1.0, contradiction_count / support_count))
    missing_u = min(1.0, missing_count / 5.0)
    move_u = min(1.0, abs(posterior - prior) / 0.35)
    # Binary entropy-ish around posterior
    p = min(max(posterior, 1e-6), 1 - 1e-6)
    entropy = -(p * __import__("math").log(p) + (1 - p) * __import__("math").log(1 - p)) / __import__("math").log(2)

    overall = round(min(0.95, 0.25 * conflict_intensity + 0.35 * missing_u + 0.2 * move_u + 0.2 * entropy), 4)
    return {
        "overall_uncertainty": overall,
        "conflict_intensity": round(conflict_intensity, 4),
        "missingness": round(missing_u, 4),
        "update_instability": round(move_u, 4),
        "belief_entropy": round(entropy, 4),
        "known_unknowns": list(tested_uncertainty.get("known_unknowns") or [])[:6],
        "unknown_unknowns": list(tested_uncertainty.get("unknown_unknowns") or [])[:4],
        "missing_evidence": list(tested_uncertainty.get("missing_evidence") or [])[:6],
        "band": "High" if overall >= 0.65 else "Moderate" if overall >= 0.4 else "Low",
    }
