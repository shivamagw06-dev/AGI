"""Compatibility façade over FSE-03 Metric Registry.

Do not add new synonyms or canonical metrics here.
Author changes in ``metric_registry/dictionary.py`` and ``metric_registry/synonyms.py``.
"""

from __future__ import annotations

from typing import Any, Iterable

from financial_statements_engine.metric_registry.dictionary import CANONICAL_METRICS, metrics_by_category
from financial_statements_engine.metric_registry.service import assert_unique_canonical
from financial_statements_engine.metric_registry.service import resolve as _resolve
from financial_statements_engine.metric_registry.service import to_normalized_value
from financial_statements_engine.metric_registry.synonyms import SYNONYMS

_by_cat = metrics_by_category()

INCOME_CANONICAL = tuple(
    m
    for m in (
        "revenue",
        "other_income",
        "total_income",
        "cogs",
        "employee_cost",
        "operating_expenses",
        "ebitda",
        "depreciation",
        "ebit",
        "finance_cost",
        "profit_before_tax",
        "tax_expense",
        "net_income",
        "pat_owners",
        "eps_basic",
        "eps_diluted",
    )
    if m in CANONICAL_METRICS
)
BALANCE_CANONICAL = tuple(
    m
    for m in (
        "total_assets",
        "current_assets",
        "non_current_assets",
        "cash",
        "receivables",
        "inventory",
        "investments",
        "total_equity",
        "share_capital",
        "equity_owners",
        "reserves",
        "retained_earnings",
        "face_value",
        "shares_outstanding",
        "deposits",
        "total_liabilities",
        "current_liabilities",
        "non_current_liabilities",
        "total_debt",
        "working_capital",
        "minority_interest",
        "treasury_shares",
    )
    if m in CANONICAL_METRICS
)
CASHFLOW_CANONICAL = tuple(
    m
    for m in (
        "operating_cash_flow",
        "investing_cash_flow",
        "financing_cash_flow",
        "free_cash_flow",
        "capex",
        "net_cash_change",
    )
    if m in CANONICAL_METRICS
)

UNIT_SCALES = ("ones", "thousands", "lakhs", "crores", "millions", "billions")
UNIT_SCALE_TO_ONES = {
    "ones": 1.0,
    "thousands": 1_000.0,
    "lakhs": 100_000.0,
    "crores": 10_000_000.0,
    "millions": 1_000_000.0,
    "billions": 1_000_000_000.0,
}

# Exposed for any code that imported SYNONYMS from registry
SYNONYMS = SYNONYMS


def all_canonical() -> tuple[str, ...]:
    return tuple(sorted(CANONICAL_METRICS.keys()))


def canonical_set() -> set[str]:
    return set(CANONICAL_METRICS.keys())


def resolve(name: str | None) -> str | None:
    return _resolve(name)


def to_value_inr(reported_value: float | int | None, unit_scale: str | None) -> float | None:
    return to_normalized_value(reported_value, unit_scale)


def registry_manifest() -> dict[str, Any]:
    assert_unique_canonical()
    return {
        "income": list(INCOME_CANONICAL),
        "balance_sheet": list(BALANCE_CANONICAL),
        "cash_flow": list(CASHFLOW_CANONICAL),
        "synonym_count": len(SYNONYMS),
        "canonical_count": len(CANONICAL_METRICS),
        "unit_scales": list(UNIT_SCALES),
        "authority": "metric_registry",
        "categories": _by_cat,
    }
