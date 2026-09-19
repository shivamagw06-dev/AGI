"""The literal bridge: turn Phase 1 (``financial_foundations``) output
into a Phase 2 ``FinancialSeries``.

Phase 1 proves a company's statements are internally consistent
(accounting equation holds, cash flow reconciles). Phase 2 then reads
those exact numbers as an analyst would — this adapter is what makes
that handoff real instead of aspirational.
"""

from __future__ import annotations

from typing import Any

from financial_statement_intelligence.schema import FinancialSeries, StatementPeriod


def statement_period_from_phase1(statements: dict[str, Any], *, label: str, sequence: int) -> StatementPeriod:
    """Convert one period's ``build_all_statements`` output (Phase 1) into
    a Phase 2 ``StatementPeriod``."""
    is_ = statements["income_statement"]
    bs = statements["balance_sheet"]
    cf = statements["cash_flow_statement"]

    return StatementPeriod(
        label=label,
        sequence=sequence,
        revenue=is_["revenue"],
        cogs=next(l["value"] for l in is_["lines"] if l["key"] == "cogs"),
        gross_profit=is_["gross_profit"],
        opex=next(l["value"] for l in is_["lines"] if l["key"] == "operating_expense"),
        ebitda=is_["ebitda"],
        depreciation=next(l["value"] for l in is_["lines"] if l["key"] == "depreciation"),
        ebit=is_["ebit"],
        interest_expense=next(l["value"] for l in is_["lines"] if l["key"] == "interest"),
        pbt=is_["pbt"],
        tax_expense=next(l["value"] for l in is_["lines"] if l["key"] == "tax"),
        pat=is_["pat"],
        cash=bs["assets"]["current_assets"]["cash"],
        receivables=bs["assets"]["current_assets"]["accounts_receivable"],
        inventory=bs["assets"]["current_assets"]["inventory"],
        ppe_net=bs["assets"]["non_current_assets"]["ppe_net"],
        payables=bs["liabilities"]["current_liabilities"]["accounts_payable"],
        long_term_debt=bs["liabilities"]["long_term_liabilities"]["bank_loan"],
        share_capital=bs["equity"]["share_capital"],
        retained_earnings=bs["equity"]["retained_earnings"],
        operating_cf=cf["operating"]["direct"],
        investing_cf=cf["investing"]["amount"],
        financing_cf=cf["financing"]["amount"],
        meta={
            "phase1_reconciles_to_actual_cash_movement": cf["reconciles_to_actual_cash_movement"],
            "phase1_operating_cf_direct_equals_indirect": cf["operating"]["reconciles"],
            "phase1_accounting_equation_balances": bs["accounting_equation"]["balances"],
        },
    )


def series_from_phase1_ledger(ledger: Any, *, company: str, periods: list[int], sector: str | None = None) -> FinancialSeries:
    """Build a Phase 2 series directly from a live Phase 1 ``Ledger``
    across the given closed periods."""
    from financial_foundations.statement_builder import build_all_statements

    statement_periods = []
    for seq, period in enumerate(sorted(periods), start=1):
        statements = build_all_statements(ledger, period)
        statement_periods.append(
            statement_period_from_phase1(statements, label=f"P{period}", sequence=seq)
        )
    return FinancialSeries(company=company, periods=statement_periods, sector=sector, data_source="financial_foundations_ledger")
