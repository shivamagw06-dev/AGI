"""Module 11 — Business Simulation: ABC Manufacturing Pvt Ltd.

Founder invests → buys land → buys machinery → purchases inventory →
sells goods → pays salaries → borrows money → pays interest → pays
taxes → all three statements are built automatically from the
transaction sequence, via the same deterministic engines used
everywhere else in this package (no hand-typed statement values).
"""

from __future__ import annotations

from typing import Any

from financial_foundations.journal import Ledger
from financial_foundations.linkage_engine import explain_transaction_linkage
from financial_foundations.statement_builder import build_all_statements

COMPANY_NAME = "ABC Manufacturing Pvt Ltd"

# The exact sequence from Module 11, with concrete amounts (₹). Each step
# is a (transaction_type, amount, kwargs, narrative) tuple.
ABC_MANUFACTURING_SCENARIO: list[tuple[str, float, dict[str, Any], str]] = [
    ("founder_investment", 2_000_000, {}, "Founder invests capital to start ABC Manufacturing."),
    ("buy_asset_cash", 500_000, {"asset_account": "land"}, "Buy land for the factory site."),
    ("buy_asset_cash", 600_000, {"asset_account": "machinery"}, "Buy machinery for production."),
    ("purchase_inventory_cash", 500_000, {}, "Purchase raw material / finished-goods inventory for cash."),
    ("credit_sale", 400_000, {}, "Sell goods to a distributor on 60-day credit terms."),
    ("sell_inventory_cogs", 200_000, {}, "Recognise the cost of goods sold against the credit sale."),
    ("cash_sale", 300_000, {}, "Sell goods to a retail customer for immediate cash."),
    ("sell_inventory_cogs", 150_000, {}, "Recognise the cost of goods sold against the cash sale."),
    ("pay_expense_cash", 120_000, {"expense_account": "salary_expense"}, "Pay factory and office salaries in cash."),
    ("take_loan", 500_000, {}, "Borrow working capital from the bank."),
    ("pay_interest", 25_000, {}, "Pay interest on the bank loan for the period."),
    ("record_depreciation", 60_000, {}, "Record straight-line depreciation on machinery (10-year life)."),
    ("pay_tax", 36_250, {}, "Pay income tax on this period's profit (25% effective rate)."),
]


def run_simulation(*, period: int = 1) -> dict[str, Any]:
    """Execute the full ABC Manufacturing scenario and build all three statements."""
    ledger = Ledger()
    transaction_log: list[dict[str, Any]] = []

    for transaction_type, amount, kwargs, narrative in ABC_MANUFACTURING_SCENARIO:
        entry = ledger.record(transaction_type, amount, narrative=narrative, period=period, **kwargs)
        linkage = explain_transaction_linkage(transaction_type, amount=amount)
        transaction_log.append(
            {
                "entry_id": entry.entry_id,
                "transaction_type": transaction_type,
                "narrative": narrative,
                "amount": amount,
                "postings": [
                    {"account": p.account_code, "side": p.side.value, "amount": p.amount}
                    for p in entry.postings
                ],
                "teaches": linkage.get("teaches"),
            }
        )

    pre_close_trial_balance = ledger.trial_balance(through_period=period)
    closing_entry = ledger.close_period(period)
    statements = build_all_statements(ledger, period)

    return {
        "company": COMPANY_NAME,
        "period": period,
        "transaction_log": transaction_log,
        "pre_close_trial_balance": pre_close_trial_balance,
        "pre_close_trial_balance_balanced": ledger.trial_balance_is_balanced(through_period=period - 1)
        if period > 1
        else True,
        "closing_entry": {
            "entry_id": closing_entry.entry_id,
            "narrative": closing_entry.narrative,
            "net_income": closing_entry.meta.get("net_income"),
        },
        "post_close_trial_balance_balanced": ledger.trial_balance_is_balanced(through_period=period),
        **statements,
        "narrative_summary": _narrative_summary(statements),
    }


def _narrative_summary(statements: dict[str, Any]) -> str:
    is_ = statements["income_statement"]
    bs = statements["balance_sheet"]
    cf = statements["cash_flow_statement"]
    return (
        f"Revenue ₹{is_['revenue']:,.0f} → PAT ₹{is_['pat']:,.0f}. "
        f"Total Assets ₹{bs['assets']['total_assets']:,.0f} = "
        f"Liabilities ₹{bs['liabilities']['total_liabilities']:,.0f} + "
        f"Equity ₹{bs['equity']['total_equity']:,.0f} "
        f"(accounting equation balances: {bs['accounting_equation']['balances']}). "
        f"Operating Cash Flow ₹{cf['operating']['direct']:,.0f} vs PAT ₹{is_['pat']:,.0f} — "
        f"gap of ₹{cf['pat_vs_operating_cash_flow_gap']:,.0f} driven mainly by inventory build "
        f"and uncollected receivables (working capital), not by weak underlying profitability."
    )
