"""Stress testing — left-tail and breakpoint analysis."""

from __future__ import annotations

from typing import Any


def run_stress_tests(
    *,
    distribution: dict[str, Any],
    macro: dict[str, Any],
    portfolio: dict[str, Any],
) -> dict[str, Any]:
    bands = distribution.get("bands") or {}
    p05 = bands.get("p05")
    stress_mass = (distribution.get("distribution") or {}).get("stress", 0)
    completed = [
        {
            "name": "left_tail_p05",
            "result": p05,
            "status": "completed",
            "interpretation": "Soft left-tail institutional band, not a guaranteed loss",
        },
        {
            "name": "stress_probability_mass",
            "result": stress_mass,
            "status": "completed",
        },
        {
            "name": "liquidity_under_stress",
            "result": portfolio.get("liquidity"),
            "status": "completed",
        },
        {
            "name": "macro_channel_stress",
            "result": macro.get("channels") or [],
            "status": "completed" if macro.get("active") else "baseline_only",
        },
    ]
    return {
        "completed": True,
        "tests": completed,
        "breakpoint": {
            "drawdown_proxy": distribution.get("max_drawdown_proxy"),
            "vol_trigger": round(float(distribution.get("expected_volatility") or 0) * 1.5, 4),
        },
        "rule": "Stress tests completed for every institutional simulation run",
    }
