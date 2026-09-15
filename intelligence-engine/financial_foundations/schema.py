"""Financial Foundations — core schema (accounts, postings, journal entries).

Deterministic double-entry accounting model. No LLM, no market data, no
valuation. Every object here is pure accounting logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

FF_VERSION = "financial-foundations-v1.0.0"
PROGRAMME = "AGIB Phase 1 — Financial Foundations (Accounting Intelligence)"
MODULE_CODE = "FF"

FREEZE_LOCKS: dict[str, Any] = {
    "not_an_investment_module": True,
    "not_a_valuation_module": True,
    "no_llm_accounting_logic": True,
    "deterministic_only": True,
    "double_entry_always_balances": True,
}

# Phase 1 is declared FROZEN as of the Institutional Accounting Exam
# (Level 1) release-gate pass (see institutional_accounting_exam/).
# No new features from here — only bug fixes. Phase 3 (business models,
# unit economics, moats, industry structure) builds ON TOP of this
# engine rather than modifying it.
RELEASE_STATUS: dict[str, Any] = {
    "status": "frozen",
    "frozen_version": FF_VERSION,
    "frozen_reason": "Passed Institutional Accounting Exam (Level 1) release gate.",
    "exam_overall_score": 0.9365,
    "exam_passing_score": 0.90,
    "exam_module_code": "IAE",
    "policy": "no_new_features_bug_fixes_only",
}


class AccountType(str, Enum):
    ASSET = "asset"
    LIABILITY = "liability"
    EQUITY = "equity"
    REVENUE = "revenue"
    EXPENSE = "expense"
    CONTRA_ASSET = "contra_asset"  # e.g. Accumulated Depreciation


class NormalBalance(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"


class Side(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"


# Which side increases each account type — this is THE double-entry rule
# (Module 2). Everything else in the engine derives from this table.
NORMAL_BALANCE_BY_TYPE: dict[AccountType, NormalBalance] = {
    AccountType.ASSET: NormalBalance.DEBIT,
    AccountType.EXPENSE: NormalBalance.DEBIT,
    AccountType.CONTRA_ASSET: NormalBalance.CREDIT,
    AccountType.LIABILITY: NormalBalance.CREDIT,
    AccountType.EQUITY: NormalBalance.CREDIT,
    AccountType.REVENUE: NormalBalance.CREDIT,
}


class BsClassification(str, Enum):
    CURRENT_ASSET = "current_asset"
    NON_CURRENT_ASSET = "non_current_asset"
    CURRENT_LIABILITY = "current_liability"
    LONG_TERM_LIABILITY = "long_term_liability"
    EQUITY = "equity"
    NOT_APPLICABLE = "n/a"


class IsCategory(str, Enum):
    REVENUE = "revenue"
    COGS = "cogs"
    OPERATING_EXPENSE = "operating_expense"
    DEPRECIATION = "depreciation"
    INTEREST = "interest"
    TAX = "tax"
    NOT_APPLICABLE = "n/a"


class CashFlowSection(str, Enum):
    OPERATING = "operating"
    INVESTING = "investing"
    FINANCING = "financing"
    NON_CASH = "non_cash"  # e.g. accruals that never touch Cash directly


@dataclass(frozen=True)
class Account:
    code: str
    name: str
    type: AccountType
    bs_classification: BsClassification = BsClassification.NOT_APPLICABLE
    is_category: IsCategory = IsCategory.NOT_APPLICABLE
    description: str = ""

    @property
    def normal_balance(self) -> NormalBalance:
        return NORMAL_BALANCE_BY_TYPE[self.type]


@dataclass(frozen=True)
class Posting:
    """One leg of a journal entry: an account, a side, and an amount."""

    account_code: str
    side: Side
    amount: float

    def signed(self, normal_balance: NormalBalance) -> float:
        """Return the amount signed so that + always means 'increase'."""
        if self.side.value == normal_balance.value:
            return self.amount
        return -self.amount


@dataclass
class JournalEntry:
    """A balanced double-entry transaction (Module 2)."""

    entry_id: str
    transaction_type: str
    narrative: str
    postings: list[Posting] = field(default_factory=list)
    period: int = 1
    meta: dict[str, Any] = field(default_factory=dict)

    def total_debits(self) -> float:
        return round(sum(p.amount for p in self.postings if p.side == Side.DEBIT), 2)

    def total_credits(self) -> float:
        return round(sum(p.amount for p in self.postings if p.side == Side.CREDIT), 2)

    def is_balanced(self) -> bool:
        return abs(self.total_debits() - self.total_credits()) < 1e-6

    def accounts_touched(self) -> list[str]:
        seen: list[str] = []
        for p in self.postings:
            if p.account_code not in seen:
                seen.append(p.account_code)
        return seen
