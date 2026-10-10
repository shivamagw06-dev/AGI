"""Reusable Earnings Quality Score methodology (investor lens)."""

from __future__ import annotations

from typing import Any


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def score_earnings_quality(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Score 0–100 from cash conversion, accruals, revenue quality, one-offs, policy stability.

    Soft, explainable methodology for IIE/EVE/FLE/VE consumers — not a black box.
    """
    p = payload or {}
    # Inputs (defaults = neutral mid-quality)
    cfo = float(p.get("cfo", p.get("operating_cash_flow", 100)))
    ni = float(p.get("net_income", p.get("ni", 100)))
    accruals_ratio = float(p.get("accruals_ratio", abs(ni - cfo) / max(abs(float(p.get("assets", 1000))), 1)))
    revenue_quality = float(p.get("revenue_quality", 0.7))  # 0-1 analyst prior
    one_off_burden = float(p.get("one_off_burden", p.get("exceptionals_pct_ebit", 0.05)))
    policy_stability = float(p.get("policy_stability", 0.75))  # 0-1
    aggressive = bool(p.get("aggressive_accounting", False))
    restated = bool(p.get("restatement", p.get("restated_statements", False)))

    cash_conversion = cfo / ni if abs(ni) > 1e-9 else (1.0 if cfo >= 0 else 0.0)
    cash_score = _clamp(cash_conversion)  # >1 caps at 1
    if cash_conversion < 0:
        cash_score = 0.0
    accrual_score = _clamp(1.0 - accruals_ratio / 0.15)  # 15% accruals/assets ≈ poor
    revenue_score = _clamp(revenue_quality)
    one_off_score = _clamp(1.0 - one_off_burden / 0.25)
    policy_score = _clamp(policy_stability)

    weights = {
        "cash_conversion": 0.30,
        "accrual_quality": 0.25,
        "revenue_quality": 0.20,
        "one_off_burden": 0.15,
        "policy_stability": 0.10,
    }
    components = {
        "cash_conversion": cash_score,
        "accrual_quality": accrual_score,
        "revenue_quality": revenue_score,
        "one_off_burden": one_off_score,
        "policy_stability": policy_score,
    }
    raw = sum(components[k] * weights[k] for k in weights)
    if aggressive:
        raw *= 0.85
    if restated:
        raw *= 0.7
    score = round(100 * _clamp(raw), 1)
    label = "high" if score >= 75 else "moderate" if score >= 55 else "low"

    red_flags = []
    if cash_conversion < 0.8:
        red_flags.append("declining_or_weak_cash_conversion")
    if accruals_ratio > 0.1:
        red_flags.append("elevated_accruals")
    if one_off_burden > 0.15:
        red_flags.append("heavy_exceptionals")
    if restated:
        red_flags.append("restatement")
    if aggressive:
        red_flags.append("aggressive_accounting_flag")

    return {
        "methodology": "Academy Earnings Quality Score v1",
        "score": score,
        "label": label,
        "components": {k: round(v, 4) for k, v in components.items()},
        "weights": weights,
        "inputs": {
            "cash_conversion": round(cash_conversion, 4),
            "accruals_ratio": round(accruals_ratio, 4),
            "revenue_quality": revenue_quality,
            "one_off_burden": one_off_burden,
            "policy_stability": policy_stability,
            "aggressive_accounting": aggressive,
            "restatement": restated,
        },
        "red_flags": red_flags,
        "valuation_guidance": {
            "multiple": "compress" if label == "low" else "neutral" if label == "moderate" else "support",
            "margin_of_safety": "widen" if score < 60 else "standard",
            "forecast_confidence": label,
        },
        "questions_answered": [
            "Are earnings high quality?",
            "Is cash flow supporting profits?",
            "Are financial statements a reliable base for valuation?",
        ],
    }
