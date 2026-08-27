"""Module 7 — Regime Detection.

Learning is segmented by market regime — never average everything together.
"""

from __future__ import annotations

from typing import Any

REGIME_VERSION = "regime-detection-v1.0.0"

REGIMES = (
    "bull",
    "bear",
    "high_inflation",
    "low_rates",
    "high_rates",
    "crisis",
    "recovery",
    "neutral",
)


def detect_regime(
    *,
    market: dict[str, Any] | None = None,
    hint: str | None = None,
    macro: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if hint and str(hint).lower() in REGIMES:
        return {
            "regime_version": REGIME_VERSION,
            "regime": str(hint).lower(),
            "source": "hint",
            "confidence": 0.9,
        }

    market = market or {}
    macro = macro or {}
    total = float(market.get("total_return") or 0.0)
    dd = float(market.get("maximum_drawdown") or market.get("max_drawdown") or 0.0)
    vol = float(market.get("volatility") or 0.0)
    inflation = float(macro.get("inflation") or 0.0)
    rates = float(macro.get("policy_rate") or macro.get("rates") or 0.0)

    regime = "neutral"
    reasons: list[str] = []
    if dd >= 0.25 or vol >= 0.40:
        regime = "crisis"
        reasons.append("elevated_drawdown_or_vol")
    elif total <= -0.12:
        regime = "bear"
        reasons.append("negative_realised_return")
    elif total >= 0.12 and dd <= 0.10:
        regime = "bull"
        reasons.append("strong_return_low_dd")
    elif inflation >= 0.06:
        regime = "high_inflation"
        reasons.append("inflation_elevated")
    elif rates >= 0.065:
        regime = "high_rates"
        reasons.append("policy_rate_elevated")
    elif rates > 0 and rates <= 0.035:
        regime = "low_rates"
        reasons.append("policy_rate_low")
    elif total > 0 and dd >= 0.15:
        regime = "recovery"
        reasons.append("positive_return_after_stress")

    return {
        "regime_version": REGIME_VERSION,
        "regime": regime,
        "source": "detected",
        "confidence": 0.7 if reasons else 0.55,
        "reasons": reasons,
        "segment_key": regime,
    }
