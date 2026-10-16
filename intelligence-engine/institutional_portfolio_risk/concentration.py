"""PRE-01 concentration engine — deterministic Low/Moderate/High/Critical."""

from __future__ import annotations

from typing import Any, Sequence

from institutional_portfolio.portfolio_entities import ExposureRecord, HoldingRecord
from institutional_portfolio_risk.models import ConcentrationRisk


def _level(*, hhi: float, sector_conc: float, largest: float, top5: float) -> str:
    if hhi >= 0.28 or sector_conc >= 0.85 or largest >= 0.30:
        return "Critical"
    if hhi >= 0.20 or sector_conc >= 0.70 or largest >= 0.25 or top5 >= 0.85:
        return "High"
    if hhi >= 0.12 or sector_conc >= 0.50 or largest >= 0.15:
        return "Moderate"
    return "Low"


def evaluate_concentration(
    holdings: Sequence[HoldingRecord],
    exposures: Sequence[ExposureRecord],
    *,
    cash_weight: float = 0.0,
) -> ConcentrationRisk:
    ordered = sorted(holdings, key=lambda h: float(h.weight or 0.0), reverse=True)
    weights = [float(h.weight or 0.0) for h in ordered]
    hhi = sum(w * w for w in weights)
    # Include cash as a diversifying residual for effective_n only when present
    if cash_weight > 0:
        hhi_with_cash = hhi + float(cash_weight) ** 2
    else:
        hhi_with_cash = hhi
    effective_n = (1.0 / hhi_with_cash) if hhi_with_cash > 0 else 0.0

    largest = ordered[0] if ordered else None
    largest_w = float(largest.weight) if largest else 0.0
    top5 = sum(weights[:5])

    sectors = [e for e in exposures if e.dimension == "sector"]
    if not sectors:
        # Derive from holdings
        buckets: dict[str, float] = {}
        for h in holdings:
            key = (h.sector or "Unknown").strip() or "Unknown"
            buckets[key] = buckets.get(key, 0.0) + float(h.weight or 0.0)
        sectors_sorted = sorted(buckets.items(), key=lambda kv: kv[1], reverse=True)
        top_sector = sectors_sorted[0][0] if sectors_sorted else ""
        sector_conc = float(sectors_sorted[0][1]) if sectors_sorted else 0.0
    else:
        top_sector = sectors[0].name
        sector_conc = float(sectors[0].weight)

    # Theme = industry concentration as proxy for single-theme exposure
    themes: dict[str, float] = {}
    for h in holdings:
        key = (h.industry or h.sector or "Unknown").strip() or "Unknown"
        themes[key] = themes.get(key, 0.0) + float(h.weight or 0.0)
    theme_w = max(themes.values()) if themes else 0.0

    # Diversification score 0–100 (higher = more diversified)
    divers = 100.0
    divers -= min(40.0, hhi * 120.0)
    divers -= min(35.0, max(0.0, sector_conc - 0.35) * 80.0)
    divers -= min(15.0, max(0.0, largest_w - 0.12) * 50.0)
    divers += min(10.0, float(cash_weight) * 40.0)
    divers = max(0.0, min(100.0, divers))

    level = _level(hhi=hhi, sector_conc=sector_conc, largest=largest_w, top5=top5)
    return ConcentrationRisk(
        level=level,
        hhi=round(hhi, 6),
        effective_n=round(effective_n, 4),
        largest_position_ticker=(largest.ticker if largest else ""),
        largest_position_weight=round(largest_w, 6),
        top_5_weight=round(top5, 6),
        sector_concentration=round(sector_conc, 6),
        top_sector=top_sector,
        single_theme_exposure=round(theme_w, 6),
        diversification_score=round(divers, 2),
    )


def concentration_as_dict(
    holdings: Sequence[HoldingRecord],
    exposures: Sequence[ExposureRecord],
    *,
    cash_weight: float = 0.0,
) -> dict[str, Any]:
    return evaluate_concentration(holdings, exposures, cash_weight=cash_weight).to_dict()
