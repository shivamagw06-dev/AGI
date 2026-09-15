"""Pure factor mathematics, deliberately independent from storage."""

from __future__ import annotations

import math
import statistics
from typing import Any, Iterable, Optional


def number(value: Any) -> Optional[float]:
    if isinstance(value, bool) or value in (None, ""):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def ratio(numerator: Any, denominator: Any) -> Optional[float]:
    n, d = number(numerator), number(denominator)
    if n is None or d is None or abs(d) <= 1e-9:
        return None
    return n / d


def effective_tax_rate(pbt: Any, pat: Any) -> Optional[float]:
    before, after = number(pbt), number(pat)
    if before is None or after is None or before <= 0:
        return None
    return max(0.0, min(0.50, (before - after) / before))


def nopat(ebit: Any, tax_rate: Any) -> Optional[float]:
    operating_profit, tax = number(ebit), number(tax_rate)
    if operating_profit is None or tax is None:
        return None
    return operating_profit * (1.0 - tax)


def invested_capital(equity: Any, debt: Any, cash: Any) -> Optional[float]:
    eq, borrowings, liquidity = number(equity), number(debt), number(cash)
    if eq is None or borrowings is None or liquidity is None:
        return None
    value = eq + borrowings - liquidity
    return value if value > 0 else None


def free_cash_flow(cfo: Any, capex: Any) -> Optional[float]:
    operating, investment = number(cfo), number(capex)
    if operating is None or investment is None:
        return None
    return operating - abs(investment)


def reinvestment_rate(capex: Any, research_and_development: Any, depreciation: Any, operating_nopat: Any) -> Optional[float]:
    values = [number(v) for v in (capex, research_and_development, depreciation, operating_nopat)]
    if any(v is None for v in values) or abs(values[3]) <= 1e-9:
        return None
    return (abs(values[0]) + values[1] - values[2]) / values[3]


def median(values: Iterable[Any]) -> Optional[float]:
    clean = [v for v in (number(item) for item in values) if v is not None]
    return statistics.median(clean) if clean else None


def change_volatility(values: Iterable[Any]) -> Optional[float]:
    clean = [v for v in (number(item) for item in values) if v is not None]
    changes = [clean[i] - clean[i - 1] for i in range(1, len(clean))]
    return statistics.stdev(changes) if len(changes) >= 2 else None


def volatility(values: Iterable[Any]) -> Optional[float]:
    clean = [v for v in (number(item) for item in values) if v is not None]
    return statistics.stdev(clean) if len(clean) >= 2 else None


def cagr(values: Iterable[Any]) -> Optional[float]:
    clean = [v for v in (number(item) for item in values) if v is not None]
    if len(clean) < 2 or clean[0] <= 0 or clean[-1] <= 0:
        return None
    return (clean[-1] / clean[0]) ** (1.0 / (len(clean) - 1)) - 1.0


def trend(values: Iterable[Any]) -> Optional[float]:
    clean = [v for v in (number(item) for item in values) if v is not None]
    if len(clean) < 2:
        return None
    x_mean = (len(clean) - 1) / 2.0
    denominator = sum((i - x_mean) ** 2 for i in range(len(clean)))
    return sum((i - x_mean) * (value - statistics.mean(clean)) for i, value in enumerate(clean)) / denominator if denominator else None


def percentile_rank(values: Iterable[Any], current: Any) -> Optional[float]:
    clean = [v for v in (number(item) for item in values) if v is not None]
    value = number(current)
    if value is None or not clean:
        return None
    return 100.0 * sum(1 for item in clean if item <= value) / len(clean)


def z_score(values: Iterable[Any], current: Any) -> Optional[float]:
    clean = [v for v in (number(item) for item in values) if v is not None]
    value = number(current)
    if value is None or len(clean) < 2:
        return None
    sigma = statistics.stdev(clean)
    return (value - statistics.mean(clean)) / sigma if sigma > 1e-9 else None


def weighted_score(components: dict[str, Optional[float]], weights: dict[str, float], *, minimum: int = 1) -> Optional[float]:
    available = {key: value for key, value in components.items() if value is not None and key in weights}
    if len(available) < minimum:
        return None
    total_weight = sum(weights[key] for key in available)
    if total_weight <= 0:
        return None
    return sum(available[key] * weights[key] for key in available) / total_weight
