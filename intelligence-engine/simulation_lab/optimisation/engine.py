"""Lightweight sleeve optimisation hints — exposure balance, not a solver redesign."""

from __future__ import annotations

from typing import Any


def optimisation_notes(*, portfolio: dict[str, Any], strategies: dict[str, Any]) -> dict[str, Any]:
    return {
        "notes": [
            "Balance quality score delta against factor concentration",
            "Prefer liquidity-adequate paths when weight deltas exceed 100 bps",
            "Use strategy comparison distributions before concentrated tilts",
        ],
        "constraints_respected": [
            "no_unsupported_deterministic_outcomes",
            "assumptions_explicit",
            "append_only_history",
        ],
        "portfolio_quality_delta": portfolio.get("quality_score_delta"),
        "strategy_count": len(strategies.get("strategies") or []),
        "rule": "Optimisation notes are soft guidance for committee review",
    }
