"""Backend calculation engine.

Every derived number is computed here, server-side, from stored raw values.
Nothing is a spreadsheet formula and nothing is computed in the UI, so the
same figure is identical for every consumer and is always traceable to its
inputs.
"""

from __future__ import annotations

import statistics as stats
from typing import Any, Optional

# Metrics where a lower value is the cheaper end of the range.
_LOWER_IS_CHEAPER = frozenset({"pe", "forward_pe", "pb", "ev_ebitda", "ev_sales", "ps"})

# Metrics where a higher value is the better end.
_HIGHER_IS_BETTER = frozenset({"roe", "dividend_yield", "profit_margin"})

RELATIVE_BANDS: tuple[tuple[float, str], ...] = (
    (20.0, "Deep Discount"),
    (40.0, "Discount"),
    (60.0, "Fair"),
    (80.0, "Premium"),
    (100.1, "Rich"),
)


def num(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def upside_pct(target: Any, price: Any) -> Optional[float]:
    """(Target − CMP) ÷ CMP."""
    t, p = num(target), num(price)
    if t is None or not p:
        return None
    return round(((t - p) / p) * 100.0, 2)


def premium_vs(value: Any, benchmark: Any) -> Optional[float]:
    """Percentage premium (+) or discount (−) of a value against a benchmark."""
    v, b = num(value), num(benchmark)
    if v is None or not b:
        return None
    return round(((v / b) - 1.0) * 100.0, 2)


def consensus_spread(high: Any, low: Any, target: Any = None) -> Optional[float]:
    """Absolute high−low spread, or as a percentage of the mean target."""
    h, low_v = num(high), num(low)
    if h is None or low_v is None:
        return None
    spread = h - low_v
    t = num(target)
    if t:
        return round((spread / t) * 100.0, 2)
    return round(spread, 2)


def percentile_of(value: Any, population: list[Any], *, lower_is_cheaper: bool = True) -> Optional[float]:
    """Where this value sits in a population, 0 = cheapest, 100 = richest."""
    v = num(value)
    clean = sorted(x for x in (num(p) for p in population) if x is not None)
    if v is None or len(clean) < 5:
        return None
    below = sum(1 for x in clean if x < v)
    pct = (below / len(clean)) * 100.0
    if not lower_is_cheaper:
        pct = 100.0 - pct
    return round(pct, 1)


def median_of(values: list[Any]) -> Optional[float]:
    clean = [v for v in (num(x) for x in values) if v is not None]
    return round(stats.median(clean), 2) if clean else None


def band_for(score: Optional[float]) -> Optional[str]:
    if score is None:
        return None
    for ceiling, label in RELATIVE_BANDS:
        if score < ceiling:
            return label
    return "Rich"


def relative_valuation_score(
    *,
    sector_percentile: Optional[float],
    historical_percentile: Optional[float] = None,
    consensus_upside: Optional[float] = None,
    roe: Optional[float] = None,
    sector_median_roe: Optional[float] = None,
) -> dict[str, Any]:
    """Descriptive 0–100 position. 0 = deep discount, 100 = rich.

    Never advice: it says where the market has placed the company, not what to
    do about it.
    """
    components: dict[str, float] = {}
    weights: dict[str, float] = {}

    if sector_percentile is not None:
        components["sector_percentile"] = sector_percentile
        weights["sector_percentile"] = 0.45
    if historical_percentile is not None:
        components["historical_percentile"] = historical_percentile
        weights["historical_percentile"] = 0.30

    # Rich consensus upside implies the market is *not* already paying up.
    if consensus_upside is not None:
        capped = max(-50.0, min(100.0, consensus_upside))
        components["consensus"] = round(max(0.0, 100.0 - (capped + 50.0) / 1.5), 1)
        weights["consensus"] = 0.15

    # Superior profitability justifies a higher placement in the range.
    if roe is not None and sector_median_roe:
        rel = premium_vs(roe, sector_median_roe) or 0.0
        components["profitability"] = round(max(0.0, min(100.0, 50.0 + rel / 2.0)), 1)
        weights["profitability"] = 0.10

    if not components:
        return {"score": None, "band": None, "components": {}, "coverage": 0.0}

    total_w = sum(weights.values())
    score = round(sum(components[k] * weights[k] for k in components) / total_w, 1)
    return {
        "score": score,
        "band": band_for(score),
        "components": components,
        "weights": {k: round(v / total_w, 3) for k, v in weights.items()},
        "coverage": round(total_w, 2),
    }


def derive_company(
    row: dict[str, Any],
    consensus: dict[str, Any],
    sector_stats: dict[str, Any],
    industry_population: dict[str, list[Any]],
    primary_metric: str,
) -> dict[str, Any]:
    """All derived fields for one company, recomputed from raw inputs."""
    price = num(row.get("price")) or num(consensus.get("cmp"))
    target = num(consensus.get("target_price"))

    primary_value = num(row.get(primary_metric))
    sector_median = num((sector_stats or {}).get(f"median_{primary_metric}"))
    sector_pct = percentile_of(
        primary_value,
        industry_population.get(primary_metric, []),
        lower_is_cheaper=primary_metric in _LOWER_IS_CHEAPER,
    )

    roe = num(row.get("roe"))
    score = relative_valuation_score(
        sector_percentile=sector_pct,
        consensus_upside=num(consensus.get("upside")),
        roe=roe,
        sector_median_roe=num((sector_stats or {}).get("median_roe")),
    )

    return {
        "upside_pct": upside_pct(target, price) if target and price else num(consensus.get("upside")),
        "consensus_spread_pct": consensus_spread(
            consensus.get("target_high"), consensus.get("target_low"), target
        ),
        "primary_metric": primary_metric,
        "primary_value": primary_value,
        "sector_median": sector_median,
        "premium_vs_sector_pct": premium_vs(primary_value, sector_median),
        "sector_percentile": sector_pct,
        "roe_premium_vs_sector_pct": premium_vs(roe, (sector_stats or {}).get("median_roe")),
        "relative_valuation": score,
        "inputs": {
            "price": price,
            "target_price": target,
            primary_metric: primary_value,
            "roe": roe,
            "sector_median": sector_median,
        },
    }
