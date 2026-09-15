"""Confidence engine — belief strength in the testing result itself."""

from __future__ import annotations

from typing import Any


def score_result_confidence(
    *,
    support_count: int,
    contradiction_count: int,
    missing_count: int,
    historical_count: int,
    peer_count: int,
    macro_count: int,
    updated_probability: float,
) -> dict[str, Any]:
    # Meta-confidence: how reliable is the test, not the hypothesis probability
    coverage = 0.0
    coverage += min(support_count, 5) / 5 * 0.35
    coverage += min(contradiction_count, 2) / 2 * 0.2
    coverage += min(historical_count, 1) * 0.15
    coverage += min(peer_count, 1) * 0.15
    coverage += min(macro_count, 1) * 0.1
    coverage -= min(missing_count, 3) * 0.04
    coverage = max(0.2, min(0.95, coverage))
    # Slight boost when probability is decisive
    if updated_probability >= 0.75 or updated_probability <= 0.35:
        coverage = min(0.95, coverage + 0.05)
    return {
        "confidence": round(coverage, 4),
        "confidence_pct": round(coverage * 100),
        "interpretation": (
            "High test reliability"
            if coverage >= 0.75
            else "Moderate test reliability"
            if coverage >= 0.55
            else "Low test reliability — expand evidence"
        ),
    }
