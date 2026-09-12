"""Phase 2 core schema — a generic, statement-agnostic period model.

Deliberately NOT coupled to any single data source: a ``StatementPeriod``
can be built from Phase 1's ``financial_foundations`` simulation output
(see ``adapters.py``), from the repo's financial_statements_engine, or
from any structured fundamentals feed. This is what lets Phase 2 be the
bridge — Phase 1 teaches how the numbers are built; Phase 2 reads
whatever numbers arrive in this shape.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

FSI_VERSION = "financial-statement-intelligence-v1.0.0"
PROGRAMME = "AGIB Phase 2 — Financial Statement Intelligence (Analyst Reasoning)"
MODULE_CODE = "FSI"

FREEZE_LOCKS: dict[str, Any] = {
    "not_a_recommendation_engine": True,
    "no_llm_narrative_fabrication": True,
    "no_market_data_fetch": True,
    "deterministic_only": True,
    "evidence_required_for_every_claim": True,
}

# Phase 2 is declared FROZEN as of the Institutional Accounting Exam
# (Level 1) release-gate pass (see institutional_accounting_exam/).
# No new features from here — only bug fixes. Documented, not-yet-built
# refinements identified during exam review (deeper hypothesis
# enumeration for Q7/Q12/Q21-style questions; investment-committee-memo
# style prose for the analyst note) are intentionally deferred past this
# freeze — see institutional_accounting_exam/PHASE2_BACKLOG.md.
RELEASE_STATUS: dict[str, Any] = {
    "status": "frozen",
    "frozen_version": FSI_VERSION,
    "frozen_reason": "Passed Institutional Accounting Exam (Level 1) release gate.",
    "exam_overall_score": 0.9365,
    "exam_passing_score": 0.90,
    "exam_module_code": "IAE",
    "policy": "no_new_features_bug_fixes_only",
    "deferred_refinements_doc": "institutional_accounting_exam/PHASE2_BACKLOG.md",
}


@dataclass
class StatementPeriod:
    """One period's Income Statement + Balance Sheet + Cash Flow, flattened.

    All fields default to 0.0 / None so partial data (e.g. a bank with no
    Inventory) does not break the engine — ratios requiring a missing
    field simply report as unavailable rather than fabricating a value.
    """

    label: str  # e.g. "FY24", "Q1FY25"
    sequence: int  # ordering key (1 = earliest)

    # Income Statement
    revenue: float = 0.0
    cogs: float = 0.0
    gross_profit: Optional[float] = None
    opex: float = 0.0
    ebitda: Optional[float] = None
    depreciation: float = 0.0
    ebit: Optional[float] = None
    interest_expense: float = 0.0
    pbt: Optional[float] = None
    tax_expense: float = 0.0
    pat: Optional[float] = None
    shares_outstanding: Optional[float] = None
    eps: Optional[float] = None

    # Balance Sheet
    cash: float = 0.0
    receivables: float = 0.0
    inventory: float = 0.0
    other_current_assets: float = 0.0
    ppe_net: float = 0.0
    intangibles: float = 0.0
    goodwill: float = 0.0
    total_assets: Optional[float] = None

    payables: float = 0.0
    short_term_debt: float = 0.0
    long_term_debt: float = 0.0
    lease_liabilities: float = 0.0
    deferred_tax_liability: float = 0.0
    other_current_liabilities: float = 0.0
    total_liabilities: Optional[float] = None

    share_capital: float = 0.0
    retained_earnings: float = 0.0
    treasury_stock: float = 0.0
    total_equity: Optional[float] = None

    # Cash Flow Statement
    operating_cf: Optional[float] = None
    investing_cf: Optional[float] = None
    financing_cf: Optional[float] = None
    capex: float = 0.0
    dividends_paid: float = 0.0
    buybacks: float = 0.0
    debt_raised: float = 0.0
    debt_repaid: float = 0.0

    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.gross_profit is None:
            self.gross_profit = self.revenue - self.cogs
        if self.ebitda is None:
            self.ebitda = self.gross_profit - self.opex
        if self.ebit is None:
            self.ebit = self.ebitda - self.depreciation
        if self.pbt is None:
            self.pbt = self.ebit - self.interest_expense
        if self.pat is None:
            self.pat = self.pbt - self.tax_expense
        if self.eps is None and self.shares_outstanding:
            self.eps = round(self.pat / self.shares_outstanding, 4)
        current_assets = self.cash + self.receivables + self.inventory + self.other_current_assets
        if self.total_assets is None:
            self.total_assets = current_assets + self.ppe_net + self.intangibles + self.goodwill
        current_liabilities = self.payables + self.short_term_debt + self.other_current_liabilities
        if self.total_liabilities is None:
            self.total_liabilities = (
                current_liabilities + self.long_term_debt + self.lease_liabilities + self.deferred_tax_liability
            )
        if self.total_equity is None:
            self.total_equity = self.share_capital + self.retained_earnings - self.treasury_stock
        if self.operating_cf is None:
            # Indirect-method approximation when a direct OCF isn't supplied.
            self.operating_cf = self.pat + self.depreciation
        if self.investing_cf is None:
            self.investing_cf = -self.capex
        if self.financing_cf is None:
            self.financing_cf = (
                self.debt_raised - self.debt_repaid - self.dividends_paid - self.buybacks
            )

    @property
    def current_assets(self) -> float:
        return self.cash + self.receivables + self.inventory + self.other_current_assets

    @property
    def current_liabilities(self) -> float:
        return self.payables + self.short_term_debt + self.other_current_liabilities

    @property
    def total_debt(self) -> float:
        return self.short_term_debt + self.long_term_debt

    @property
    def net_debt(self) -> float:
        return self.total_debt - self.cash

    @property
    def free_cash_flow(self) -> float:
        return self.operating_cf - self.capex


@dataclass
class FinancialSeries:
    """An ordered multi-period series for one company — the unit every
    engine in this package consumes."""

    company: str
    periods: list[StatementPeriod]
    sector: Optional[str] = None
    data_source: str = "structured_input"

    def __post_init__(self) -> None:
        self.periods = sorted(self.periods, key=lambda p: p.sequence)

    def latest(self) -> Optional[StatementPeriod]:
        return self.periods[-1] if self.periods else None

    def prior(self, *, lag: int = 1) -> Optional[StatementPeriod]:
        if len(self.periods) <= lag:
            return None
        return self.periods[-1 - lag]

    def pair(self, *, lag: int = 1) -> tuple[Optional[StatementPeriod], Optional[StatementPeriod]]:
        return self.prior(lag=lag), self.latest()

    def window(self, n: int) -> list[StatementPeriod]:
        return self.periods[-n:] if n <= len(self.periods) else list(self.periods)
