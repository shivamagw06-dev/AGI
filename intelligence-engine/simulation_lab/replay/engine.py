"""Historical replay — COVID, GFC, taper, 2022 inflation analogues."""

from __future__ import annotations

from typing import Any

from simulation_lab.probabilities.engine import run_monte_carlo
from simulation_lab.schema import HISTORICAL_REPLAYS

REPLAY_PROFILES = {
    "covid": {"shock": -0.18, "vol": 0.32, "label": "COVID / pandemic risk-off"},
    "lockdowns_2020": {"shock": -0.16, "vol": 0.3, "label": "2020 lockdowns"},
    "gfc": {"shock": -0.22, "vol": 0.35, "label": "Global Financial Crisis"},
    "banking_crisis_2008": {"shock": -0.2, "vol": 0.34, "label": "2008 banking crisis"},
    "taper_tantrum": {"shock": -0.08, "vol": 0.22, "label": "Taper tantrum"},
    "inflation_2022": {"shock": -0.1, "vol": 0.24, "label": "2022 inflation shock"},
}


def available_replays() -> list[str]:
    return list(HISTORICAL_REPLAYS)


def run_replay(
    *,
    run_key: str,
    assumptions: dict[str, Any],
    portfolio_id: str,
) -> dict[str, Any]:
    rid = str(assumptions.get("replay") or assumptions.get("also") or "")
    if rid not in REPLAY_PROFILES:
        for key in HISTORICAL_REPLAYS:
            if key in str(assumptions).lower() or assumptions.get("family") == "replay":
                rid = key if key in REPLAY_PROFILES else rid
                break
    if rid not in REPLAY_PROFILES and assumptions.get("family") == "replay":
        rid = "covid"
    if rid not in REPLAY_PROFILES:
        return {
            "available": True,
            "active": False,
            "replays": available_replays(),
            "rule": "Historical replay available on demand",
        }
    profile = REPLAY_PROFILES[rid]
    dist = run_monte_carlo(
        run_key=f"{run_key}:replay:{rid}",
        assumptions=assumptions,
        n=1800,
        base_return=0.02,
        base_vol=profile["vol"],
        shock=profile["shock"],
    )
    return {
        "available": True,
        "active": True,
        "replay_id": rid,
        "label": profile["label"],
        "portfolio_id": portfolio_id,
        "portfolio_behaviour": {
            "expected_return": dist["expected_return"],
            "expected_volatility": dist["expected_volatility"],
            "tail_risk_p05": dist["tail_risk_p05"],
            "distribution": dist["distribution"],
        },
        "decision_quality_estimate": {
            "liquidity_stress": "elevated",
            "quality_sleeve_resilience": "relative_outperform_in_left_tail",
            "note": "Estimate only — analogue, not identical history",
        },
        "bands": dist["bands"],
        "seed": dist["seed"],
        "reproducible": True,
        "rule": "Historical replay available — behaviour estimated under analogue shocks",
    }
