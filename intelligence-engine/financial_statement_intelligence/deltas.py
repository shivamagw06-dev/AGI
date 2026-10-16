"""Period-over-period deltas — the raw material every interpretive rule
in ``rule_library.py`` reasons over.

One function, one source of truth: every % / absolute change quoted
anywhere in Phase 2's output (findings, narrative, red flags) traces
back to ``compute_deltas``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from financial_statement_intelligence.ratio_engine import compute_ratios
from financial_statement_intelligence.schema import StatementPeriod


def _pct(prior: Optional[float], current: Optional[float]) -> Optional[float]:
    if prior is None or current is None or abs(prior) < 1e-9:
        return None
    return round((current - prior) / abs(prior), 4)


@dataclass
class MetricDelta:
    key: str
    prior: Optional[float]
    current: Optional[float]
    abs_change: Optional[float]
    pct_change: Optional[float]


LEVEL_FIELDS: tuple[str, ...] = (
    "revenue", "cogs", "gross_profit", "opex", "ebitda", "depreciation", "ebit",
    "interest_expense", "pbt", "tax_expense", "pat", "eps",
    "cash", "receivables", "inventory", "ppe_net", "intangibles", "goodwill",
    "payables", "total_debt", "total_equity", "total_assets", "share_capital",
    "treasury_stock", "operating_cf", "investing_cf", "financing_cf", "capex",
    "dividends_paid", "buybacks", "short_term_debt", "long_term_debt",
    "lease_liabilities", "total_liabilities", "debt_raised", "debt_repaid",
)

DERIVED_FIELDS: tuple[str, ...] = ("free_cash_flow", "working_capital", "current_liabilities", "net_debt")


def _derived_value(p: StatementPeriod, key: str) -> float:
    if key == "free_cash_flow":
        return p.free_cash_flow
    if key == "working_capital":
        return (p.receivables + p.inventory) - p.payables
    if key == "current_liabilities":
        return p.current_liabilities
    if key == "net_debt":
        return p.net_debt
    raise KeyError(key)


class Deltas:
    """Computed once per (prior, current) pair; cheap dict-like lookups."""

    def __init__(self, prior: StatementPeriod, current: StatementPeriod, prior_ratios: dict, current_ratios: dict):
        self.prior_period = prior
        self.current_period = current
        self._values: dict[str, MetricDelta] = {}
        for field in LEVEL_FIELDS:
            p_val = getattr(prior, field, None)
            c_val = getattr(current, field, None)
            self._values[field] = MetricDelta(
                field, p_val, c_val,
                (c_val - p_val) if (p_val is not None and c_val is not None) else None,
                _pct(p_val, c_val),
            )
        for field in DERIVED_FIELDS:
            p_val = _derived_value(prior, field)
            c_val = _derived_value(current, field)
            self._values[field] = MetricDelta(field, p_val, c_val, c_val - p_val, _pct(p_val, c_val))
        for key, c_val in current_ratios.items():
            p_val = prior_ratios.get(key)
            self._values[f"ratio_{key}"] = MetricDelta(
                f"ratio_{key}", p_val, c_val,
                (c_val - p_val) if (p_val is not None and c_val is not None) else None,
                _pct(p_val, c_val),
            )
        # Effective tax rate — used by several rules independently of ratio_engine.
        p_tax_rate = _pct_ratio(prior.tax_expense, prior.pbt)
        c_tax_rate = _pct_ratio(current.tax_expense, current.pbt)
        self._values["tax_rate"] = MetricDelta(
            "tax_rate", p_tax_rate, c_tax_rate,
            (c_tax_rate - p_tax_rate) if (p_tax_rate is not None and c_tax_rate is not None) else None,
            _pct(p_tax_rate, c_tax_rate),
        )

    def get(self, key: str) -> Optional[MetricDelta]:
        return self._values.get(key)

    def pct(self, key: str) -> Optional[float]:
        d = self._values.get(key)
        return d.pct_change if d else None

    def abs_change(self, key: str) -> Optional[float]:
        d = self._values.get(key)
        return d.abs_change if d else None

    def level(self, key: str, *, current: bool = True) -> Optional[float]:
        d = self._values.get(key)
        if not d:
            return None
        return d.current if current else d.prior

    def keys(self):
        return self._values.keys()


def _pct_ratio(numerator: float, denominator: Optional[float]) -> Optional[float]:
    if denominator is None or abs(denominator) < 1e-9:
        return None
    return round(numerator / denominator, 4)


def compute_deltas(prior: StatementPeriod, current: StatementPeriod) -> Deltas:
    from financial_statement_intelligence.schema import FinancialSeries

    prior_ratios = compute_ratios(FinancialSeries(company="_tmp", periods=[prior]))
    current_ratios = compute_ratios(FinancialSeries(company="_tmp", periods=[prior, current]))
    return Deltas(prior, current, prior_ratios, current_ratios)
