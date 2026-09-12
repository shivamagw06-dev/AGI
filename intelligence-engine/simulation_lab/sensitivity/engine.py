"""Sensitivity lab — key drivers and breakpoints."""

from __future__ import annotations

from typing import Any


def sensitivity_analysis(
    *,
    assumptions: dict[str, Any],
    macro: dict[str, Any],
    distribution: dict[str, Any],
) -> dict[str, Any]:
    drivers = []
    if assumptions.get("weight_delta_bps") is not None:
        drivers.append(
            {
                "variable": "weight_delta_bps",
                "sensitivity": "high" if abs(float(assumptions["weight_delta_bps"])) >= 100 else "medium",
                "note": "Portfolio concentration and factor tilt",
            }
        )
    if macro.get("active"):
        drivers.append(
            {
                "variable": macro.get("shock_id"),
                "sensitivity": "high",
                "note": "Macro channel dominates near-term distribution mass",
            }
        )
    if assumptions.get("nim_sensitivity") is not None:
        drivers.append({"variable": "nim_sensitivity", "sensitivity": "high", "note": "Bank sleeve earnings path"})
    if assumptions.get("pass_through") is not None:
        drivers.append({"variable": "pass_through", "sensitivity": "medium", "note": "Margin defence under cost shock"})
    if assumptions.get("horizon_months") is not None:
        drivers.append({"variable": "horizon_months", "sensitivity": "low", "note": "Path timing, not direction"})
    if not drivers:
        drivers = [
            {"variable": "scenario_probability_mass", "sensitivity": "medium", "note": "FIE-linked distribution"},
            {"variable": "evidence_completeness", "sensitivity": "medium", "note": "Missing evidence widens bands"},
        ]
    ranked = sorted(drivers, key=lambda d: {"high": 0, "medium": 1, "low": 2}.get(d["sensitivity"], 3))
    return {
        "most_sensitive": [d for d in ranked if d["sensitivity"] == "high"] or ranked[:1],
        "least_sensitive": [d for d in ranked if d["sensitivity"] == "low"] or ranked[-1:],
        "key_drivers": ranked[:4],
        "scenario_breakpoints": {
            "vol_breakpoint": round(float(distribution.get("expected_volatility") or 0.16) * 1.35, 4),
            "tail_breakpoint": distribution.get("tail_risk_p05"),
        },
        "rule": "Sensitivity identifies drivers — not deterministic tipping points",
    }
