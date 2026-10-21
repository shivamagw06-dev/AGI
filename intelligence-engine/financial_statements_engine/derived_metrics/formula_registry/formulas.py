"""Canonical formula seed — sole definition site for derived metrics.

Expressions use a tiny AST:
  {"div": [a, b]}  {"sub": [a, b]}  {"add": [...]}  {"mul": [a, b]}  {"neg": [a]}
  {"abs": [a]}     literals as numbers; identifiers as metric / fact names.
"""

from __future__ import annotations

from typing import Any

Formula = dict[str, Any]


def _f(
    formula_id: str,
    metric_name: str,
    category: str,
    expression: dict[str, Any],
    required: tuple[str, ...],
    *,
    optional: tuple[str, ...] = (),
    dependencies: tuple[str, ...] = (),
    description: str = "",
    forbid_neg_denom: bool = True,
) -> Formula:
    return {
        "formula_id": formula_id,
        "metric_name": metric_name,
        "version": "1.0.0",
        "category": category,
        "expression": expression,
        "required_inputs": list(required),
        "optional_inputs": list(optional),
        "dependencies": list(dependencies),
        "sector_overrides": {},
        "effective_date": "2016-04-01",
        "status": "active",
        "owner": "fse-07-dme",
        "description": description,
        "forbid_negative_denominator": forbid_neg_denom,
    }


# Intermediate derived metrics first (dependencies), then ratios
FORMULAS: tuple[Formula, ...] = (
    # --- profitability ---
    _f("f.gross_margin.v1", "gross_margin", "profitability", {"div": [{"sub": ["revenue", "cogs"]}, "revenue"]}, ("revenue", "cogs"), description="(Revenue - COGS) / Revenue"),
    _f("f.ebit_margin.v1", "ebit_margin", "profitability", {"div": ["ebit", "revenue"]}, ("ebit", "revenue"), description="EBIT / Revenue"),
    _f("f.ebitda_margin.v1", "ebitda_margin", "profitability", {"div": ["ebitda", "revenue"]}, ("ebitda", "revenue"), description="EBITDA / Revenue"),
    _f("f.operating_margin.v1", "operating_margin", "profitability", {"div": ["ebit", "revenue"]}, ("ebit", "revenue"), description="Operating margin (EBIT/Revenue)"),
    _f("f.net_margin.v1", "net_margin", "profitability", {"div": ["net_income", "revenue"]}, ("net_income", "revenue"), description="Net Income / Revenue"),
    _f("f.roe.v1", "roe", "profitability", {"div": ["net_income", "total_equity"]}, ("net_income", "total_equity"), description="Return on Equity"),
    _f("f.roa.v1", "roa", "profitability", {"div": ["net_income", "total_assets"]}, ("net_income", "total_assets"), description="Return on Assets"),
    _f("f.roce.v1", "roce", "profitability", {"div": ["ebit", {"sub": ["total_assets", "current_liabilities"]}]}, ("ebit", "total_assets", "current_liabilities"), description="EBIT / (Assets - Current Liabilities)"),
    # NOPAT intermediate then ROIC
    _f("f.nopat.v1", "nopat", "profitability", {"mul": ["ebit", {"sub": [1.0, {"div": ["tax_expense", "profit_before_tax"]}]}]}, ("ebit", "tax_expense", "profit_before_tax"), description="EBIT * (1 - effective tax rate)"),
    _f("f.roic.v1", "roic", "profitability", {"div": ["nopat", {"sub": ["total_assets", "current_liabilities"]}]}, ("nopat", "total_assets", "current_liabilities"), dependencies=("nopat",), description="NOPAT / Invested Capital (approx)"),
    # --- efficiency ---
    _f("f.asset_turnover.v1", "asset_turnover", "efficiency", {"div": ["revenue", "total_assets"]}, ("revenue", "total_assets"), description="Revenue / Total Assets"),
    _f("f.inventory_turnover.v1", "inventory_turnover", "efficiency", {"div": ["cogs", "inventory"]}, ("cogs", "inventory"), description="COGS / Inventory"),
    _f("f.receivable_turnover.v1", "receivable_turnover", "efficiency", {"div": ["revenue", "receivables"]}, ("revenue", "receivables"), description="Revenue / Receivables"),
    # --- liquidity ---
    _f("f.current_ratio.v1", "current_ratio", "liquidity", {"div": ["current_assets", "current_liabilities"]}, ("current_assets", "current_liabilities"), description="Current Assets / Current Liabilities"),
    _f("f.quick_ratio.v1", "quick_ratio", "liquidity", {"div": [{"sub": ["current_assets", "inventory"]}, "current_liabilities"]}, ("current_assets", "inventory", "current_liabilities"), description="(CA - Inventory) / CL"),
    _f("f.cash_ratio.v1", "cash_ratio", "liquidity", {"div": ["cash", "current_liabilities"]}, ("cash", "current_liabilities"), description="Cash / Current Liabilities"),
    # --- leverage ---
    _f("f.net_debt.v1", "net_debt", "leverage", {"sub": ["total_debt", "cash"]}, ("total_debt", "cash"), description="Total Debt - Cash", forbid_neg_denom=False),
    _f("f.debt_to_equity.v1", "debt_to_equity", "leverage", {"div": ["total_debt", "total_equity"]}, ("total_debt", "total_equity"), description="Debt / Equity"),
    _f("f.debt_to_ebitda.v1", "debt_to_ebitda", "leverage", {"div": ["total_debt", "ebitda"]}, ("total_debt", "ebitda"), description="Debt / EBITDA"),
    _f("f.interest_coverage.v1", "interest_coverage", "leverage", {"div": ["ebit", "finance_cost"]}, ("ebit", "finance_cost"), description="EBIT / Finance Cost"),
    _f("f.debt_ratio.v1", "debt_ratio", "leverage", {"div": ["total_liabilities", "total_assets"]}, ("total_liabilities", "total_assets"), description="Total Liabilities / Total Assets"),
    # --- cash flow ---
    _f("f.free_cash_flow.v1", "free_cash_flow", "cash_flow", {"sub": ["operating_cash_flow", "capex"]}, ("operating_cash_flow", "capex"), description="OCF - CapEx", forbid_neg_denom=False),
    _f("f.fcf_margin.v1", "fcf_margin", "cash_flow", {"div": ["free_cash_flow", "revenue"]}, ("free_cash_flow", "revenue"), dependencies=("free_cash_flow",), description="FCF / Revenue"),
    _f("f.operating_cash_conversion.v1", "operating_cash_conversion", "cash_flow", {"div": ["operating_cash_flow", "net_income"]}, ("operating_cash_flow", "net_income"), description="OCF / Net Income"),
    _f("f.capex_ratio.v1", "capex_ratio", "cash_flow", {"div": ["capex", "revenue"]}, ("capex", "revenue"), description="CapEx / Revenue"),
    # --- valuation inputs ---
    _f("f.book_value_per_share.v1", "book_value_per_share", "valuation", {"div": ["total_equity", "shares_outstanding"]}, ("total_equity", "shares_outstanding"), description="Equity / Shares"),
    _f("f.eps_basic_pass.v1", "eps_basic_derived", "valuation", {"div": ["net_income", "shares_outstanding"]}, ("net_income", "shares_outstanding"), description="Net Income / Shares (when EPS not reported)"),
    # --- quality / accruals ---
    _f("f.accrual_ratio.v1", "accrual_ratio", "quality", {"div": [{"sub": ["net_income", "operating_cash_flow"]}, "total_assets"]}, ("net_income", "operating_cash_flow", "total_assets"), description="(NI - OCF) / Assets"),
)


def build_registry() -> dict[str, Formula]:
    out: dict[str, Formula] = {}
    by_metric: dict[str, str] = {}
    for f in FORMULAS:
        fid = f["formula_id"]
        if fid in out:
            raise ValueError(f"duplicate_formula_id: {fid}")
        m = f["metric_name"]
        if m in by_metric:
            raise ValueError(f"duplicate_metric_name: {m} ({by_metric[m]} vs {fid})")
        by_metric[m] = fid
        out[fid] = f
    return out
