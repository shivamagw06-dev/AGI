"""Contextual confidence — sector × regime × horizon.

Soft overlay helper. Never rewrites framework source confidence tables.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.cal.overlays import confidence_for
from institutional_reasoning.cal.regime import detect_regime

CONTEXT_VERSION = "contextual-confidence-v1.0.0"

# Mild dampeners / boosts — never extreme; production must stay conservative.
_SECTOR_ADJ = {
    "it_services": 0.02,
    "banks": -0.01,
    "fmcg": 0.01,
    "energy_conglomerate": -0.02,
    "telecom": -0.02,
    "consumer_internet": -0.03,
}
_REGIME_ADJ = {
    "bull": 0.02,
    "bear": -0.04,
    "crisis": -0.08,
    "recovery": -0.01,
    "high_inflation": -0.03,
    "high_rates": -0.02,
    "low_rates": 0.01,
    "neutral": 0.0,
}
_HORIZON_ADJ = {
    "1m": -0.03,
    "3m": -0.01,
    "6m": 0.0,
    "12m": 0.01,
    "24m": 0.02,
    "36m": 0.01,
}


def contextual_confidence(
    framework_id: str,
    *,
    sector: str | None = None,
    regime: str | None = None,
    horizon: str | None = None,
    market: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base = confidence_for(framework_id, regime=regime)
    detected = detect_regime(market=market, hint=regime)
    reg = str(regime or detected.get("regime") or "neutral").lower()
    sec = str(sector or "").lower()
    hor = str(horizon or "12m").lower()

    adj = (
        _SECTOR_ADJ.get(sec, 0.0)
        + _REGIME_ADJ.get(reg, 0.0)
        + _HORIZON_ADJ.get(hor, 0.0)
    )
    raw = float(base.get("dynamic") or base.get("ies") or 0.7)
    value = round(min(0.95, max(0.35, raw + adj)), 4)

    return {
        "context_version": CONTEXT_VERSION,
        "framework": framework_id,
        "base": base,
        "sector": sec or None,
        "regime": reg,
        "horizon": hor,
        "adjustment": round(adj, 4),
        "value": value,
        "dynamic": value,
        "sector_specific": sec or None,
        "source": "contextual_overlay",
    }
