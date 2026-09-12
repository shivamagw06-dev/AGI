"""Ratio & Trend Engine — Module 5 (Ratio Intelligence), Module 9 (Trend
Analysis).

Computes every ratio in the brief for a single period, classifies its
direction across a series (improving / deteriorating / stable), and
attaches the interpretation + warning-sign context from
``metric_concepts``. Every number here is arithmetic on the
``StatementPeriod`` fields — nothing is invented.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from financial_statement_intelligence.metric_concepts import get_metric
from financial_statement_intelligence.schema import FinancialSeries, StatementPeriod


def _safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None or abs(b) < 1e-9:
        return None
    return round(a / b, 4)


def _avg(a: float, b: Optional[float]) -> float:
    return (a + b) / 2 if b is not None else a


# ---------------------------------------------------------------------------
# Single-period ratio calculators. Each takes (current, prior_or_None) and
# returns a value or None if the inputs required are unavailable.
# ---------------------------------------------------------------------------
RatioFn = Callable[[StatementPeriod, Optional[StatementPeriod]], Optional[float]]


def _r_gross_margin(c: StatementPeriod, _p: Optional[StatementPeriod]) -> Optional[float]:
    return _safe_div(c.gross_profit, c.revenue)


def _r_ebitda_margin(c: StatementPeriod, _p: Optional[StatementPeriod]) -> Optional[float]:
    return _safe_div(c.ebitda, c.revenue)


def _r_operating_margin(c: StatementPeriod, _p: Optional[StatementPeriod]) -> Optional[float]:
    return _safe_div(c.ebit, c.revenue)


def _r_net_margin(c: StatementPeriod, _p: Optional[StatementPeriod]) -> Optional[float]:
    return _safe_div(c.pat, c.revenue)


def _r_current_ratio(c: StatementPeriod, _p: Optional[StatementPeriod]) -> Optional[float]:
    return _safe_div(c.current_assets, c.current_liabilities)


def _r_quick_ratio(c: StatementPeriod, _p: Optional[StatementPeriod]) -> Optional[float]:
    return _safe_div(c.current_assets - c.inventory, c.current_liabilities)


def _r_cash_ratio(c: StatementPeriod, _p: Optional[StatementPeriod]) -> Optional[float]:
    return _safe_div(c.cash, c.current_liabilities)


def _r_debt_to_equity(c: StatementPeriod, _p: Optional[StatementPeriod]) -> Optional[float]:
    return _safe_div(c.total_debt, c.total_equity)


def _r_net_debt_to_ebitda(c: StatementPeriod, _p: Optional[StatementPeriod]) -> Optional[float]:
    return _safe_div(c.net_debt, c.ebitda)


def _r_interest_coverage(c: StatementPeriod, _p: Optional[StatementPeriod]) -> Optional[float]:
    return _safe_div(c.ebit, c.interest_expense)


def _r_roe(c: StatementPeriod, p: Optional[StatementPeriod]) -> Optional[float]:
    return _safe_div(c.pat, _avg(c.total_equity, p.total_equity if p else None))


def _r_roa(c: StatementPeriod, p: Optional[StatementPeriod]) -> Optional[float]:
    return _safe_div(c.pat, _avg(c.total_assets, p.total_assets if p else None))


def _r_roce(c: StatementPeriod, _p: Optional[StatementPeriod]) -> Optional[float]:
    return _safe_div(c.ebit, c.total_assets - c.current_liabilities)


def _r_roic(c: StatementPeriod, _p: Optional[StatementPeriod]) -> Optional[float]:
    invested_capital = c.total_debt + c.total_equity - c.cash
    effective_tax_rate = _safe_div(c.tax_expense, c.pbt) or 0.25
    nopat = c.ebit * (1 - effective_tax_rate)
    return _safe_div(nopat, invested_capital)


def _r_asset_turnover(c: StatementPeriod, p: Optional[StatementPeriod]) -> Optional[float]:
    return _safe_div(c.revenue, _avg(c.total_assets, p.total_assets if p else None))


def _r_inventory_turnover(c: StatementPeriod, p: Optional[StatementPeriod]) -> Optional[float]:
    return _safe_div(c.cogs, _avg(c.inventory, p.inventory if p else None))


def _r_receivable_days(c: StatementPeriod, _p: Optional[StatementPeriod]) -> Optional[float]:
    v = _safe_div(c.receivables, c.revenue)
    return round(v * 365, 1) if v is not None else None


def _r_payable_days(c: StatementPeriod, _p: Optional[StatementPeriod]) -> Optional[float]:
    v = _safe_div(c.payables, c.cogs)
    return round(v * 365, 1) if v is not None else None


def _r_inventory_days(c: StatementPeriod, _p: Optional[StatementPeriod]) -> Optional[float]:
    v = _safe_div(c.inventory, c.cogs)
    return round(v * 365, 1) if v is not None else None


def _r_cash_conversion_cycle(c: StatementPeriod, p: Optional[StatementPeriod]) -> Optional[float]:
    rd, idays, pd_ = _r_receivable_days(c, p), _r_inventory_days(c, p), _r_payable_days(c, p)
    if rd is None or idays is None or pd_ is None:
        return None
    return round(rd + idays - pd_, 1)


def _r_free_cash_flow(c: StatementPeriod, _p: Optional[StatementPeriod]) -> Optional[float]:
    return round(c.free_cash_flow, 2)


RATIO_REGISTRY: dict[str, RatioFn] = {
    "gross_margin": _r_gross_margin,
    "ebitda_margin": _r_ebitda_margin,
    "operating_margin": _r_operating_margin,
    "net_margin": _r_net_margin,
    "current_ratio": _r_current_ratio,
    "quick_ratio": _r_quick_ratio,
    "cash_ratio": _r_cash_ratio,
    "debt_to_equity": _r_debt_to_equity,
    "net_debt_to_ebitda": _r_net_debt_to_ebitda,
    "interest_coverage": _r_interest_coverage,
    "roe": _r_roe,
    "roa": _r_roa,
    "roce": _r_roce,
    "roic": _r_roic,
    "asset_turnover": _r_asset_turnover,
    "inventory_turnover": _r_inventory_turnover,
    "receivable_days": _r_receivable_days,
    "payable_days": _r_payable_days,
    "inventory_days": _r_inventory_days,
    "cash_conversion_cycle": _r_cash_conversion_cycle,
    "free_cash_flow": _r_free_cash_flow,
}

# Ratios where a HIGHER value is generally a warning (e.g. leverage, days
# outstanding); everything else treats higher-is-better by default. Used
# only for default trend labelling — real interpretation lives in the
# rule library, which reasons about combinations, not single ratios.
_HIGHER_IS_WARNING = {
    "debt_to_equity", "net_debt_to_ebitda", "receivable_days", "payable_days",
    "inventory_days", "cash_conversion_cycle",
}


def compute_ratios(series: FinancialSeries, *, period_index: int = -1) -> dict[str, Optional[float]]:
    periods = series.periods
    if not periods:
        return {}
    idx = period_index if period_index >= 0 else len(periods) + period_index
    current = periods[idx]
    prior = periods[idx - 1] if idx > 0 else None
    return {key: fn(current, prior) for key, fn in RATIO_REGISTRY.items()}


@dataclass
class RatioTrend:
    key: str
    title: str
    values: list[Optional[float]]
    labels: list[str]
    direction: str  # "improving" | "deteriorating" | "stable" | "insufficient_data"
    interpretation: str
    warning: Optional[str]


def _direction(key: str, values: list[Optional[float]]) -> str:
    clean = [v for v in values if v is not None]
    if len(clean) < 2:
        return "insufficient_data"
    delta = clean[-1] - clean[0]
    if abs(delta) < 1e-6:
        return "stable"
    rising = delta > 0
    is_warning_metric = key in _HIGHER_IS_WARNING
    if rising:
        return "deteriorating" if is_warning_metric else "improving"
    return "improving" if is_warning_metric else "deteriorating"


def ratio_trends(series: FinancialSeries) -> list[RatioTrend]:
    """Module 5 + 9 combined: every ratio's history + trend classification."""
    out: list[RatioTrend] = []
    labels = [p.label for p in series.periods]
    for key in RATIO_REGISTRY:
        values = [compute_ratios(series, period_index=i).get(key) for i in range(len(series.periods))]
        direction = _direction(key, values)
        card = get_metric(key)
        warning = None
        clean = [v for v in values if v is not None]
        if clean and card:
            warning = _warning_for(key, clean[-1])
        out.append(
            RatioTrend(
                key=key,
                title=card.title if card else key,
                values=values,
                labels=labels,
                direction=direction,
                interpretation=card.interpretation if card else "",
                warning=warning,
            )
        )
    return out


_WARNING_THRESHOLDS: dict[str, tuple[str, float]] = {
    "current_ratio": ("below", 1.0),
    "quick_ratio": ("below", 1.0),
    "cash_ratio": ("below", 0.2),
    "debt_to_equity": ("above", 1.5),
    "net_debt_to_ebitda": ("above", 3.5),
    "interest_coverage": ("below", 2.0),
    "cash_conversion_cycle": ("above", 100.0),
}


def _warning_for(key: str, latest: float) -> Optional[str]:
    rule = _WARNING_THRESHOLDS.get(key)
    if not rule:
        return None
    direction, threshold = rule
    if direction == "below" and latest < threshold:
        return f"{key.replace('_', ' ')} of {latest:.2f} is below the {threshold} warning threshold."
    if direction == "above" and latest > threshold:
        return f"{key.replace('_', ' ')} of {latest:.2f} is above the {threshold} warning threshold."
    return None


def cagr(start: Optional[float], end: Optional[float], years: float) -> Optional[float]:
    """Compound annual growth rate. Returns None whenever the metric crosses
    zero/sign between the two points — a CAGR is not meaningfully defined
    for a value that goes from positive to negative (or vice versa); a
    fractional power of a negative ratio yields a complex number, not a
    real growth rate."""
    if start is None or end is None or start <= 0 or end <= 0 or years <= 0:
        return None
    try:
        result = (end / start) ** (1 / years) - 1
        return round(float(result), 4)
    except (ValueError, ZeroDivisionError, OverflowError):
        return None


def growth_metrics(series: FinancialSeries) -> dict[str, Any]:
    """Revenue / EPS / FCF CAGR across the full available window (Module 5)."""
    periods = series.periods
    if len(periods) < 2:
        return {"available": False}
    start, end = periods[0], periods[-1]
    years = max(1, end.sequence - start.sequence)
    return {
        "available": True,
        "years": years,
        "window": [p.label for p in periods],
        "revenue_cagr": cagr(start.revenue, end.revenue, years),
        "eps_cagr": cagr(start.eps, end.eps, years) if start.eps and end.eps else None,
        "fcf_cagr": cagr(start.free_cash_flow, end.free_cash_flow, years),
        "pat_cagr": cagr(start.pat, end.pat, years),
    }
