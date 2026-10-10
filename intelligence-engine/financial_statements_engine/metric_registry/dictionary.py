"""Seeded canonical metric dictionary — FSE-03 Appendix A + India equity extensions.

This is the only place canonical metric definitions are authored.
Parsers/validators/consumers must query the Metric Registry service.
"""

from __future__ import annotations

from typing import Any

# Appendix A core metrics (authoritative)
_APPENDIX_A: tuple[tuple[str, str, str, str], ...] = (
    # category, metric, statement_type, description
    ("income", "revenue", "income_statement", "Revenue from operations / net sales"),
    ("income", "other_income", "income_statement", "Other income"),
    ("income", "total_income", "income_statement", "Total income"),
    ("income", "cogs", "income_statement", "Cost of goods sold / cost of materials"),
    ("income", "employee_cost", "income_statement", "Employee benefit expense"),
    ("income", "operating_expenses", "income_statement", "Operating expenses (ex-COGS when separated)"),
    ("income", "ebitda", "income_statement", "Earnings before interest, tax, depreciation & amortisation"),
    ("income", "depreciation", "income_statement", "Depreciation and amortisation"),
    ("income", "ebit", "income_statement", "Operating profit / EBIT"),
    ("income", "finance_cost", "income_statement", "Finance costs / interest expense"),
    ("income", "profit_before_tax", "income_statement", "Profit before tax"),
    ("income", "tax_expense", "income_statement", "Tax expense"),
    ("income", "net_income", "income_statement", "Profit after tax / net income"),
    ("income", "eps_basic", "eps", "Basic earnings per share"),
    ("income", "eps_diluted", "eps", "Diluted earnings per share"),
    ("balance", "cash", "balance_sheet", "Cash and cash equivalents"),
    ("balance", "receivables", "balance_sheet", "Trade receivables"),
    ("balance", "inventory", "balance_sheet", "Inventories"),
    ("balance", "current_assets", "balance_sheet", "Total current assets"),
    ("balance", "total_assets", "balance_sheet", "Total assets"),
    ("balance", "current_liabilities", "balance_sheet", "Total current liabilities"),
    ("balance", "total_liabilities", "balance_sheet", "Total liabilities"),
    ("balance", "share_capital", "share_capital", "Equity share capital"),
    ("balance", "retained_earnings", "balance_sheet", "Retained earnings / other equity portion"),
    ("balance", "total_equity", "balance_sheet", "Total equity"),
    ("cash_flow", "operating_cash_flow", "cash_flow", "Net cash from operating activities"),
    ("cash_flow", "investing_cash_flow", "cash_flow", "Net cash from investing activities"),
    ("cash_flow", "financing_cash_flow", "cash_flow", "Net cash from financing activities"),
    ("cash_flow", "free_cash_flow", "cash_flow", "Free cash flow"),
    ("cash_flow", "net_cash_change", "cash_flow", "Net increase/(decrease) in cash"),
)

# Continuity extensions (India listed equities / P2.1 pack coverage)
_EXTENSIONS: tuple[tuple[str, str, str, str], ...] = (
    ("balance", "non_current_assets", "balance_sheet", "Non-current assets"),
    ("balance", "non_current_liabilities", "balance_sheet", "Non-current liabilities"),
    ("balance", "total_debt", "balance_sheet", "Total debt / borrowings"),
    ("balance", "working_capital", "balance_sheet", "Working capital"),
    ("balance", "equity_owners", "balance_sheet", "Equity attributable to owners"),
    ("balance", "reserves", "balance_sheet", "Reserves and surplus / other equity"),
    ("balance", "face_value", "share_capital", "Face value per share"),
    ("balance", "shares_outstanding", "share_capital", "Shares outstanding"),
    ("balance", "deposits", "balance_sheet", "Bank deposits (financials)"),
    ("balance", "investments", "balance_sheet", "Investments"),
    ("capital_structure", "minority_interest", "balance_sheet", "Non-controlling / minority interest"),
    ("capital_structure", "treasury_shares", "share_capital", "Treasury shares"),
    ("cash_flow", "capex", "cash_flow", "Capital expenditure"),
    ("income", "pat_owners", "income_statement", "PAT attributable to owners"),
    ("segment", "segment_revenue", "segment_statement", "Segment revenue"),
    ("segment", "segment_profit", "segment_statement", "Segment profit"),
    ("segment", "segment_assets", "segment_statement", "Segment assets"),
)


def _record(category: str, metric: str, statement_type: str, description: str, *, appendix: bool) -> dict[str, Any]:
    return {
        "metric": metric,
        "category": category,
        "statement_type": statement_type,
        "description": description,
        "kind": "reported",
        "status": "active",
        "replaced_by": None,
        "allowed_scales": ["ones", "thousands", "lakhs", "crores", "millions", "billions"],
        "default_scale": "crores",
        "default_currency": "INR",
        "validation_rule_ids": [],
        "dependencies": [],
        "appendix_a": appendix,
        "unit_rules": {
            "currency_required": True,
            "scale_required": True,
            "consumer_must_not_infer_units": True,
        },
    }


def build_dictionary() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for category, metric, statement_type, description in _APPENDIX_A:
        if metric in out:
            raise ValueError(f"duplicate appendix metric: {metric}")
        out[metric] = _record(category, metric, statement_type, description, appendix=True)
    for category, metric, statement_type, description in _EXTENSIONS:
        if metric in out:
            raise ValueError(f"duplicate extension metric: {metric}")
        out[metric] = _record(category, metric, statement_type, description, appendix=False)
    return out


CANONICAL_METRICS: dict[str, dict[str, Any]] = build_dictionary()

APPENDIX_A_METRICS: tuple[str, ...] = tuple(m for m, r in CANONICAL_METRICS.items() if r.get("appendix_a"))


def metrics_by_category() -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for metric, rec in CANONICAL_METRICS.items():
        grouped.setdefault(str(rec["category"]), []).append(metric)
    for k in grouped:
        grouped[k] = sorted(grouped[k])
    return grouped
