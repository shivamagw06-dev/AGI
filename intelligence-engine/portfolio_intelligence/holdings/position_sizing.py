"""Position sizing — suitability bands only (never buy/sell instructions)."""

from __future__ import annotations

from typing import Any


def position_sizing(
    *,
    profile: dict[str, Any],
    overlap: dict[str, Any],
    diversification_delta: float,
    risk_delta: float,
    quality_delta: float,
) -> dict[str, Any]:
    limit = float(profile.get("single_name_limit") or 0.12)
    if overlap.get("already_held"):
        suggested = None
        note = "Name already held — sizing evaluates add-on only within single-name limit"
        max_w = limit
        min_w = 0.0
    else:
        base = min(0.06, limit * 0.5)
        if diversification_delta > 0 and quality_delta >= 0:
            base = min(limit * 0.7, base + 0.02)
        if risk_delta > 0.02 or overlap.get("overlap_flag") == "sector_cluster":
            base = max(0.02, base - 0.02)
        suggested = round(base, 4)
        max_w = round(min(limit, suggested + 0.03), 4)
        min_w = round(max(0.01, suggested - 0.02), 4)
        note = "Suggested initial weight is a suitability band — not an order"

    return {
        "minimum_weight": min_w,
        "suggested_initial_weight": suggested,
        "maximum_weight": max_w,
        "maximum_exposure": limit,
        "scaling_strategy": "scale_with_evidence_coverage_and_thesis_conviction",
        "never_buy_sell_instructions": True,
        "note": note,
    }
