"""Prior engine — establish institutional prior belief before evidence update."""

from __future__ import annotations

from typing import Any

# Mild type-level prior shrinkage toward institutional base rates
_TYPE_BASE_RATE: dict[str, float] = {
    "Business": 0.58,
    "Financial": 0.55,
    "Valuation": 0.48,
    "Macro": 0.5,
    "Risk": 0.45,
    "Portfolio": 0.5,
    "Competitive": 0.52,
    "Industry": 0.5,
    "Forecast": 0.47,
    "Management": 0.5,
    "Accounting": 0.48,
    "Capital Allocation": 0.5,
}


def _clamp(p: float) -> float:
    return round(max(0.05, min(0.95, float(p))), 4)


def build_prior(hypothesis: dict[str, Any]) -> dict[str, Any]:
    """Blend stated initial confidence with type base rate (conservative prior)."""
    raw = hypothesis.get("initial_confidence")
    if raw is None:
        raw = hypothesis.get("prior_belief") or hypothesis.get("confidence") or 0.55
    raw = float(raw)
    if raw > 1.0:
        raw = raw / 100.0
    base = float(_TYPE_BASE_RATE.get(str(hypothesis.get("type") or "Business"), 0.5))
    # 70% stated prior, 30% type base rate — avoids overconfident starting points
    prior = _clamp(0.7 * raw + 0.3 * base)
    return {
        "prior_belief": prior,
        "stated_confidence": _clamp(raw),
        "type_base_rate": base,
        "shrinkage": 0.3,
        "source": "ihte_or_ihg_with_type_shrinkage",
    }
