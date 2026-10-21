"""Statement Linkage Engine — Module 9 (Three Statement Linkage).

The most important chapter: every transaction should update the Income
Statement, then the Balance Sheet, then the Cash Flow Statement — and
some transactions also create a FUTURE ripple (e.g. buying a machine
today creates depreciation in every future period).

``explain_transaction_linkage`` traces both the immediate ("today") and
downstream ("over time") chain for a transaction type, in plain language.
"""

from __future__ import annotations

from typing import Any, Optional

from financial_foundations.accounting_rules import get_rule
from financial_foundations.chart_of_accounts import get_account
from financial_foundations.schema import AccountType, NormalBalance, Side
from financial_foundations.statement_builder import CASH_FLOW_CLASSIFICATION

# Future ripple effects — Module 9's "over time" chain. Each entry describes
# what a transaction sets in motion for LATER periods (Module 12 exam
# questions are drawn directly from this table).
FUTURE_RIPPLES: dict[str, list[str]] = {
    "buy_asset_cash": [
        "The asset is depreciated over its useful life in future periods.",
        "Depreciation Expense increases each period → EBIT decreases.",
        "Lower EBIT → lower PBT → lower PAT in those future periods.",
        "Lower PAT → smaller addition to Retained Earnings at each future year-end close.",
        "Depreciation itself never reduces Cash again — the cash outflow already "
        "happened today, in Investing activities.",
    ],
    "buy_asset_credit": [
        "The asset is depreciated over its useful life in future periods (same chain as a cash purchase).",
        "Separately, the Accounts Payable created today must eventually be settled in cash "
        "— a future Operating cash outflow with no further Income Statement effect.",
    ],
    "take_loan": [
        "Interest accrues on the outstanding balance in every future period the loan is outstanding.",
        "Interest Expense increases → PBT decreases → PAT decreases in those periods.",
        "Eventually the principal must be repaid — a future Financing cash outflow with "
        "no Income Statement effect (repaying principal is not an expense).",
    ],
    "deferred_revenue_received": [
        "Cash was already received today with no Income Statement effect.",
        "As the obligation is fulfilled in a future period, Unearned Revenue is reduced "
        "and Revenue is recognised then — with NO further cash movement.",
        "This is why a growing 'Unearned Revenue' balance signals future revenue already "
        "paid for by customers.",
    ],
    "prepay_expense": [
        "Cash was already paid today with no Income Statement effect.",
        "As the benefit is consumed in a future period, the Prepaid Expense asset is "
        "reduced and the matching Expense is recognised then — with NO further cash movement.",
    ],
    "salary_due": [
        "The expense already reduced PAT this period.",
        "When the payable is eventually paid, Cash decreases with NO further Income "
        "Statement effect — the expense is not recognised twice.",
    ],
    "accrue_interest": [
        "The expense already reduced PAT this period.",
        "When the payable is eventually paid, Cash decreases with NO further Income "
        "Statement effect.",
    ],
    "accrue_tax": [
        "The expense already reduced PAT this period.",
        "When the payable is eventually remitted, Cash decreases with NO further Income "
        "Statement effect.",
    ],
    "credit_sale": [
        "Revenue was already recognised this period regardless of when cash arrives.",
        "When the customer eventually pays, Cash increases and Accounts Receivable "
        "decreases — Revenue is NOT recognised again.",
    ],
    "purchase_inventory_cash": [
        "No Income Statement effect yet — Inventory sits on the Balance Sheet.",
        "When the inventory is sold, its cost moves to COGS, reducing Gross Profit and "
        "PAT in that future period — with no further cash movement (cash already left today).",
    ],
    "purchase_inventory_credit": [
        "No Income Statement effect yet — Inventory (asset) and Accounts Payable "
        "(liability) both sit on the Balance Sheet.",
        "When the inventory is sold, its cost moves to COGS in that future period.",
        "Separately, when the payable is settled, Cash decreases with no further "
        "Income Statement effect.",
    ],
}


def _statement_tags(account_code: str, transaction_type: str) -> list[str]:
    acc = get_account(account_code)
    tags: list[str] = ["Balance Sheet"]
    if acc.type in (AccountType.REVENUE, AccountType.EXPENSE):
        tags.append("Income Statement")
    if account_code == "cash":
        section = CASH_FLOW_CLASSIFICATION.get(transaction_type)
        if section:
            tags = ["Cash Flow Statement (" + section.value.capitalize() + ")"]
        else:
            tags = ["Cash Flow Statement"]
    return tags


def explain_transaction_linkage(transaction_type: str, *, amount: float = 100_000.0, **kwargs: Any) -> dict[str, Any]:
    """Trace one transaction's impact across IS → BS → CF, today and later.

    Extra ``kwargs`` (e.g. ``asset_account="machinery"``) are passed
    through to the transaction rule exactly as in ``build_journal_entry``,
    so the explanation names the correct account instead of defaulting.
    """
    rule = get_rule(transaction_type)
    if rule is None:
        return {"found": False, "transaction_type": transaction_type}

    legs = rule.build(amount, **kwargs)
    today: list[dict[str, Any]] = []
    for code, side, amt in legs:
        acc = get_account(code)
        side_matches_normal = (
            side == Side.DEBIT and acc.normal_balance == NormalBalance.DEBIT
        ) or (side == Side.CREDIT and acc.normal_balance == NormalBalance.CREDIT)
        direction = "↑" if side_matches_normal else "↓"
        today.append(
            {
                "account": acc.name,
                "account_code": code,
                "direction": direction,
                "amount": round(amt, 2),
                "statements_affected": _statement_tags(code, transaction_type),
            }
        )

    touches_is = any("Income Statement" in t["statements_affected"] for t in today)
    touches_cash = any("Cash Flow" in " ".join(t["statements_affected"]) for t in today)

    return {
        "found": True,
        "transaction_type": transaction_type,
        "label": rule.label,
        "teaches": rule.teaches,
        "today": today,
        "cash_affected_today": touches_cash,
        "income_statement_affected_today": touches_is,
        "future_ripple": FUTURE_RIPPLES.get(transaction_type, []),
        "summary": _summary(rule.label, today, touches_is, touches_cash, transaction_type),
    }


def _summary(label: str, today: list[dict[str, Any]], touches_is: bool, touches_cash: bool, ttype: str) -> str:
    parts = [f"{label}:"]
    for t in today:
        parts.append(f"{t['account']} {t['direction']} ₹{t['amount']:,.0f} ({', '.join(t['statements_affected'])})")
    if not touches_is:
        parts.append("No Income Statement effect today.")
    if not touches_cash:
        parts.append("No Cash Flow effect today.")
    if ttype in FUTURE_RIPPLES:
        parts.append("Over time: " + " → ".join(FUTURE_RIPPLES[ttype][:3]))
    return " ".join(parts)


def why_pat_not_equal_cash_flow() -> dict[str, Any]:
    """The single most important Phase-1 lesson, as a structured explanation."""
    return {
        "question": "Why can PAT differ from Operating Cash Flow?",
        "reasons": [
            {
                "cause": "Depreciation",
                "explanation": "Depreciation reduces PAT (via EBIT) but is a non-cash expense — "
                "it is added back when computing Operating Cash Flow.",
            },
            {
                "cause": "Revenue recognised without cash collected",
                "explanation": "A credit sale increases PAT via Revenue, but if Accounts "
                "Receivable increases, cash has not yet been collected — the increase in "
                "Receivables is subtracted in the Cash Flow Statement.",
            },
            {
                "cause": "Inventory build-up",
                "explanation": "Buying inventory ahead of sales increases the Inventory asset "
                "without any Income Statement effect yet, consuming cash that PAT does not reflect.",
            },
            {
                "cause": "Expenses accrued but not yet paid",
                "explanation": "Salary/Interest/Tax due but unpaid reduce PAT immediately, but "
                "conserve cash until actually paid — increasing the related payable adds cash "
                "back in the Cash Flow Statement relative to PAT.",
            },
            {
                "cause": "Cash received before revenue is earned",
                "explanation": "Deferred/Unearned Revenue increases cash with no PAT effect — "
                "the opposite direction of the credit-sale case above.",
            },
        ],
        "one_line": "PAT is an accounting measure of value created; Operating Cash Flow is a "
        "measure of cash actually moved — depreciation, working capital, and accrual timing "
        "are exactly what separates the two.",
    }
