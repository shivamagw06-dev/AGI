"""Debate scorecard — measure how well AGIB argued with itself."""

from __future__ import annotations

from typing import Any


def build_scorecard(
    positions: list[dict[str, Any]],
    evidence_conflicts: list[dict[str, Any]],
    assumption_conflicts: list[dict[str, Any]],
    minority_report: list[dict[str, Any]],
    consensus: dict[str, Any],
    tournament: dict[str, Any],
) -> dict[str, Any]:
    evidence_quality = round(
        sum(float(c.get("evidence_quality") or 0) for c in evidence_conflicts)
        / max(len(evidence_conflicts), 1)
    )
    assumption_testing = round(min(100, 55 + 10 * len(assumption_conflicts)))
    contradiction_coverage = round(
        min(100, 50 + 5 * len(evidence_conflicts))
    )
    minority_preservation = (
        100 if minority_report and all(m.get("preserved") for m in minority_report) else 0
    )
    consensus_strength = round(float(consensus.get("confidence") or 0) * 100)
    completeness = round(
        min(
            100,
            20
            + 8 * len(positions)
            + 4 * len(assumption_conflicts)
            + 3 * int(tournament.get("round_count") or 0),
        )
    )
    metrics = {
        "evidence_quality": evidence_quality,
        "assumption_testing": assumption_testing,
        "contradiction_coverage": contradiction_coverage,
        "minority_preservation": minority_preservation,
        "consensus_strength": consensus_strength,
        "debate_completeness": completeness,
    }
    overall = round(sum(metrics.values()) / len(metrics))
    return {
        "overall": overall,
        "grade": "Excellent" if overall >= 90 else "Strong" if overall >= 80 else "Adequate" if overall >= 65 else "Weak",
        "metrics": metrics,
        "metric_labels": {
            "evidence_quality": "Evidence Quality",
            "assumption_testing": "Assumption Testing",
            "contradiction_coverage": "Contradiction Coverage",
            "minority_preservation": "Minority Preservation",
            "consensus_strength": "Consensus Strength",
            "debate_completeness": "Debate Completeness",
        },
        "irs_ready": overall >= 75,
    }
