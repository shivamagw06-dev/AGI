"""Strategy lab — compare alternative institutional sleeves."""

from __future__ import annotations

from typing import Any

from simulation_lab.probabilities.engine import run_monte_carlo


def compare_strategies(
    *,
    run_key: str,
    assumptions: dict[str, Any],
    macro_shock: float = 0.0,
) -> dict[str, Any]:
    a = str(assumptions.get("strategy_a") or "high_quality")
    b = str(assumptions.get("strategy_b") or "deep_value")
    c = assumptions.get("strategy_c")
    profiles = {
        "high_quality": {"base_return": 0.09, "base_vol": 0.14, "label": "High Quality"},
        "deep_value": {"base_return": 0.11, "base_vol": 0.22, "label": "Deep Value"},
        "dividend": {"base_return": 0.07, "base_vol": 0.12, "label": "Dividend"},
        "growth": {"base_return": 0.12, "base_vol": 0.24, "label": "Growth"},
        "concentrated": {"base_return": 0.105, "base_vol": 0.26, "label": "Concentrated"},
        "diversified": {"base_return": 0.085, "base_vol": 0.15, "label": "Diversified"},
        "quality_strategy": {"base_return": 0.09, "base_vol": 0.14, "label": "Quality"},
        "value_strategy": {"base_return": 0.11, "base_vol": 0.22, "label": "Value"},
        "growth_strategy": {"base_return": 0.12, "base_vol": 0.24, "label": "Growth"},
        "dividend_strategy": {"base_return": 0.07, "base_vol": 0.12, "label": "Dividend"},
    }

    def _one(name: str) -> dict[str, Any]:
        p = profiles.get(name) or {"base_return": 0.08, "base_vol": 0.18, "label": name}
        dist = run_monte_carlo(
            run_key=f"{run_key}:{name}",
            assumptions=assumptions,
            n=1500,
            base_return=p["base_return"],
            base_vol=p["base_vol"],
            shock=macro_shock,
        )
        return {
            "strategy": name,
            "label": p["label"],
            "expected_return": dist["expected_return"],
            "expected_volatility": dist["expected_volatility"],
            "tail_risk_p05": dist["tail_risk_p05"],
            "distribution": dist["distribution"],
            "bands": dist["bands"],
        }

    strategies = [_one(a), _one(b)]
    if c:
        strategies.append(_one(str(c)))
    # Trade-off narrative without recommendation language
    trade_offs = [
        f"{strategies[0]['label']} offers lower left-tail vs {strategies[1]['label']}"
        if strategies[0]["tail_risk_p05"] > strategies[1]["tail_risk_p05"]
        else f"{strategies[1]['label']} carries more left-tail mass than {strategies[0]['label']}",
        "Opportunity cost is the forgone sleeve distribution, not a single missed ticker",
    ]
    return {
        "strategies": strategies,
        "trade_offs": trade_offs,
        "comparison_complete": True,
        "rule": "Strategy lab compares distributions and trade-offs — committee decides",
    }
