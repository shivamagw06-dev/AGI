"""Accounting Rules Engine — Module 2 (Double Entry), 4 (Revenue Recognition),
5 (Expense Recognition).

Deterministic logic for turning a business event into a balanced journal
entry. Every transaction type below is a rule: given a type + amount (+
optional secondary amount, e.g. COGS on a sale), produce the correct
debits and credits. This is the "Accounting Rules Engine" deliverable —
no LLM, no ambiguity, always balances.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from financial_foundations.chart_of_accounts import get_account
from financial_foundations.schema import JournalEntry, Posting, Side

_COUNTER = {"n": 0}


def _next_id(prefix: str = "je") -> str:
    _COUNTER["n"] += 1
    return f"{prefix}_{_COUNTER['n']:04d}"


@dataclass(frozen=True)
class TransactionRule:
    """A named, teachable transaction template.

    ``build`` receives (amount, **kwargs) and returns the list of
    (account_code, side, amount) legs. ``teaches`` is the plain-language
    concept this rule demonstrates (used by the Education Layer).
    """

    key: str
    label: str
    description: str
    teaches: str
    cash_effect_today: bool
    build: Callable[..., list[tuple[str, Side, float]]]


def _legs(*pairs: tuple[str, Side, float]) -> list[tuple[str, Side, float]]:
    return list(pairs)


D = Side.DEBIT
C = Side.CREDIT


TRANSACTION_CATALOG: dict[str, TransactionRule] = {
    # ---- Module 1 — Birth of a company ----
    "founder_investment": TransactionRule(
        "founder_investment", "Founder invests capital",
        "Founder contributes cash in exchange for share capital.",
        "The accounting equation (Assets = Liabilities + Equity) is established: "
        "Cash increases and Share Capital increases by the same amount — no liabilities.",
        True,
        lambda amount, **kw: _legs(("cash", D, amount), ("share_capital", C, amount)),
    ),
    "issue_shares": TransactionRule(
        "issue_shares", "Issue additional shares",
        "Company raises fresh equity capital from investors.",
        "Equity financing increases Cash and Share Capital together; no liability is created.",
        True,
        lambda amount, **kw: _legs(("cash", D, amount), ("share_capital", C, amount)),
    ),
    "take_loan": TransactionRule(
        "take_loan", "Take a bank loan",
        "Company borrows cash from a bank.",
        "Debt financing increases Cash and a Liability together — it is not revenue, "
        "because nothing has been earned; it must eventually be repaid.",
        True,
        lambda amount, **kw: _legs(("cash", D, amount), ("bank_loan", C, amount)),
    ),
    "repay_debt": TransactionRule(
        "repay_debt", "Repay bank loan principal",
        "Company repays part of its borrowed principal.",
        "Reduces both a Liability and Cash; it is a Financing outflow and never touches "
        "the Income Statement (principal repayment is not an expense).",
        True,
        lambda amount, **kw: _legs(("bank_loan", D, amount), ("cash", C, amount)),
    ),
    # ---- Module 2 — Double entry basics ----
    "buy_asset_cash": TransactionRule(
        "buy_asset_cash", "Buy a fixed asset for cash",
        "Company buys a fixed asset (land, machinery, furniture) for cash.",
        "One asset (Cash) is exchanged for another asset (PPE) — total assets, and the "
        "accounting equation, are unchanged today. The Income Statement is untouched.",
        True,
        lambda amount, *, asset_account="furniture", **kw: _legs(
            (asset_account, D, amount), ("cash", C, amount)
        ),
    ),
    "buy_asset_credit": TransactionRule(
        "buy_asset_credit", "Buy a fixed asset on credit",
        "Company buys a fixed asset without paying cash immediately.",
        "An asset increases and a liability (Accounts Payable) increases together — cash is untouched today.",
        False,
        lambda amount, *, asset_account="machinery", **kw: _legs(
            (asset_account, D, amount), ("accounts_payable", C, amount)
        ),
    ),
    # ---- Module 4 — Revenue recognition ----
    "credit_sale": TransactionRule(
        "credit_sale", "Sell goods/services on credit",
        "Revenue is earned when goods/services are delivered — not when cash is received.",
        "Revenue is recognised on delivery via Accounts Receivable, NOT cash. "
        "Cash does not increase; the sale still counts toward this period's Income Statement.",
        False,
        lambda amount, **kw: _legs(("accounts_receivable", D, amount), ("service_revenue" if kw.get("service") else "product_sales", C, amount)),
    ),
    "cash_sale": TransactionRule(
        "cash_sale", "Sell goods/services for cash",
        "Revenue is earned and cash is collected in the same transaction.",
        "Both Cash and Revenue increase together — the simplest case, but still governed "
        "by the same recognition rule as a credit sale (delivery, not cash, triggers revenue).",
        True,
        lambda amount, **kw: _legs(("cash", D, amount), ("service_revenue" if kw.get("service") else "product_sales", C, amount)),
    ),
    "collect_receivable": TransactionRule(
        "collect_receivable", "Collect cash from a customer",
        "Customer pays an invoice that was already recognised as revenue earlier.",
        "Cash increases and Accounts Receivable decreases — revenue is NOT recognised "
        "again; it was already earned when the sale occurred.",
        True,
        lambda amount, **kw: _legs(("cash", D, amount), ("accounts_receivable", C, amount)),
    ),
    "deferred_revenue_received": TransactionRule(
        "deferred_revenue_received", "Receive cash before delivering the product/service",
        "Customer pays in advance for a product/service not yet delivered.",
        "Cash increases but revenue is NOT recognised — a liability (Unearned Revenue) "
        "increases instead, because the obligation to deliver has not been satisfied.",
        True,
        lambda amount, **kw: _legs(("cash", D, amount), ("unearned_revenue", C, amount)),
    ),
    "recognize_deferred_revenue": TransactionRule(
        "recognize_deferred_revenue", "Deliver the product/service owed to a customer",
        "The obligation behind previously-collected cash is now satisfied.",
        "Unearned Revenue (a liability) decreases and Revenue increases — cash does not "
        "move again; it moved when the cash was originally collected.",
        False,
        lambda amount, **kw: _legs(("unearned_revenue", D, amount), ("service_revenue", C, amount)),
    ),
    "write_off_bad_debt": TransactionRule(
        "write_off_bad_debt", "Write off an uncollectible receivable",
        "A customer will never pay; the receivable is no longer an asset.",
        "Accounts Receivable decreases and Bad Debt Expense increases — revenue already "
        "recognised is not reversed; only the expected collection is written off.",
        False,
        lambda amount, **kw: _legs(("bad_debt_expense", D, amount), ("accounts_receivable", C, amount)),
    ),
    # ---- Module 5 — Expense recognition ----
    "purchase_inventory_cash": TransactionRule(
        "purchase_inventory_cash", "Purchase inventory for cash",
        "Buying inventory is not an expense — it is an asset until sold.",
        "One asset (Cash) is exchanged for another (Inventory). The Income Statement is "
        "untouched until the inventory is sold (matching principle).",
        True,
        lambda amount, **kw: _legs(("inventory", D, amount), ("cash", C, amount)),
    ),
    "purchase_inventory_credit": TransactionRule(
        "purchase_inventory_credit", "Purchase inventory on credit",
        "Inventory is received before it is paid for.",
        "Inventory (asset) increases and Accounts Payable (liability) increases; cash "
        "is untouched today.",
        False,
        lambda amount, **kw: _legs(("inventory", D, amount), ("accounts_payable", C, amount)),
    ),
    "sell_inventory_cogs": TransactionRule(
        "sell_inventory_cogs", "Recognise COGS when inventory is sold",
        "When inventory is sold, its cost moves from the Balance Sheet to the Income Statement.",
        "Inventory (asset) decreases and COGS (expense) increases by the same amount — "
        "this is the matching principle: cost is recognised in the same period as the "
        "revenue it helped generate.",
        False,
        lambda amount, **kw: _legs(("cogs", D, amount), ("inventory", C, amount)),
    ),
    "pay_payable": TransactionRule(
        "pay_payable", "Pay a supplier invoice",
        "Settling a liability that was already recorded as an expense/asset earlier.",
        "Accounts Payable decreases and Cash decreases — no new expense is recognised; "
        "the expense was already recorded when the goods/services were received.",
        True,
        lambda amount, **kw: _legs(("accounts_payable", D, amount), ("cash", C, amount)),
    ),
    "salary_due": TransactionRule(
        "salary_due", "Recognise salary expense before payment",
        "The expense happens before the cash payment (accrual basis).",
        "Salary Expense increases and Salary Payable (liability) increases — cash is "
        "unchanged; the obligation exists the moment the work is done, not when paid.",
        False,
        lambda amount, **kw: _legs(("salary_expense", D, amount), ("salary_payable", C, amount)),
    ),
    "pay_salary_payable": TransactionRule(
        "pay_salary_payable", "Pay previously-accrued salary",
        "Cash settles an obligation already expensed in an earlier period.",
        "Salary Payable decreases and Cash decreases — no new expense; it was already "
        "recognised when the salary became due.",
        True,
        lambda amount, **kw: _legs(("salary_payable", D, amount), ("cash", C, amount)),
    ),
    "pay_expense_cash": TransactionRule(
        "pay_expense_cash", "Pay an operating expense in cash",
        "Expense incurred and paid in the same transaction (rent, marketing, R&D).",
        "The relevant expense account increases and Cash decreases together — this "
        "reduces both PAT and Cash in the same period, unlike an accrual.",
        True,
        lambda amount, *, expense_account="rent_expense", **kw: _legs(
            (expense_account, D, amount), ("cash", C, amount)
        ),
    ),
    "accrue_interest": TransactionRule(
        "accrue_interest", "Accrue interest on borrowed capital",
        "Interest is owed for the period even before it is paid.",
        "Interest Expense increases and Interest Payable increases — reduces PAT this "
        "period with no cash effect until paid.",
        False,
        lambda amount, **kw: _legs(("interest_expense", D, amount), ("interest_payable", C, amount)),
    ),
    "pay_interest": TransactionRule(
        "pay_interest", "Pay interest in cash",
        "Interest expense and cash payment occur together.",
        "Interest Expense increases and Cash decreases in the same period — reduces "
        "both PAT and Cash from Operating activities.",
        True,
        lambda amount, **kw: _legs(("interest_expense", D, amount), ("cash", C, amount)),
    ),
    "accrue_tax": TransactionRule(
        "accrue_tax", "Accrue income tax on this period's profit",
        "Tax is owed on this period's PBT even before it is remitted.",
        "Tax Expense increases and Tax Payable increases — reduces PAT this period "
        "with no cash effect until the tax authority is paid.",
        False,
        lambda amount, **kw: _legs(("tax_expense", D, amount), ("tax_payable", C, amount)),
    ),
    "pay_tax": TransactionRule(
        "pay_tax", "Pay income tax in cash",
        "Tax expense and cash payment occur together.",
        "Tax Expense increases and Cash decreases together — reduces both PAT and Cash.",
        True,
        lambda amount, **kw: _legs(("tax_expense", D, amount), ("cash", C, amount)),
    ),
    "record_depreciation": TransactionRule(
        "record_depreciation", "Record periodic depreciation",
        "PPE's cost is allocated to the Income Statement over its useful life.",
        "Depreciation Expense increases (reduces EBIT and PAT) while Accumulated "
        "Depreciation (a contra-asset) increases — Cash is completely untouched. This is "
        "why Depreciation is added back when building Cash Flow from PAT.",
        False,
        lambda amount, **kw: _legs(("depreciation_expense", D, amount), ("accumulated_depreciation", C, amount)),
    ),
    "prepay_expense": TransactionRule(
        "prepay_expense", "Pay cash for a future expense",
        "Cash is paid today for a benefit consumed in a future period.",
        "Prepaid Expenses (asset) increases and Cash decreases — no expense is "
        "recognised yet; the Income Statement is untouched until the benefit is consumed.",
        True,
        lambda amount, **kw: _legs(("prepaid_expenses", D, amount), ("cash", C, amount)),
    ),
    "consume_prepaid_expense": TransactionRule(
        "consume_prepaid_expense", "Recognise a prepaid expense as it is consumed",
        "The future period arrives and the benefit is used up.",
        "Rent/other Expense increases and Prepaid Expenses (asset) decreases — cash "
        "does not move again; it moved when the expense was prepaid.",
        False,
        lambda amount, **kw: _legs(("rent_expense", D, amount), ("prepaid_expenses", C, amount)),
    ),
    # ---- Capital / dividends ----
    "declare_dividend": TransactionRule(
        "declare_dividend", "Declare a dividend to shareholders",
        "A distribution of profit is declared but not yet paid.",
        "Retained Earnings decreases and Dividends Payable (liability) increases — "
        "dividends reduce equity directly; they are never an Income Statement expense.",
        False,
        lambda amount, **kw: _legs(("retained_earnings", D, amount), ("dividends_payable", C, amount)),
    ),
    "pay_dividend": TransactionRule(
        "pay_dividend", "Pay a previously-declared dividend",
        "Cash settles the obligation created when the dividend was declared.",
        "Dividends Payable decreases and Cash decreases — a Financing outflow with no "
        "Income Statement effect.",
        True,
        lambda amount, **kw: _legs(("dividends_payable", D, amount), ("cash", C, amount)),
    ),
}


def get_rule(key: str) -> Optional[TransactionRule]:
    return TRANSACTION_CATALOG.get(key)


def list_transaction_types() -> list[str]:
    return sorted(TRANSACTION_CATALOG.keys())


def build_journal_entry(
    transaction_type: str,
    amount: float,
    *,
    narrative: Optional[str] = None,
    period: int = 1,
    **kwargs: Any,
) -> JournalEntry:
    """The Accounting Rules Engine's single entry point.

    Given a transaction type and amount, deterministically produce a
    balanced JournalEntry. Raises ValueError for unknown types or
    unbalanced results (should never happen if rules are authored
    correctly — this is a hard safety net).
    """
    rule = get_rule(transaction_type)
    if rule is None:
        raise ValueError(f"Unknown transaction type: {transaction_type!r}")
    legs = rule.build(amount, **kwargs)
    postings = [Posting(account_code=code, side=side, amount=round(amt, 2)) for code, side, amt in legs]
    entry = JournalEntry(
        entry_id=_next_id(),
        transaction_type=transaction_type,
        narrative=narrative or rule.label,
        postings=postings,
        period=period,
        meta={"teaches": rule.teaches, "cash_effect_today": rule.cash_effect_today, **kwargs},
    )
    if not entry.is_balanced():
        raise ValueError(
            f"Unbalanced journal entry for {transaction_type}: "
            f"debits={entry.total_debits()} credits={entry.total_credits()}"
        )
    for code in entry.accounts_touched():
        if get_account(code) is None:
            raise ValueError(f"Unknown account in chart of accounts: {code!r}")
    return entry


def explain_rule(transaction_type: str) -> dict[str, Any]:
    rule = get_rule(transaction_type)
    if not rule:
        return {"found": False, "transaction_type": transaction_type}
    return {
        "found": True,
        "key": rule.key,
        "label": rule.label,
        "description": rule.description,
        "teaches": rule.teaches,
        "cash_effect_today": rule.cash_effect_today,
    }
