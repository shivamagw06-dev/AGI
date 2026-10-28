"""Module 3 — Chart of Accounts.

AGI should know where every transaction belongs. This registry is the
single source of truth for account classification: type, normal balance
(derived), balance-sheet bucket, and income-statement category.
"""

from __future__ import annotations

from typing import Optional

from financial_foundations.schema import (
    Account,
    AccountType,
    BsClassification,
    IsCategory,
)

_A = BsClassification
_I = IsCategory

CHART_OF_ACCOUNTS: dict[str, Account] = {
    # ---- Assets ----
    "cash": Account(
        "cash", "Cash", AccountType.ASSET, _A.CURRENT_ASSET,
        description="Cash and bank balances — the only account both statements agree on.",
    ),
    "accounts_receivable": Account(
        "accounts_receivable", "Accounts Receivable", AccountType.ASSET, _A.CURRENT_ASSET,
        description="Amounts owed by customers for credit sales already recognised as revenue.",
    ),
    "inventory": Account(
        "inventory", "Inventory", AccountType.ASSET, _A.CURRENT_ASSET,
        description="Goods held for sale; becomes COGS when sold.",
    ),
    "prepaid_expenses": Account(
        "prepaid_expenses", "Prepaid Expenses", AccountType.ASSET, _A.CURRENT_ASSET,
        description="Cash paid for a future expense; not yet an expense.",
    ),
    "land": Account(
        "land", "Land", AccountType.ASSET, _A.NON_CURRENT_ASSET,
        description="Non-depreciating fixed asset.",
    ),
    "machinery": Account(
        "machinery", "Machinery", AccountType.ASSET, _A.NON_CURRENT_ASSET,
        description="Property, Plant & Equipment (PPE) — depreciates over its useful life.",
    ),
    "furniture": Account(
        "furniture", "Furniture", AccountType.ASSET, _A.NON_CURRENT_ASSET,
        description="PPE — depreciates over its useful life.",
    ),
    "accumulated_depreciation": Account(
        "accumulated_depreciation", "Accumulated Depreciation", AccountType.CONTRA_ASSET,
        _A.NON_CURRENT_ASSET,
        description="Contra-asset: cumulative depreciation charged against PPE. Net PPE = PPE − this.",
    ),
    # ---- Liabilities ----
    "accounts_payable": Account(
        "accounts_payable", "Accounts Payable", AccountType.LIABILITY, _A.CURRENT_LIABILITY,
        description="Amounts owed to suppliers for goods/services already received.",
    ),
    "salary_payable": Account(
        "salary_payable", "Salary Payable", AccountType.LIABILITY, _A.CURRENT_LIABILITY,
        description="Salary expense recognised but not yet paid in cash.",
    ),
    "interest_payable": Account(
        "interest_payable", "Interest Payable", AccountType.LIABILITY, _A.CURRENT_LIABILITY,
        description="Interest expense accrued but not yet paid.",
    ),
    "tax_payable": Account(
        "tax_payable", "Tax Payable", AccountType.LIABILITY, _A.CURRENT_LIABILITY,
        description="Tax expense accrued but not yet remitted.",
    ),
    "unearned_revenue": Account(
        "unearned_revenue", "Unearned / Deferred Revenue", AccountType.LIABILITY,
        _A.CURRENT_LIABILITY,
        description="Cash received before the related goods/services are delivered — a liability, not revenue.",
    ),
    "dividends_payable": Account(
        "dividends_payable", "Dividends Payable", AccountType.LIABILITY, _A.CURRENT_LIABILITY,
        description="Dividend declared but not yet paid to shareholders.",
    ),
    "bank_loan": Account(
        "bank_loan", "Bank Loan", AccountType.LIABILITY, _A.LONG_TERM_LIABILITY,
        description="Borrowed capital; a financing inflow, never revenue.",
    ),
    # ---- Equity ----
    "share_capital": Account(
        "share_capital", "Share Capital", AccountType.EQUITY, _A.EQUITY,
        description="Capital contributed by owners in exchange for equity ownership.",
    ),
    "retained_earnings": Account(
        "retained_earnings", "Retained Earnings", AccountType.EQUITY, _A.EQUITY,
        description="Cumulative PAT not distributed as dividends — the bridge between the Income Statement and the Balance Sheet.",
    ),
    # ---- Revenue ----
    "product_sales": Account(
        "product_sales", "Product Sales", AccountType.REVENUE, is_category=_I.REVENUE,
        description="Revenue earned from selling goods, recognised on delivery — not on cash receipt.",
    ),
    "service_revenue": Account(
        "service_revenue", "Service Revenue", AccountType.REVENUE, is_category=_I.REVENUE,
        description="Revenue earned from services rendered.",
    ),
    # ---- Expenses ----
    "cogs": Account(
        "cogs", "Cost of Goods Sold", AccountType.EXPENSE, is_category=_I.COGS,
        description="Direct cost of the inventory sold in the period; matched against revenue.",
    ),
    "salary_expense": Account(
        "salary_expense", "Salary Expense", AccountType.EXPENSE, is_category=_I.OPERATING_EXPENSE,
        description="Cost of labour for the period, recognised when incurred — not when paid.",
    ),
    "rent_expense": Account(
        "rent_expense", "Rent Expense", AccountType.EXPENSE, is_category=_I.OPERATING_EXPENSE,
        description="Cost of occupying premises for the period.",
    ),
    "marketing_expense": Account(
        "marketing_expense", "Marketing Expense", AccountType.EXPENSE, is_category=_I.OPERATING_EXPENSE,
        description="Cost of demand generation for the period.",
    ),
    "rd_expense": Account(
        "rd_expense", "R&D Expense", AccountType.EXPENSE, is_category=_I.OPERATING_EXPENSE,
        description="Cost of research & development for the period.",
    ),
    "bad_debt_expense": Account(
        "bad_debt_expense", "Bad Debt Expense", AccountType.EXPENSE, is_category=_I.OPERATING_EXPENSE,
        description="Recognises receivables that are no longer expected to be collected.",
    ),
    "depreciation_expense": Account(
        "depreciation_expense", "Depreciation Expense", AccountType.EXPENSE, is_category=_I.DEPRECIATION,
        description="Non-cash allocation of a fixed asset's cost over its useful life.",
    ),
    "interest_expense": Account(
        "interest_expense", "Interest Expense", AccountType.EXPENSE, is_category=_I.INTEREST,
        description="Cost of borrowed capital for the period.",
    ),
    "tax_expense": Account(
        "tax_expense", "Tax Expense", AccountType.EXPENSE, is_category=_I.TAX,
        description="Income tax charged against pre-tax profit for the period.",
    ),
}


def get_account(code: str) -> Optional[Account]:
    return CHART_OF_ACCOUNTS.get(code)


def classify(code: str) -> dict[str, str]:
    """Where does this account belong? — the Module 3 success criterion."""
    acc = get_account(code)
    if not acc:
        return {"found": False, "code": code}
    return {
        "found": True,
        "code": acc.code,
        "name": acc.name,
        "type": acc.type.value,
        "normal_balance": acc.normal_balance.value,
        "bs_classification": acc.bs_classification.value,
        "is_category": acc.is_category.value,
        "description": acc.description,
    }


def accounts_by_type(account_type: AccountType) -> list[Account]:
    return [a for a in CHART_OF_ACCOUNTS.values() if a.type == account_type]


def list_chart() -> list[dict[str, str]]:
    return [classify(code) for code in CHART_OF_ACCOUNTS]
