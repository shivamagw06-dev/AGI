"""Journal → Ledger → Trial Balance (Module 2, Module 10 — Financial Closing).

Permanent accounts (Assets, Liabilities, Equity) carry a balance forward
across periods. Flow accounts (Revenue, Expense, COGS, Depreciation,
Interest, Tax) are period-scoped and must be closed into Retained
Earnings at period end — exactly like a real year-end close.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from financial_foundations.chart_of_accounts import CHART_OF_ACCOUNTS, get_account
from financial_foundations.accounting_rules import build_journal_entry
from financial_foundations.schema import (
    AccountType,
    JournalEntry,
    NormalBalance,
    Posting,
    Side,
)

_FLOW_TYPES = {
    AccountType.REVENUE,
    AccountType.EXPENSE,
}


@dataclass
class Ledger:
    """Posts journal entries and answers balance / trial-balance queries."""

    entries: list[JournalEntry] = field(default_factory=list)
    closed_periods: set[int] = field(default_factory=set)

    # -- posting -----------------------------------------------------
    def post(self, entry: JournalEntry) -> JournalEntry:
        if not entry.is_balanced():
            raise ValueError(f"Refusing to post unbalanced entry {entry.entry_id}")
        self.entries.append(entry)
        return entry

    def record(
        self,
        transaction_type: str,
        amount: float,
        *,
        narrative: Optional[str] = None,
        period: int = 1,
        **kwargs,
    ) -> JournalEntry:
        entry = build_journal_entry(transaction_type, amount, narrative=narrative, period=period, **kwargs)
        return self.post(entry)

    # -- queries -------------------------------------------------------
    def postings_for_account(
        self, account_code: str, *, period: Optional[int] = None, through_period: Optional[int] = None
    ) -> list[tuple[JournalEntry, Posting]]:
        out: list[tuple[JournalEntry, Posting]] = []
        for entry in self.entries:
            if period is not None and entry.period != period:
                continue
            if through_period is not None and entry.period > through_period:
                continue
            # An exact-period query is used to build THAT period's Income
            # Statement — it must reflect actual activity, not the closing
            # entry that immediately zeroes Revenue/Expense back out.
            if period is not None and entry.transaction_type == "closing_entry":
                continue
            for p in entry.postings:
                if p.account_code == account_code:
                    out.append((entry, p))
        return out

    def balance(
        self,
        account_code: str,
        *,
        period: Optional[int] = None,
        through_period: Optional[int] = None,
    ) -> float:
        """Signed balance where + always means 'increase' for that account type.

        - period=N restricts to postings tagged exactly period N (used for
          flow accounts — this period's Revenue/Expense only).
        - through_period=N accumulates all postings up to and including
          period N (used for permanent accounts — cumulative Balance Sheet).
        """
        acc = get_account(account_code)
        if acc is None:
            raise ValueError(f"Unknown account: {account_code!r}")
        rows = self.postings_for_account(account_code, period=period, through_period=through_period)
        total = 0.0
        for _entry, p in rows:
            total += p.signed(acc.normal_balance)
        return round(total, 2)

    def period_entries(self, period: int, *, include_closing: bool = True) -> list[JournalEntry]:
        return [
            e
            for e in self.entries
            if e.period == period and (include_closing or e.transaction_type != "closing_entry")
        ]

    def trial_balance(self, *, through_period: Optional[int] = None) -> dict[str, dict[str, float]]:
        """All non-zero account balances as {code: {debit, credit}} — must balance."""
        rows: dict[str, dict[str, float]] = {}
        codes = {
            code
            for entry in self.entries
            if through_period is None or entry.period <= through_period
            for code in entry.accounts_touched()
        }
        for code in codes:
            acc = get_account(code)
            bal = self.balance(code, through_period=through_period)
            if abs(bal) < 1e-9:
                continue
            if acc.normal_balance == NormalBalance.DEBIT:
                rows[code] = {"debit": round(bal, 2), "credit": 0.0} if bal >= 0 else {"debit": 0.0, "credit": round(-bal, 2)}
            else:
                rows[code] = {"debit": 0.0, "credit": round(bal, 2)} if bal >= 0 else {"debit": round(-bal, 2), "credit": 0.0}
        return rows

    def trial_balance_is_balanced(self, *, through_period: Optional[int] = None) -> bool:
        tb = self.trial_balance(through_period=through_period)
        total_debit = round(sum(r["debit"] for r in tb.values()), 2)
        total_credit = round(sum(r["credit"] for r in tb.values()), 2)
        return abs(total_debit - total_credit) < 1e-6

    # -- Module 10: financial closing -----------------------------------
    def period_net_income(self, period: int) -> float:
        """PAT for the period from flow-account balances (before closing)."""
        total = 0.0
        for code, acc in CHART_OF_ACCOUNTS.items():
            if acc.type not in _FLOW_TYPES:
                continue
            bal = self.balance(code, period=period)
            if acc.type == AccountType.REVENUE:
                total += bal
            else:  # EXPENSE
                total -= bal
        return round(total, 2)

    def close_period(self, period: int, *, narrative: Optional[str] = None) -> JournalEntry:
        """Zero out this period's Revenue/Expense accounts into Retained Earnings.

        This is the textbook year-end close: every temporary (flow) account
        is debited/credited back to zero, and the net (PAT or loss) lands
        in Retained Earnings — the bridge between the Income Statement and
        the Balance Sheet.
        """
        if period in self.closed_periods:
            raise ValueError(f"Period {period} already closed")
        postings: list[Posting] = []
        net_income = 0.0
        for code, acc in sorted(CHART_OF_ACCOUNTS.items()):
            if acc.type not in _FLOW_TYPES:
                continue
            bal = self.balance(code, period=period)
            if abs(bal) < 1e-9:
                continue
            if acc.type == AccountType.REVENUE:
                # Revenue has a credit balance; close it by debiting.
                postings.append(Posting(code, Side.DEBIT, round(bal, 2)))
                net_income += bal
            else:
                # Expenses have a debit balance; close it by crediting.
                postings.append(Posting(code, Side.CREDIT, round(bal, 2)))
                net_income -= bal
        net_income = round(net_income, 2)
        if net_income >= 0:
            postings.append(Posting("retained_earnings", Side.CREDIT, net_income))
        else:
            postings.append(Posting("retained_earnings", Side.DEBIT, -net_income))
        entry = JournalEntry(
            entry_id=f"close_{period:03d}",
            transaction_type="closing_entry",
            narrative=narrative or f"Year-end close — period {period} (PAT={net_income:,.2f})",
            postings=postings,
            period=period,
            meta={"teaches": "Journal → Ledger → Trial Balance → Adjustments → Close → Statements.", "net_income": net_income},
        )
        if not entry.is_balanced():
            raise ValueError("Closing entry failed to balance — accounting rules engine has a defect")
        self.post(entry)
        self.closed_periods.add(period)
        return entry

    def cash_balance(self, *, through_period: Optional[int] = None) -> float:
        return self.balance("cash", through_period=through_period)
