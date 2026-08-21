"""Warehouse schema — the 14 workbook tabs and their columns.

Each tab is a physical database table. The admin workspace renders a tab as a
sheet, but nothing here is a spreadsheet: types, keys, editability and
computation are declared once and enforced on the server.

Column semantics
----------------
``editable``  admin may type into the cell (creates an override + version)
``computed``  written only by the server-side formula engine (read only)
``key``       part of the natural key that makes a row unique in the tab
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Optional

# --------------------------------------------------------------------------
# Column / tab model
# --------------------------------------------------------------------------

TEXT = "text"
NUMBER = "number"
INTEGER = "integer"
PERCENT = "percent"
CURRENCY = "currency"
DATE = "date"
DATETIME = "datetime"
BOOL = "bool"
JSON = "json"

_NUMERIC_TYPES = {NUMBER, INTEGER, PERCENT, CURRENCY}

# --------------------------------------------------------------------------
# Unit classes
# --------------------------------------------------------------------------
# The database type says how a value is stored; the unit class says what it
# means. Both a share price and annual revenue are CURRENCY, so type alone
# cannot drive normalisation — scaling revenue to millions is correct and
# doing the same to a closing price is data loss.
#
# Only UNIT_INR_MILLION columns are rescaled on write. Everything else passes
# through untouched, so a column nobody has classified can never be corrupted
# by the normaliser.

UNIT_INR_MILLION = "inr_million"  # aggregate money — canonical storage
UNIT_INR = "inr"                  # price and per-share money — stored as reported
UNIT_COUNT = "count"              # share counts, volumes
UNIT_RATIO = "ratio"              # unitless multiples (P/E, P/B)
UNIT_PERCENT = "percent"          # already expressed as a percentage
UNIT_NONE = ""                    # non-numeric or unclassified

#: Columns in this class are rescaled to INR million by the unit normaliser.
RESCALED_UNITS = frozenset({UNIT_INR_MILLION})


@dataclass(frozen=True)
class Column:
    key: str
    label: str
    type: str = TEXT
    editable: bool = True
    computed: bool = False
    width: int = 140
    group: str = ""
    required: bool = False
    options: tuple[str, ...] = ()
    help: str = ""
    unit: str = UNIT_NONE

    @property
    def numeric(self) -> bool:
        return self.type in _NUMERIC_TYPES

    @property
    def rescaled(self) -> bool:
        """True when the unit normaliser may change this column's magnitude."""
        return self.unit in RESCALED_UNITS

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "type": self.type,
            "editable": self.editable and not self.computed,
            "computed": self.computed,
            "width": self.width,
            "group": self.group,
            "required": self.required,
            "options": list(self.options),
            "help": self.help,
            "numeric": self.numeric,
            "unit": self.unit,
        }


@dataclass(frozen=True)
class Tab:
    id: str
    label: str
    description: str
    mode: str  # master | append | structured | computed | generated | internal
    key: tuple[str, ...]
    columns: tuple[Column, ...]
    order_by: tuple[str, ...] = ()
    entity_column: Optional[str] = "symbol"
    search_columns: tuple[str, ...] = ()
    icon: str = ""
    notes: tuple[str, ...] = field(default_factory=tuple)

    # -- lookups ----------------------------------------------------------
    def column(self, key: str) -> Optional[Column]:
        for col in self.columns:
            if col.key == key:
                return col
        return None

    @property
    def column_keys(self) -> list[str]:
        return [c.key for c in self.columns]

    @property
    def computed_keys(self) -> list[str]:
        return [c.key for c in self.columns if c.computed]

    @property
    def editable_keys(self) -> list[str]:
        return [c.key for c in self.columns if c.editable and not c.computed]

    @property
    def append_only(self) -> bool:
        """Append-only tabs keep an immutable snapshot per key (never overwrite history)."""
        return self.mode in {"append", "computed_daily"}

    @property
    def read_only(self) -> bool:
        return self.mode in {"computed", "internal"}

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "mode": self.mode,
            "key": list(self.key),
            "order_by": list(self.order_by or self.key),
            "entity_column": self.entity_column,
            "read_only": self.read_only,
            "append_only": self.append_only,
            "icon": self.icon,
            "notes": list(self.notes),
            "columns": [c.to_dict() for c in self.columns],
        }


def _c(key: str, label: str, type_: str = TEXT, **kw: Any) -> Column:
    return Column(key=key, label=label, type=type_, **kw)


def _computed(key: str, label: str, type_: str = NUMBER, **kw: Any) -> Column:
    kw.setdefault("width", 120)
    return Column(key=key, label=label, type=type_, editable=False, computed=True, **kw)


# Provenance columns exist on every tab and are managed by the server.
PROVENANCE_COLUMNS: tuple[Column, ...] = (
    _c("source", "Source", TEXT, editable=False, width=150, group="Provenance"),
    _c("last_updated", "Last Updated", DATETIME, editable=False, width=170, group="Provenance"),
)

SYSTEM_COLUMNS = ("row_id", "version", "published", "created_at", "overridden")


# --------------------------------------------------------------------------
# Tab 1 — Company Master
# --------------------------------------------------------------------------

COMPANY_MASTER = Tab(
    id="company_master",
    label="Company Master",
    description="Master registry. Primary key for every AGI module.",
    mode="master",
    key=("company_id",),
    order_by=("symbol",),
    entity_column="symbol",
    search_columns=("company_id", "symbol", "bse_symbol", "isin", "company_name", "legal_name"),
    icon="registry",
    columns=(
        _c("company_id", "Company ID", TEXT, editable=False, required=True, width=140, group="Identity"),
        _c("symbol", "NSE Symbol", TEXT, required=True, width=130, group="Identity"),
        _c("bse_symbol", "BSE Symbol", TEXT, width=120, group="Identity"),
        _c("isin", "ISIN", TEXT, width=140, group="Identity"),
        _c("instrument_key", "Instrument Key", TEXT, width=180, group="Identity",
           help="Upstox NSE_EQ|ISIN instrument key"),
        _c("company_name", "Company Name", TEXT, required=True, width=240, group="Identity"),
        _c("legal_name", "Legal Name", TEXT, width=240, group="Identity"),
        _c("sector", "Sector", TEXT, width=160, group="Classification"),
        _c("industry", "Industry", TEXT, width=180, group="Classification"),
        _c("sub_industry", "Sub Industry", TEXT, width=180, group="Classification"),
        _c("industry_dna", "Industry DNA", TEXT, width=180, group="Classification"),
        _c("business_type", "Business Type", TEXT, width=150, group="Classification"),
        _c("business_description", "Business Description", TEXT, width=320, group="Profile"),
        _c("exchange", "Exchange", TEXT, width=110, group="Listing"),
        _c("listing_date", "Listing Date", DATE, width=130, group="Listing"),
        _c("website", "Website", TEXT, width=210, group="Profile"),
        _c("country", "Country", TEXT, width=110, group="Profile"),
        _c("state", "State", TEXT, width=130, group="Profile"),
        _c("city", "City", TEXT, width=130, group="Profile"),
        _c("currency", "Currency", TEXT, width=100, group="Profile"),
        _c("market_cap_inr", "Market Cap (INR)", CURRENCY, width=150, group="Profile", unit=UNIT_INR),
        _c("market_cap_usd", "Market Cap (USD)", CURRENCY, width=150, group="Profile"),
        _c("employee_count", "Employees", INTEGER, width=120, group="Profile"),
        _c("market_status", "Market Status", TEXT, width=130, group="Status",
           options=("listed", "suspended", "delisted", "unlisted")),
        _c("active", "Active", BOOL, width=90, group="Status"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tab — Profile History (append-only revisions from Upstox / other providers)
# --------------------------------------------------------------------------

PROFILE_HISTORY = Tab(
    id="profile_history",
    label="Profile History",
    description="Append-only company profile revisions. Every change is preserved.",
    mode="append",
    key=("symbol", "as_of", "source"),
    order_by=("as_of DESC", "symbol"),
    search_columns=("symbol", "company_name", "sector", "industry"),
    icon="registry",
    notes=("Do not overwrite. Diffs against company_master are stored as new rows.",),
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=130, group="Key"),
        _c("as_of", "As Of", DATE, required=True, width=120, group="Key"),
        _c("isin", "ISIN", TEXT, width=140, group="Identity"),
        _c("instrument_key", "Instrument Key", TEXT, width=180, group="Identity"),
        _c("company_name", "Company Name", TEXT, width=240, group="Identity"),
        _c("legal_name", "Legal Name", TEXT, width=240, group="Identity"),
        _c("sector", "Sector", TEXT, width=160, group="Classification"),
        _c("industry", "Industry", TEXT, width=180, group="Classification"),
        _c("sub_industry", "Sub Industry", TEXT, width=180, group="Classification"),
        _c("business_description", "Business Description", TEXT, width=320, group="Profile"),
        _c("market_cap_inr", "Market Cap (INR)", CURRENCY, width=150, group="Profile", unit=UNIT_INR),
        _c("market_cap_usd", "Market Cap (USD)", CURRENCY, width=150, group="Profile"),
        _c("sector_market_cap_inr", "Sector Market Cap (INR Cr)", CURRENCY,
           width=180, group="Profile"),
        _c("sector_market_cap_usd", "Sector Market Cap (USD)", CURRENCY,
           width=180, group="Profile"),
        _c("website", "Website", TEXT, width=210, group="Profile"),
        _c("city", "City", TEXT, width=130, group="Profile"),
        _c("state", "State", TEXT, width=130, group="Profile"),
        _c("country", "Country", TEXT, width=110, group="Profile"),
        _c("listing_date", "Listing Date", DATE, width=130, group="Listing"),
        _c("employee_count", "Employees", INTEGER, width=120, group="Profile"),
        _c("confidence", "Confidence", NUMBER, width=110, group="Quality"),
        _c("dqiv_status", "DQIV", TEXT, width=110, group="Quality"),
        _c("validation_notes", "Notes", TEXT, width=220, group="Quality"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tab — Peer Relationships (competitor graph)
# --------------------------------------------------------------------------

PEER_RELATIONSHIPS = Tab(
    id="peer_relationships",
    label="Peer Relationships",
    description="Competitor / peer graph resolved to company_master symbols.",
    mode="append",
    key=("symbol", "peer_symbol", "relationship", "source"),
    order_by=("symbol", "peer_symbol"),
    search_columns=("symbol", "peer_symbol", "peer_isin"),
    icon="factors",
    columns=(
        _c("symbol", "Company", TEXT, required=True, width=130, group="Key"),
        _c("peer_symbol", "Peer", TEXT, required=True, width=130, group="Key"),
        _c("peer_isin", "Peer ISIN", TEXT, width=140, group="Identity"),
        _c("peer_instrument_key", "Peer Instrument Key", TEXT, width=180, group="Identity"),
        _c("sector", "Sector", TEXT, width=160, group="Classification"),
        _c("industry", "Industry", TEXT, width=180, group="Classification"),
        _c("relationship", "Relationship", TEXT, required=True, width=140, group="Key",
           options=("competitor", "peer", "subsidiary", "related")),
        _c("confidence", "Confidence", NUMBER, width=110, group="Quality"),
        _c("as_of", "As Of", DATE, width=120, group="Key"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tab 2 — Daily Market History
# --------------------------------------------------------------------------

DAILY_MARKET_HISTORY = Tab(
    id="daily_market_history",
    label="Daily Market History",
    description="One row per company per trading day. Daily append only — history is never overwritten.",
    mode="append",
    key=("symbol", "date"),
    order_by=("date DESC", "symbol"),
    search_columns=("symbol",),
    icon="market",
    notes=("Append only. A re-import for an existing (symbol, date) writes a new snapshot version.",),
    columns=(
        _c("date", "Date", DATE, required=True, width=120, group="Key"),
        _c("symbol", "Symbol", TEXT, required=True, width=130, group="Key"),
        # Prices are money but not aggregates — they stay in rupees.
        _c("open", "Open", CURRENCY, width=110, group="OHLCV", unit=UNIT_INR),
        _c("high", "High", CURRENCY, width=110, group="OHLCV", unit=UNIT_INR),
        _c("low", "Low", CURRENCY, width=110, group="OHLCV", unit=UNIT_INR),
        _c("close", "Close", CURRENCY, width=110, group="OHLCV", unit=UNIT_INR),
        _c("adjusted_close", "Adjusted Close", CURRENCY, width=140, group="OHLCV", unit=UNIT_INR),
        # What `close` actually means on this row.
        #
        # Three feeds write this table and they do not agree on the question.
        # Upstox supplies prices already adjusted for splits and bonuses; the
        # NSE bhavcopy supplies the raw price that traded. Both landed in
        # `close`, so a series could begin on one convention and finish on the
        # other, and the ratio between its ends carried the split factor rather
        # than the return - Dr. Lal PathLabs split two-for-one and was published
        # at -45.29% for a year it finished up 9.4%.
        #
        # The immediate fix was to compute returns within one feed, which works
        # but infers the convention from the writer's name. This column states
        # it, so a reader can ask for a basis instead of guessing at one.
        #
        # RAW              the price as it traded, unadjusted
        # SPLIT_ADJUSTED   restated for splits and bonuses
        # TOTAL_RETURN     splits, bonuses and dividends reinvested
        _c("price_basis", "Price Basis", TEXT, width=150, group="OHLCV",
           help="RAW | SPLIT_ADJUSTED | TOTAL_RETURN"),
        # The vendor behind the row, as distinct from the writer in front of it.
        # Upstox writes under two names - a deep backfill and a nightly top-up -
        # and they share a convention. Grouping on the writer split them apart
        # and left the desk with nothing to pair.
        _c("feed_family", "Feed", TEXT, width=130, group="Provenance"),
        _c("volume", "Volume", INTEGER, width=130, group="OHLCV", unit=UNIT_COUNT),
        _c("vwap", "VWAP", CURRENCY, width=110, group="OHLCV", unit=UNIT_INR),
        _c("delivery_pct", "Delivery %", PERCENT, width=110, group="OHLCV", unit=UNIT_PERCENT),
        _c("dividend", "Dividend", CURRENCY, width=110, group="Actions", unit=UNIT_INR),
        _c("split", "Split", NUMBER, width=100, group="Actions", unit=UNIT_RATIO),
        # Derived from close x shares, so it follows the price scale, not the
        # statement scale. Changing this would change the formula engine too.
        _computed("market_cap", "Market Cap", CURRENCY, width=150, group="Derived", unit=UNIT_INR,
                  help="Close x Shares Outstanding"),
        _c("shares_outstanding", "Shares Outstanding", NUMBER, width=160, group="Derived",
           unit=UNIT_COUNT),
        *PROVENANCE_COLUMNS,
        _c("import_time", "Import Time", DATETIME, editable=False, width=170, group="Provenance"),
    ),
)

EXCHANGE_SESSIONS = Tab(
    id="exchange_sessions",
    label="Exchange Sessions",
    description="Append-only official exchange calendar observations used by point-in-time freshness gates.",
    mode="append",
    key=("exchange", "date"),
    order_by=("date DESC", "exchange"),
    search_columns=("exchange", "calendar_source"),
    icon="market",
    columns=(
        _c("exchange", "Exchange", TEXT, required=True, width=110, group="Key"),
        _c("date", "Date", DATE, required=True, width=120, group="Key"),
        _c("is_trading_day", "Trading Day", BOOL, required=True, width=120, group="Session"),
        _c("start_time", "Start Time", DATETIME, width=170, group="Session"),
        _c("end_time", "End Time", DATETIME, width=170, group="Session"),
        _c("calendar_source", "Calendar Source", TEXT, required=True, width=220, group="Lineage"),
        _c("observed_at", "Observed At", DATETIME, required=True, width=170, group="Lineage"),
        _c("raw", "Raw", JSON, width=260, group="Lineage"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tabs 3 & 4 — Financial statements
# --------------------------------------------------------------------------

_MN = UNIT_INR_MILLION

# Consolidated and standalone are different facts about the same period, not two
# opinions about one fact. Before they were part of the key the second import
# hashed to the same row and silently replaced the first.
STATEMENT_TYPES = ("CONSOLIDATED", "STANDALONE", "UNKNOWN")

# Frequency is carried alongside the type so a tab can hold half-yearly and
# trailing-twelve-month filings without another schema change.
STATEMENT_FREQUENCIES = ("ANNUAL", "QUARTERLY", "HALF_YEARLY", "TTM", "UNKNOWN")

DEFAULT_STATEMENT_TYPE = "UNKNOWN"


def _identity_columns(frequency: str) -> tuple[Column, ...]:
    """Statement identity — part of the natural key on both financial tabs."""
    return (
        _c("statement_type", "Statement Type", TEXT, required=True, width=140, group="Key",
           options=STATEMENT_TYPES,
           help="Consolidated and standalone are stored separately and never compared."),
        _c("statement_frequency", "Frequency", TEXT, width=120, group="Key",
           options=STATEMENT_FREQUENCIES,
           help=f"Defaults to {frequency} for this tab."),
    )


#: Filing lifecycle. Restatements are kept as row snapshots by ``versions``,
#: so these describe *which* filing a row represents rather than duplicating
#: the version chain that already exists.
_FILING_COLUMNS: tuple[Column, ...] = (
    _c("fiscal_end_date", "Fiscal End Date", DATE, width=130, group="Filing"),
    _c("filing_date", "Filing Date", DATE, width=120, group="Filing"),
    _c("effective_date", "Effective Date", DATE, width=130, group="Filing"),
    _c("restated", "Restated", BOOL, width=100, group="Filing",
       help="Set when this filing revises figures the company published earlier."),
    _c("pit_status", "PIT Status", TEXT, editable=False, width=130, group="Filing",
       help="PIT_VALID only when a defensible publication/effective date exists; otherwise PIT_LIMITED."),
    _c("source_document", "Source Document", TEXT, editable=False, width=210, group="Filing"),
    _c("retrieval_date", "Retrieval Date", DATE, editable=False, width=130, group="Filing"),
    _c("source_sheets", "Source Sheets", JSON, editable=False, width=230, group="Filing"),
    _c("source_mnemonics", "Source Mnemonics", JSON, editable=False, width=300, group="Filing"),
)

_STATEMENT_COLUMNS: tuple[Column, ...] = (
    _c("revenue", "Revenue", CURRENCY, width=130, group="P&L", unit=_MN),
    _c("gross_profit", "Gross Profit", CURRENCY, width=130, group="P&L", unit=_MN),
    _c("ebitda", "EBITDA", CURRENCY, width=120, group="P&L", unit=_MN),
    _c("ebit", "EBIT", CURRENCY, width=120, group="P&L", unit=_MN),
    _c("pbt", "PBT", CURRENCY, width=120, group="P&L", unit=_MN),
    _c("pat", "PAT", CURRENCY, width=120, group="P&L", unit=_MN),
    _c("depreciation", "Depreciation", CURRENCY, width=130, group="P&L", unit=_MN),
    _c("amortization", "Amortization", CURRENCY, width=130, group="P&L", unit=_MN),
    _c("ebita", "EBITA", CURRENCY, width=120, group="P&L", unit=_MN),
    _c("tax_expense", "Tax Expense", CURRENCY, width=130, group="P&L", unit=_MN),
    _c("minority_interest", "Minority Interest", CURRENCY, width=150, group="P&L", unit=_MN),
    _c("exceptional_items", "Exceptional Items", CURRENCY, width=150, group="P&L", unit=_MN),
    _c("finance_cost", "Finance Cost", CURRENCY, width=130, group="P&L", unit=_MN),
    _c("research_and_development", "R&D", CURRENCY, width=120, group="P&L", unit=_MN),
    _c("employee_cost", "Employee Cost", CURRENCY, width=140, group="P&L", unit=_MN),
    _c("other_operating_expense", "Other Operating Expense", CURRENCY, width=180, group="P&L", unit=_MN),
    # Per share, not an aggregate: rescaling this to millions would make every
    # earnings per share read as zero.
    _c("eps", "EPS", NUMBER, width=100, group="P&L", unit=UNIT_INR),
    _c("assets", "Assets", CURRENCY, width=130, group="Balance Sheet", unit=_MN),
    _c("equity", "Equity", CURRENCY, width=130, group="Balance Sheet", unit=_MN),
    _c("debt", "Debt", CURRENCY, width=120, group="Balance Sheet", unit=_MN),
    _c("cash", "Cash", CURRENCY, width=120, group="Balance Sheet", unit=_MN),
    _c("short_term_investments", "Short-term Investments", CURRENCY, width=170, group="Balance Sheet", unit=_MN),
    _c("total_investments", "Total Investments", CURRENCY, width=150, group="Balance Sheet", unit=_MN),
    _c("accounts_receivable", "Accounts Receivable", CURRENCY, width=160, group="Balance Sheet", unit=_MN),
    _c("current_assets", "Current Assets", CURRENCY, width=140, group="Balance Sheet", unit=_MN),
    _c("current_liabilities", "Current Liabilities", CURRENCY, width=160, group="Balance Sheet",
       unit=_MN),
    _c("inventory", "Inventory", CURRENCY, width=120, group="Balance Sheet", unit=_MN),
    _c("other_current_assets", "Other Current Assets", CURRENCY, width=160, group="Balance Sheet", unit=_MN),
    _c("net_ppe", "Net PPE", CURRENCY, width=120, group="Balance Sheet", unit=_MN),
    _c("intangible_assets", "Intangible Assets", CURRENCY, width=150, group="Balance Sheet", unit=_MN),
    _c("goodwill", "Goodwill", CURRENCY, width=120, group="Balance Sheet", unit=_MN),
    _c("accounts_payable", "Accounts Payable", CURRENCY, width=150, group="Balance Sheet", unit=_MN),
    _c("other_current_liabilities", "Other Current Liabilities", CURRENCY, width=180, group="Balance Sheet", unit=_MN),
    _c("current_debt", "Current Debt", CURRENCY, width=130, group="Balance Sheet", unit=_MN),
    _c("long_term_debt", "Long-term Debt", CURRENCY, width=140, group="Balance Sheet", unit=_MN),
    _c("lease_liabilities", "Lease Liabilities", CURRENCY, width=150, group="Balance Sheet", unit=_MN),
    _c("provisions", "Provisions", CURRENCY, width=130, group="Balance Sheet", unit=_MN),
    _c("total_liabilities", "Total Liabilities", CURRENCY, width=150, group="Balance Sheet", unit=_MN),
    _c("balance_sheet_minority_interest", "Balance Sheet Minority Interest", CURRENCY,
       width=210, group="Balance Sheet", unit=_MN),
    _c("working_capital", "Working Capital", CURRENCY, width=150, group="Balance Sheet", unit=_MN,
       help="Current Assets - Current Liabilities when both are supplied"),
    _c("capex", "Capex", CURRENCY, width=120, group="Cash Flow", unit=_MN),
    _c("cfo", "CFO", CURRENCY, width=120, group="Cash Flow", unit=_MN),
    _c("cfi", "CFI", CURRENCY, width=120, group="Cash Flow", unit=_MN),
    _c("cff", "CFF", CURRENCY, width=120, group="Cash Flow", unit=_MN),
    _c("acquisition_spending", "Acquisition Spending", CURRENCY, width=170, group="Cash Flow", unit=_MN),
    _c("dividends_paid", "Dividends Paid", CURRENCY, width=140, group="Cash Flow", unit=_MN),
    _c("buybacks", "Buybacks", CURRENCY, width=120, group="Cash Flow", unit=_MN),
    _c("debt_issuance", "Debt Issuance", CURRENCY, width=140, group="Cash Flow", unit=_MN),
    _c("debt_repayment", "Debt Repayment", CURRENCY, width=150, group="Cash Flow", unit=_MN),
    _c("depreciation_cash_flow", "Depreciation (Cash Flow)", CURRENCY,
       width=190, group="Cash Flow", unit=_MN),
    _computed("free_cash_flow", "Free Cash Flow", CURRENCY, width=140, group="Cash Flow", unit=_MN,
              help="CFO - Capex"),
    _c("shares_outstanding", "Shares Outstanding", NUMBER, width=160, group="Per Share",
       unit=UNIT_COUNT),
    _computed("book_value", "Book Value", NUMBER, width=120, group="Per Share", unit=UNIT_INR,
              help="Equity / Shares Outstanding"),
    *_FILING_COLUMNS,
    *PROVENANCE_COLUMNS,
    _c("statement_version", "Statement Version", TEXT, editable=False, width=150, group="Provenance"),
    # One identity for a reporting period, whatever the vendor called it. The
    # label stays in the natural key and is never rewritten on a stored row -
    # rewriting it would mint a new row id and fork the period rather than merge
    # it - so the shared identity is carried alongside instead.
    _c("period_key", "Period Key", TEXT, editable=False, width=120, group="Provenance",
       help="Q1 FY27, FY27Q1, FY2027Q1 and Jun 2026 all resolve to 2026-07-01"),
    # Whether this row may be read as the answer, and what stopped it if not.
    _c("is_canonical", "Canonical", BOOL, editable=False, width=110, group="Provenance",
       help="Set only when period, statement type, source and units are all known"),
    _c("canonical_blockers", "Not Canonical Because", TEXT, editable=False, width=220,
       group="Provenance"),
)

FINANCIALS_ANNUAL = Tab(
    id="financials_annual",
    label="Financials (Annual)",
    description="Annual statement facts. One row per company per fiscal year per statement type.",
    mode="append",
    key=("symbol", "statement_type", "fiscal_year"),
    order_by=("symbol", "fiscal_year DESC"),
    search_columns=("symbol", "fiscal_year", "statement_type"),
    icon="annual",
    notes=("Consolidated and standalone are separate rows and are never compared "
           "against each other.",),
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=130, group="Key"),
        *_identity_columns("ANNUAL"),
        _c("fiscal_year", "Fiscal Year", TEXT, required=True, width=120, group="Key"),
        *_STATEMENT_COLUMNS,
    ),
)

FINANCIALS_QUARTERLY = Tab(
    id="financials_quarterly",
    label="Financials (Quarterly)",
    description="Quarterly statement facts. One row per company per fiscal quarter "
                "per statement type.",
    mode="append",
    key=("symbol", "statement_type", "fiscal_period"),
    order_by=("symbol", "fiscal_period DESC"),
    search_columns=("symbol", "fiscal_period", "statement_type"),
    icon="quarterly",
    notes=("Consolidated and standalone are separate rows and are never compared "
           "against each other.",),
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=130, group="Key"),
        *_identity_columns("QUARTERLY"),
        _c("fiscal_period", "Fiscal Period", TEXT, required=True, width=130, group="Key",
           help="FY2026Q1 style period label"),
        _c("fiscal_year", "Fiscal Year", TEXT, width=110, group="Key"),
        _c("quarter", "Quarter", TEXT, width=90, group="Key"),
        *_STATEMENT_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# CapIQ import controls — evidence and mapping before financial writes
# --------------------------------------------------------------------------

COMPANY_IDENTITY_MAP = Tab(
    id="company_identity_map",
    label="Company Identity Map",
    description="Verified source-to-AGI company identity matches used by controlled imports.",
    mode="structured",
    key=("source", "source_symbol"),
    order_by=("source", "source_symbol"),
    search_columns=("source", "source_symbol", "source_company_name", "symbol", "isin", "agi_company_id"),
    icon="registry",
    columns=(
        *PROVENANCE_COLUMNS,
        _c("source_symbol", "Source Symbol", TEXT, editable=False, required=True, width=140, group="Key"),
        _c("source_company_id", "Source Company ID", TEXT, editable=False, width=150, group="Source"),
        _c("source_company_name", "Source Company Name", TEXT, editable=False, width=240, group="Source"),
        _c("agi_company_id", "AGI Company ID", TEXT, editable=False, width=140, group="AGI Identity"),
        _c("symbol", "NSE Symbol", TEXT, editable=False, width=130, group="AGI Identity"),
        _c("isin", "ISIN", TEXT, editable=False, width=140, group="AGI Identity"),
        _c("company_type", "Company Type", TEXT, editable=False, width=130, group="Classification"),
        _c("match_method", "Match Method", TEXT, editable=False, width=150, group="Verification"),
        _c("match_confidence", "Match Confidence", NUMBER, editable=False, width=130, group="Verification"),
        _c("verified", "Verified", BOOL, editable=False, width=100, group="Verification"),
        _c("verified_at", "Verified At", DATETIME, editable=False, width=170, group="Verification"),
    ),
)

CAPIQ_METRIC_MAPPING = Tab(
    id="capiq_metric_mapping",
    label="CapIQ Metric Mapping",
    description="Versioned Capital IQ source-label to AGI metric dictionary.",
    mode="structured",
    key=("source", "source_label", "company_type", "statement_type", "mapping_version"),
    order_by=("company_type", "source_label"),
    search_columns=("source_label", "canonical_metric", "company_type", "statement_type"),
    icon="mapping",
    columns=(
        *PROVENANCE_COLUMNS,
        _c("source_label", "Source Label", TEXT, editable=False, required=True, width=230, group="Key"),
        _c("company_type", "Company Type", TEXT, editable=False, required=True, width=130, group="Key"),
        _c("statement_type", "Statement Type", TEXT, editable=False, required=True, width=150, group="Key"),
        _c("canonical_metric", "AGI Metric", TEXT, editable=False, width=180, group="Mapping"),
        _c("period_type", "Period Type", TEXT, editable=False, width=110, group="Mapping"),
        _c("sign_multiplier", "Sign Multiplier", NUMBER, editable=False, width=130, group="Mapping"),
        _c("mapping_version", "Mapping Version", TEXT, editable=False, required=True, width=150, group="Key"),
        _c("active", "Active", BOOL, editable=False, width=90, group="Status"),
    ),
)

FINANCIAL_IMPORT_AUDIT = Tab(
    id="financial_import_audit",
    label="Financial Import Audit",
    description="Company-period validation evidence for controlled financial imports.",
    mode="append",
    key=("source", "source_file", "source_symbol", "fiscal_year", "mapping_version"),
    order_by=("fiscal_year DESC", "source_symbol"),
    search_columns=("source_symbol", "symbol", "fiscal_year", "write_status", "overall_status"),
    icon="audit",
    columns=(
        *PROVENANCE_COLUMNS,
        _c("source_file", "Source File", TEXT, editable=False, required=True, width=190, group="Key"),
        _c("source_sheet", "Source Sheet", TEXT, editable=False, width=130, group="Source"),
        _c("source_symbol", "Source Symbol", TEXT, editable=False, required=True, width=130, group="Key"),
        _c("symbol", "NSE Symbol", TEXT, editable=False, width=130, group="Identity"),
        _c("fiscal_year", "Fiscal Year", TEXT, editable=False, required=True, width=120, group="Key"),
        _c("company_type", "Company Type", TEXT, editable=False, width=130, group="Identity"),
        _c("identity_status", "Identity", TEXT, editable=False, width=120, group="Validation"),
        _c("source_fields", "Source Fields", INTEGER, editable=False, width=120, group="Coverage"),
        _c("mapped_fields", "Mapped Fields", INTEGER, editable=False, width=120, group="Coverage"),
        _c("unmapped_fields", "Unmapped Fields", JSON, editable=False, width=250, group="Coverage"),
        _c("required_fields", "Required Fields", JSON, editable=False, width=230, group="Validation"),
        _c("required_fields_found", "Required Fields Found", INTEGER, editable=False, width=165, group="Validation"),
        _c("unit_check", "Unit Check", TEXT, editable=False, width=110, group="Validation"),
        _c("period_check", "Period Check", TEXT, editable=False, width=120, group="Validation"),
        _c("pit_status", "PIT Status", TEXT, editable=False, width=130, group="Validation"),
        _c("pit_limitation", "PIT Limitation", TEXT, editable=False, width=320, group="Validation"),
        _c("reconciliation", "Reconciliation", TEXT, editable=False, width=130, group="Validation"),
        _c("quality_score", "Quality Score", NUMBER, editable=False, width=120, group="Validation"),
        _c("overall_status", "Overall Status", TEXT, editable=False, width=150, group="Status"),
        _c("write_status", "Write Status", TEXT, editable=False, width=140, group="Status"),
        _c("mapping_version", "Mapping Version", TEXT, editable=False, required=True, width=150, group="Key"),
    ),
)

# --------------------------------------------------------------------------
# Tab 5 — Historical Ratios (computed)
# --------------------------------------------------------------------------

HISTORICAL_RATIOS = Tab(
    id="historical_ratios",
    label="Historical Ratios",
    description="Derived from the statement tabs by the server-side formula engine. Read only.",
    mode="computed",
    key=("symbol", "period"),
    order_by=("symbol", "period DESC"),
    search_columns=("symbol", "period"),
    icon="ratios",
    notes=("No manual editing. Recalculated after every statement import.",),
    columns=(
        _c("symbol", "Symbol", TEXT, editable=False, required=True, width=130, group="Key"),
        _c("period", "Period", TEXT, editable=False, required=True, width=120, group="Key"),
        _c("basis", "Basis", TEXT, editable=False, width=100, group="Key",
           options=("annual", "quarterly")),
        _computed("roe", "ROE", PERCENT, group="Returns"),
        _computed("roce", "ROCE", PERCENT, group="Returns"),
        _computed("roa", "ROA", PERCENT, group="Returns"),
        _computed("gross_margin", "Gross Margin", PERCENT, group="Margins"),
        _computed("ebitda_margin", "EBITDA Margin", PERCENT, group="Margins"),
        _computed("operating_margin", "Operating Margin", PERCENT, group="Margins"),
        _computed("net_margin", "Net Margin", PERCENT, group="Margins"),
        _computed("asset_turnover", "Asset Turnover", NUMBER, group="Efficiency"),
        _computed("debt_equity", "Debt / Equity", NUMBER, group="Leverage"),
        _computed("interest_coverage", "Interest Coverage", NUMBER, group="Leverage"),
        _computed("current_ratio", "Current Ratio", NUMBER, group="Liquidity"),
        _computed("quick_ratio", "Quick Ratio", NUMBER, group="Liquidity"),
        _computed("fcf_margin", "FCF Margin", PERCENT, group="Cash"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tab 5b — Annual Sector Ratios (computed)
# --------------------------------------------------------------------------

ANNUAL_SECTOR_RATIOS = Tab(
    id="annual_sector_ratios",
    label="Annual Sector Ratios",
    description=(
        "Fiscal-year sector medians calculated from verified company annual ratios. "
        "ETFs, funds and non-comparable sector metrics are excluded."
    ),
    mode="computed",
    key=("sector", "fiscal_year", "metric"),
    order_by=("fiscal_year DESC", "sector", "metric"),
    search_columns=("sector", "fiscal_year", "metric"),
    icon="valuation",
    notes=(
        "A median is published only with at least 10 eligible companies. ",
        "Financial-sector leverage and liquidity ratios are intentionally suppressed.",
    ),
    columns=(
        _c("sector", "Sector", TEXT, editable=False, required=True, width=170, group="Key"),
        _c("fiscal_year", "Fiscal Year", TEXT, editable=False, required=True, width=120, group="Key"),
        _c("metric", "Metric", TEXT, editable=False, required=True, width=140, group="Key"),
        _computed("median_value", "Sector Median", NUMBER, width=130, group="Ratio"),
        _c("company_count", "Valid Companies", INTEGER, editable=False, width=130, group="Coverage"),
        _c("eligible_company_count", "Eligible Companies", INTEGER, editable=False, width=145, group="Coverage"),
        _c("coverage_pct", "Coverage %", NUMBER, editable=False, width=120, group="Coverage"),
        _c("minimum_required", "Minimum Required", INTEGER, editable=False, width=140, group="Coverage"),
        _c("quality_status", "Quality Status", TEXT, editable=False, width=150, group="Quality"),
        _c("exclusion_reason", "Exclusion Rule", TEXT, editable=False, width=260, group="Quality"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tab 5c — Vendor historical sector ratios (append-only source evidence)
# --------------------------------------------------------------------------

SECTOR_RATIO_HISTORY = Tab(
    id="sector_ratio_history",
    label="Sector Ratio History",
    description=(
        "Capital IQ historical company ratios. Source evidence only: values are "
        "preserved by fiscal year and never replaced by live feeds."
    ),
    mode="append",
    key=("symbol", "fiscal_year", "metric", "source_version"),
    order_by=("fiscal_year DESC", "sector", "symbol", "metric"),
    search_columns=("symbol", "company_name", "sector", "metric", "source_sector"),
    icon="valuation",
    notes=(
        "CapIQ 2016–2025 source snapshot; values are not derived by AGI.",
        "Live feeds append current observations elsewhere and never overwrite this history.",
        "Loss-making or otherwise non-comparable multiples remain visible but are excluded from median calculations.",
    ),
    columns=(
        _c("symbol", "NSE Symbol", TEXT, editable=False, required=True, width=130, group="Key"),
        _c("fiscal_year", "Fiscal Year", TEXT, editable=False, required=True, width=110, group="Key"),
        _c("metric", "Metric", TEXT, editable=False, required=True, width=140, group="Key"),
        _c("source_version", "Source Version", TEXT, editable=False, required=True, width=180, group="Key"),
        _c("as_of", "As Of", DATE, editable=False, required=True, width=120, group="Key"),
        _c("company_name", "Company", TEXT, editable=False, width=240, group="Identity"),
        _c("capiq_ticker", "CapIQ Ticker", TEXT, editable=False, width=150, group="Identity"),
        _c("sector", "AGI Sector", TEXT, editable=False, width=170, group="Classification"),
        _c("source_sector", "Source Sector", TEXT, editable=False, width=170, group="Classification"),
        _c("value", "Reported Value", NUMBER, editable=False, width=130, group="Ratio", unit=UNIT_RATIO),
        _c("definition", "Definition", TEXT, editable=False, width=300, group="Methodology"),
        _c("median_eligibility", "Median Eligibility", TEXT, editable=False, width=165, group="Quality"),
        _c("quality_note", "Quality Note", TEXT, editable=False, width=280, group="Quality"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tab 6 — Historical Valuation (computed daily snapshots)
# --------------------------------------------------------------------------

HISTORICAL_VALUATION = Tab(
    id="historical_valuation",
    label="Historical Valuation",
    description="Daily valuation snapshots. Calculated automatically, appended never overwritten.",
    mode="computed_daily",
    key=("symbol", "date"),
    order_by=("date DESC", "symbol"),
    search_columns=("symbol",),
    icon="valuation",
    columns=(
        _c("date", "Date", DATE, editable=False, required=True, width=120, group="Key"),
        _c("symbol", "Symbol", TEXT, editable=False, required=True, width=130, group="Key"),
        _computed("cmp", "CMP", CURRENCY, group="Price"),
        _computed("market_cap", "Market Cap", CURRENCY, width=150, group="Price"),
        _computed("enterprise_value", "Enterprise Value", CURRENCY, width=160, group="Price"),
        _computed("pe", "P/E", NUMBER, group="Multiples"),
        _computed("forward_pe", "Forward P/E", NUMBER, width=130, group="Multiples"),
        _computed("pb", "P/B", NUMBER, group="Multiples"),
        _computed("ev_ebitda", "EV/EBITDA", NUMBER, width=130, group="Multiples"),
        _computed("ev_sales", "EV/Sales", NUMBER, width=120, group="Multiples"),
        _computed("price_sales", "Price/Sales", NUMBER, width=130, group="Multiples"),
        _computed("peg", "PEG", NUMBER, group="Multiples"),
        _computed("dividend_yield", "Dividend Yield", PERCENT, width=140, group="Returns"),
        _computed("roe", "ROE", PERCENT, group="Returns",
                  help="Point-in-time PAT / equity from warehouse statements (Phase 8.3B)."),
        _computed("roce", "ROCE", PERCENT, group="Returns",
                  help="Point-in-time EBIT / capital employed from warehouse statements."),
        _computed("roa", "ROA", PERCENT, group="Returns",
                  help="Point-in-time PAT / assets from warehouse statements."),
        _computed("beta", "Beta", NUMBER, group="Risk"),
        _computed("upside", "Upside", PERCENT, group="Consensus",
                  help="(Target Price - CMP) / CMP"),
        _computed("sector_median", "Sector Median P/E", NUMBER, width=160, group="Relative"),
        _computed("industry_median", "Industry Median P/E", NUMBER, width=170, group="Relative"),
        _computed("percentile", "Percentile", NUMBER, width=120, group="Relative"),
        _computed("relative_valuation_score", "Relative Valuation Score", NUMBER, width=200,
                  group="Relative"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tab 6b/6c — Point-in-time live valuation state and permanent snapshots
# --------------------------------------------------------------------------

_PIT_VALUATION_COLUMNS = (
    _c("symbol", "Symbol", TEXT, editable=False, required=True, width=130, group="Key"),
    _computed("price", "Price", CURRENCY, group="Market", unit=UNIT_INR),
    _computed("volume", "Volume", NUMBER, group="Market", unit=UNIT_COUNT),
    _computed("market_cap", "Market Cap", CURRENCY, width=150, group="Market", unit=UNIT_INR_MILLION),
    _computed("enterprise_value", "Enterprise Value", CURRENCY, width=160, group="Market", unit=UNIT_INR_MILLION),
    _computed("pe", "P/E", NUMBER, group="Valuation", unit=UNIT_RATIO),
    _computed("pb", "P/B", NUMBER, group="Valuation", unit=UNIT_RATIO),
    _computed("ptbv", "P/TBV", NUMBER, group="Valuation", unit=UNIT_RATIO),
    _computed("ev_ebitda", "EV/EBITDA", NUMBER, width=130, group="Valuation", unit=UNIT_RATIO),
    _computed("ev_sales", "EV/Sales", NUMBER, width=120, group="Valuation", unit=UNIT_RATIO),
    _computed("fcf_yield", "FCF Yield", PERCENT, width=120, group="Valuation", unit=UNIT_PERCENT),
    _computed("net_debt_ebitda", "Net Debt/EBITDA", NUMBER, width=160, group="Fundamentals", unit=UNIT_RATIO),
    _computed("roe", "ROE", PERCENT, group="Fundamentals", unit=UNIT_PERCENT),
    _computed("roa", "ROA", PERCENT, group="Fundamentals", unit=UNIT_PERCENT),
    _computed("ebitda_margin", "EBITDA Margin", PERCENT, width=150, group="Fundamentals", unit=UNIT_PERCENT),
    _c("price_as_of", "Price As Of", DATETIME, editable=False, required=True, width=180, group="PIT"),
    _c("fundamental_as_of", "Fundamental As Of", DATE, editable=False, required=True, width=160, group="PIT"),
    _c("fundamental_publication_date", "Financial Publication", DATETIME, editable=False, required=True, width=190, group="PIT"),
    _c("calculation_timestamp", "Calculated At", DATETIME, editable=False, required=True, width=180, group="PIT"),
    _c("fundamental_vintage_id", "Fundamental Vintage", TEXT, editable=False, required=True, width=210, group="PIT"),
    _c("price_source", "Price Source", TEXT, editable=False, width=150, group="Provenance"),
    _c("fundamental_source", "Fundamental Source", TEXT, editable=False, width=170, group="Provenance"),
    _c("calculation_version", "Calculation Version", TEXT, editable=False, width=170, group="Provenance"),
    _c("quality_status", "Quality Status", TEXT, editable=False, width=150, group="Quality"),
    _c("missing_inputs", "Missing Inputs", JSON, editable=False, width=260, group="Quality"),
)

LIVE_VALUATION_STATE = Tab(
    id="live_valuation_state", label="Live Valuation State",
    description="Latest PIT-valid valuation state per company. Updated in place; not historical evidence.",
    mode="computed", key=("symbol",), order_by=("symbol",), search_columns=("symbol",), icon="valuation",
    notes=("Current state only; permanent observations are stored in Valuation Snapshots.",),
    columns=(*_PIT_VALUATION_COLUMNS, *PROVENANCE_COLUMNS),
)

VALUATION_SNAPSHOTS = Tab(
    id="valuation_snapshots", label="Valuation Snapshots",
    description="Append-only PIT valuation observations triggered by time, material price moves and company events.",
    mode="append", key=("symbol", "calculation_timestamp", "snapshot_reason"),
    order_by=("calculation_timestamp DESC", "symbol"), search_columns=("symbol", "snapshot_reason"), icon="valuation",
    notes=("Never overwrites fiscal ratio history.", "Every denominator must have been public by price_as_of."),
    columns=(
        *_PIT_VALUATION_COLUMNS,
        _c("snapshot_reason", "Snapshot Reason", TEXT, editable=False, required=True, width=180, group="Trigger"),
        _computed("price_move_pct", "Price Move %", PERCENT, width=130, group="Trigger", unit=UNIT_PERCENT),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tab 7 — Consensus
# --------------------------------------------------------------------------

CONSENSUS = Tab(
    id="consensus",
    label="Consensus",
    description="Capital IQ sell-side consensus. Appended daily.",
    mode="append",
    key=("symbol", "consensus_date"),
    order_by=("consensus_date DESC", "symbol"),
    search_columns=("symbol",),
    icon="consensus",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=130, group="Key"),
        _c("consensus_date", "Consensus Date", DATE, required=True, width=140, group="Key"),
        _c("target_price", "Target Price", CURRENCY, width=130, group="Targets"),
        _c("high_target", "High Target", CURRENCY, width=130, group="Targets"),
        _c("low_target", "Low Target", CURRENCY, width=130, group="Targets"),
        _c("buy", "Buy", INTEGER, width=80, group="Ratings"),
        _c("outperform", "Outperform", INTEGER, width=120, group="Ratings"),
        _c("hold", "Hold", INTEGER, width=90, group="Ratings"),
        _c("sell", "Sell", INTEGER, width=80, group="Ratings"),
        _c("no_opinion", "No Opinion", INTEGER, width=120, group="Ratings"),
        _computed("analyst_count", "Analyst Count", INTEGER, width=130, group="Ratings"),
        _computed("target_dispersion", "Target Dispersion", PERCENT, width=160, group="Targets",
                  help="(High - Low) / Target"),
        *PROVENANCE_COLUMNS,
    ),
)

CONSENSUS_METRIC_VINTAGES = Tab(
    id="consensus_metric_vintages",
    label="Consensus Metric Vintages",
    description="Immutable point-in-time sell-side estimates by target period and financial metric.",
    mode="append",
    key=("symbol", "consensus_date", "target_period", "metric"),
    entity_column="symbol",
    order_by=("consensus_date DESC", "symbol", "target_period", "metric"),
    search_columns=("symbol", "target_period", "metric"),
    icon="consensus",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=130, group="Key"),
        _c("consensus_date", "Consensus Date", DATE, required=True, width=140, group="Key"),
        _c("target_period", "Target Period", TEXT, required=True, width=130, group="Key"),
        _c("metric", "Metric", TEXT, required=True, width=140, group="Key"),
        _c("mean_estimate", "Mean Estimate", NUMBER, required=True, width=150, group="Estimate"),
        _c("median_estimate", "Median Estimate", NUMBER, width=160, group="Estimate"),
        _c("high_estimate", "High Estimate", NUMBER, width=150, group="Estimate"),
        _c("low_estimate", "Low Estimate", NUMBER, width=140, group="Estimate"),
        _c("analyst_count", "Analyst Count", INTEGER, width=130, group="Breadth"),
        _c("currency", "Currency", TEXT, width=100, group="Units"),
        _c("unit", "Unit", TEXT, width=120, group="Units"),
        _c("isin", "ISIN", TEXT, width=140, group="Key"),
        _c("target_period_end", "Period End", DATE, width=130, group="Key"),
        # Whether target_period came from the vendor or was derived. The 2026-08
        # Capital IQ vintage export returned "(Invalid Time Period)" for every
        # period-end cell, so those labels are derived from the as-of date on an
        # Indian fiscal calendar. A derived label must never read as vendor-supplied.
        _c("period_source", "Period Source", TEXT, width=160, group="Provenance",
           options=("vendor", "derived_indian_fy")),
        _c("is_forward_estimate", "Forward Estimate", TEXT, width=150, group="Estimate",
           options=("true", "false")),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tab 8 — Research Intelligence
# --------------------------------------------------------------------------

RESEARCH_INTELLIGENCE = Tab(
    id="research_intelligence",
    label="Research Intelligence",
    description="Structured document intelligence: what management said, and what it implies.",
    mode="structured",
    key=("symbol", "document_type", "fiscal_period"),
    order_by=("symbol", "fiscal_period DESC"),
    search_columns=("symbol", "document_type", "fiscal_period", "summary", "management_themes"),
    icon="research",
    columns=(
        _c("symbol", "Company", TEXT, required=True, width=130, group="Key"),
        _c("document_type", "Document Type", TEXT, required=True, width=150, group="Key",
           options=("annual_report", "quarterly_results", "transcript", "presentation", "filing", "note")),
        _c("fiscal_period", "Fiscal Period", TEXT, required=True, width=130, group="Key"),
        _c("management_themes", "Management Themes", TEXT, width=260, group="Narrative"),
        _c("strategy", "Strategy", TEXT, width=240, group="Narrative"),
        _c("risks", "Risks", TEXT, width=240, group="Narrative"),
        _c("opportunities", "Opportunities", TEXT, width=240, group="Narrative"),
        _c("capital_allocation", "Capital Allocation", TEXT, width=220, group="Narrative"),
        _c("guidance", "Guidance", TEXT, width=220, group="Narrative"),
        _c("events", "Events", TEXT, width=200, group="Narrative"),
        _c("summary", "Summary", TEXT, width=320, group="Narrative"),
        _c("confidence", "Confidence", NUMBER, width=110, group="Quality"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tab 9 — Historical Research Timeline
# --------------------------------------------------------------------------

RESEARCH_TIMELINE = Tab(
    id="research_timeline",
    label="Research Timeline",
    description="Chronological company history: what happened, when, and what changed.",
    mode="append",
    key=("symbol", "date", "event"),
    order_by=("date DESC", "symbol"),
    search_columns=("symbol", "event", "results", "management"),
    icon="timeline",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=130, group="Key"),
        _c("date", "Date", DATE, required=True, width=120, group="Key"),
        _c("event", "Event", TEXT, required=True, width=260, group="Event"),
        _c("guidance", "Guidance", TEXT, width=220, group="Event"),
        _c("management", "Management", TEXT, width=200, group="Event"),
        _c("results", "Results", TEXT, width=220, group="Event"),
        _c("acquisitions", "Acquisitions", TEXT, width=180, group="Corporate"),
        _c("divestments", "Divestments", TEXT, width=180, group="Corporate"),
        _c("capital_allocation", "Capital Allocation", TEXT, width=200, group="Corporate"),
        _c("major_risks", "Major Risks", TEXT, width=220, group="Risk"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tab 10 — Corporate Actions
# --------------------------------------------------------------------------

CORPORATE_ACTIONS = Tab(
    id="corporate_actions",
    label="Corporate Actions",
    description="Dividends, splits, bonuses, buybacks and structural changes.",
    mode="append",
    key=("symbol", "action_date", "action_type"),
    order_by=("action_date DESC", "symbol"),
    search_columns=("symbol", "action_type", "details"),
    icon="actions",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=130, group="Key"),
        _c("action_date", "Date", DATE, required=True, width=120, group="Key"),
        _c("action_type", "Action Type", TEXT, required=True, width=140, group="Key",
           options=("dividend", "split", "bonus", "rights", "buyback", "merger",
                    "demerger", "name_change", "symbol_change")),
        _c("dividend", "Dividend", CURRENCY, width=120, group="Cash"),
        _c("split", "Split", TEXT, width=110, group="Structure"),
        _c("bonus", "Bonus", TEXT, width=110, group="Structure"),
        _c("rights", "Rights", TEXT, width=110, group="Structure"),
        _c("buyback", "Buyback", TEXT, width=120, group="Structure"),
        _c("merger", "Merger", TEXT, width=160, group="Structure"),
        _c("demerger", "Demerger", TEXT, width=160, group="Structure"),
        _c("name_change", "Name Change", TEXT, width=160, group="Identity"),
        _c("symbol_change", "Symbol Change", TEXT, width=150, group="Identity"),
        _c("details", "Details", TEXT, width=280, group="Detail"),
        _c("announcement_date", "Announcement Date", DATE, width=150, group="Dates"),
        _c("effective_date", "Effective Date", DATE, width=140, group="Dates"),
        _c("confidence", "Confidence", NUMBER, width=110, group="Quality",
           help="1.0 primary NSE/LIDI; lower when secondary (e.g. Upstox) or conflicted"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tab 11 — Ownership
# --------------------------------------------------------------------------

OWNERSHIP = Tab(
    id="ownership",
    label="Ownership",
    description="Historical shareholding snapshots by quarter.",
    mode="append",
    key=("symbol", "as_of"),
    order_by=("as_of DESC", "symbol"),
    search_columns=("symbol",),
    icon="ownership",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=130, group="Key"),
        _c("as_of", "As Of", DATE, required=True, width=120, group="Key"),
        _c("promoter_holding", "Promoter", PERCENT, width=120, group="Holders"),
        _c("institutional_holding", "Institutional", PERCENT, width=130, group="Holders"),
        _c("fii", "FII", PERCENT, width=100, group="Holders"),
        _c("dii", "DII", PERCENT, width=100, group="Holders"),
        _c("mutual_funds", "Mutual Funds", PERCENT, width=130, group="Holders"),
        _c("insider_holding", "Insider", PERCENT, width=110, group="Holders"),
        _c("public_holding", "Public", PERCENT, width=110, group="Holders"),
        _c("government_holding", "Government", PERCENT, width=120, group="Holders"),
        _c("others_holding", "Others", PERCENT, width=110, group="Holders"),
        _c("confidence", "Confidence", NUMBER, width=110, group="Quality"),
        _c("dqiv_status", "DQIV", TEXT, width=110, group="Quality"),
        _c("validation_notes", "Notes", TEXT, width=220, group="Quality"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tab — Insider Trades
# --------------------------------------------------------------------------

FUNDAMENTALS_REFRESH_QUEUE = Tab(
    id="fundamentals_refresh_queue",
    label="Fundamentals Refresh Queue",
    description=(
        "Companies owed an Upstox statement refresh, why they are owed it, and "
        "how far the refresh got. Durable so a deploy cannot lose the work."
    ),
    mode="upsert",
    # One entry per company and reporting period. A company that reports Q1 and
    # then restates it is owed two refreshes of the same period, not two
    # entries; a company that reports Q1 and then Q2 is owed two.
    key=("symbol", "reporting_period"),
    order_by=("queued_at DESC", "symbol"),
    search_columns=("symbol", "status", "trigger"),
    icon="queue",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=130, group="Key"),
        # The period that prompted the refresh, so a stale entry can be told
        # from a current one without guessing from timestamps.
        _c("reporting_period", "Period", TEXT, required=True, width=130, group="Key"),
        _c("status", "Status", TEXT, required=True, width=120, group="State",
           options=("PENDING", "RUNNING", "SUCCESS", "RETRY", "FAILED")),
        # Why this company is in the queue. Recorded because a queue nobody can
        # explain is a queue nobody will trust enough to drain.
        _c("trigger", "Trigger", TEXT, width=180, group="State",
           options=("new_period", "restated_period", "reconciliation", "manual")),
        _c("attempts", "Attempts", INTEGER, width=100, group="State"),
        _c("queued_at", "Queued", DATETIME, width=170, group="Timing"),
        _c("started_at", "Started", DATETIME, width=170, group="Timing"),
        _c("finished_at", "Finished", DATETIME, width=170, group="Timing"),
        _c("last_error", "Last Error", TEXT, width=260, group="State"),
        # SUCCESS says the refresh ran without error. This says whether it
        # changed anything. The live trial produced six SUCCESS entries that
        # wrote nothing, and without this column that is indistinguishable from
        # six quarters landing.
        _c("outcome", "Outcome", TEXT, width=140, group="Result",
           options=("UPDATED", "NO_CHANGE")),
        _c("datasets_written", "Datasets", TEXT, width=200, group="Result"),
        _c("periods_written", "Periods Written", INTEGER, width=140, group="Result"),
        _c("periods_preserved", "Periods Preserved", INTEGER, width=150, group="Result"),
        *PROVENANCE_COLUMNS,
    ),
)


INSIDER_TRADES = Tab(
    id="insider_trades",
    label="Insider Trades",
    description="Exchange-reported insider and SAST disclosures, one row per filing.",
    mode="append",
    # The export identifies companies by trade name, not ticker, and covers a
    # wider universe than company_master holds - 411 companies of which only a
    # third resolve to a symbol. Keying on the name keeps every disclosure;
    # symbol is an enrichment that is filled where it can be, and left empty
    # rather than guessed.
    #
    # A person can file more than once for one company on one day, so the key
    # also carries the trade fingerprint. Without quantity and mode, a promoter
    # buying twice in a session would collapse into a single row.
    key=("company_name", "reported_on", "person", "action", "quantity", "mode"),
    order_by=("reported_on DESC", "value DESC"),
    search_columns=("symbol", "company_name", "person"),
    icon="ownership",
    columns=(
        _c("company_name", "Company", TEXT, required=True, width=220, group="Key"),
        _c("reported_on", "Reported", DATE, required=True, width=120, group="Key"),
        _c("person", "Insider", TEXT, required=True, width=200, group="Key"),
        _c("action", "Action", TEXT, required=True, width=120, group="Key"),
        _c("quantity", "Quantity", NUMBER, required=True, width=130, group="Key"),
        _c("mode", "Mode", TEXT, required=True, width=150, group="Key"),
        _c("symbol", "Symbol", TEXT, width=130, group="Company"),
        _c("symbol_match", "Match", TEXT, width=120, group="Company"),
        _c("category", "Category", TEXT, width=170, group="Insider"),
        _c("value", "Value", CURRENCY, width=150, group="Trade"),
        _c("avg_price", "Avg Price", CURRENCY, width=120, group="Trade"),
        _c("traded_pct", "Traded %", PERCENT, width=110, group="Trade"),
        _c("post_holding", "Post Holding", NUMBER, width=140, group="Trade"),
        _c("regulation", "Regulation", TEXT, width=160, group="Filing"),
        _c("security_type", "Security", TEXT, width=130, group="Filing"),
        _c("period", "Period", TEXT, width=180, group="Filing"),
        # Market purchases are a different signal from gifts and off-market
        # transfers; keeping the raw mode alongside a normalised flag lets the
        # page separate them without re-deriving the rule.
        _c("is_open_market", "Open Market", TEXT, width=120, group="Filing"),
        # Two disclosure regimes arrive in one export and mean different things.
        # An insider filing is a director or promoter trading their own company;
        # a SAST filing is an acquirer crossing a shareholding threshold under
        # the takeover code. SAST filings never carry a price - 0 of 411 - so
        # mixing them in makes value coverage look like a data problem when it
        # is simply two populations.
        _c("regime", "Regime", TEXT, width=110, group="Filing"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tab — Share Count History (Phase 7.4F FWCP)
# --------------------------------------------------------------------------

SHARE_COUNT_HISTORY = Tab(
    id="share_count_history",
    label="Share Count History",
    description=(
        "Point-in-time share counts for HVIE, EPS, BVPS, market cap and EV. "
        "Never stores PE/PB/EV — those remain HVIE reconstructions."
    ),
    mode="append",
    key=("symbol", "as_of", "source"),
    order_by=("as_of DESC", "symbol"),
    search_columns=("symbol",),
    icon="shares",
    notes=(
        "Prefer diluted / weighted-average when available. "
        "Negative or zero share counts are rejected by FWCP DQIV.",
    ),
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=130, group="Key"),
        _c("as_of", "As Of", DATE, required=True, width=120, group="Key"),
        _c("basic_shares", "Basic Shares", NUMBER, width=150, group="Shares", unit=UNIT_COUNT),
        _c("diluted_shares", "Diluted Shares", NUMBER, width=150, group="Shares", unit=UNIT_COUNT),
        _c("weighted_average_shares", "Weighted Avg Shares", NUMBER, width=180, group="Shares",
           unit=UNIT_COUNT),
        _c("shares_outstanding", "Shares Outstanding", NUMBER, width=170, group="Shares",
           unit=UNIT_COUNT, help="Canonical share count used by HVIE / market cap"),
        _c("free_float_shares", "Free Float", NUMBER, width=140, group="Shares", unit=UNIT_COUNT),
        _c("statement_type", "Statement Type", TEXT, width=140, group="Identity",
           options=STATEMENT_TYPES),
        _c("fiscal_period", "Fiscal Period", TEXT, width=130, group="Identity"),
        _c("confidence", "Confidence", NUMBER, width=110, group="Quality"),
        _c("dqiv_status", "DQIV", TEXT, width=110, group="Quality"),
        _c("validation_notes", "Notes", TEXT, width=220, group="Quality"),
        *PROVENANCE_COLUMNS,
    ),
)

FWCP_IMPORT_QUEUE = Tab(
    id="fwcp_import_queue",
    label="FWCP Import Queue",
    description="Financial Warehouse Completion Programme import / retry queue.",
    mode="master",
    key=("symbol",),
    order_by=("updated_at DESC", "symbol"),
    search_columns=("symbol", "queue_status", "blocking_reason"),
    icon="queue",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=130, group="Key"),
        _c("queue_status", "Queue Status", TEXT, width=140, group="Runtime",
           options=("PENDING", "RUNNING", "RETRY", "COMPLETED", "FAILED", "SKIPPED")),
        _c("lifecycle", "Lifecycle", TEXT, width=160, group="Runtime"),
        _c("pack", "Active Pack", TEXT, width=160, group="Runtime"),
        _c("blocking_reason", "Blocking Reason", TEXT, width=200, group="Health"),
        _c("attempts", "Attempts", INTEGER, width=100, group="Runtime"),
        _c("last_error", "Last Error", TEXT, width=280, group="Health"),
        _c("annual_ok", "Annual OK", BOOL, width=100, group="Coverage"),
        _c("quarterly_ok", "Quarterly OK", BOOL, width=110, group="Coverage"),
        _c("share_count_ok", "Share Count OK", BOOL, width=130, group="Coverage"),
        _c("consensus_ok", "Consensus OK", BOOL, width=120, group="Coverage"),
        _c("ownership_ok", "Ownership OK", BOOL, width=120, group="Coverage"),
        _c("peers_ok", "Peers OK", BOOL, width=100, group="Coverage"),
        _c("profile_ok", "Profile OK", BOOL, width=110, group="Coverage"),
        _c("last_run_at", "Last Run", DATETIME, width=170, group="Health"),
        _c("next_retry_at", "Next Retry", DATETIME, width=170, group="Health"),
        _c("completed_at", "Completed At", DATETIME, width=170, group="Health"),
        _c("updated_at", "Updated At", DATETIME, width=170, group="Health"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tab 12 — Hedge Fund Factors (computed)
# --------------------------------------------------------------------------

HEDGE_FUND_FACTORS = Tab(
    id="hedge_fund_factors",
    label="Hedge Fund Factors",
    description="Cross-sectional factor scores computed from the warehouse. Read only.",
    mode="computed",
    key=("symbol", "as_of"),
    order_by=("as_of DESC", "opportunity_score DESC"),
    search_columns=("symbol",),
    icon="factors",
    columns=(
        _c("symbol", "Symbol", TEXT, editable=False, required=True, width=130, group="Key"),
        _c("as_of", "As Of", DATE, editable=False, required=True, width=120, group="Key"),
        _computed("value_score", "Value", NUMBER, group="Factors"),
        _computed("quality_score", "Quality", NUMBER, group="Factors"),
        _computed("growth_score", "Growth", NUMBER, group="Factors"),
        _computed("momentum_score", "Momentum", NUMBER, group="Factors"),
        _computed("technical_score", "Technical", NUMBER, group="Factors"),
        _computed("trend_score", "Trend", NUMBER, group="Technical Detail"),
        _computed("momentum_12_1_pct", "12–1 Momentum %", NUMBER, group="Technical Detail"),
        _computed("volume_ratio_20d", "20D Volume Ratio", NUMBER, group="Technical Detail"),
        _computed("consensus_score", "Consensus", NUMBER, group="Factors"),
        _computed("dividend_score", "Dividend", NUMBER, group="Factors"),
        _computed("risk_score", "Risk", NUMBER, group="Factors"),
        _computed("opportunity_score", "Opportunity", NUMBER, width=140, group="Composite"),
        _computed("strategy_agreement", "Strategy Agreement", INTEGER, width=170, group="Composite"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tab 12b — Daily Intelligence Changes (prepared post-close feed)
# --------------------------------------------------------------------------

DAILY_INTELLIGENCE_CHANGES = Tab(
    id="daily_intelligence_changes",
    label="Daily Intelligence Changes",
    description=(
        "Prepared post-close summary of material fundamental and Alpha-score "
        "changes. This is a cached research feed, not a trading signal."
    ),
    mode="append",
    key=("symbol", "date", "change_type"),
    order_by=("date DESC", "symbol", "change_type"),
    search_columns=("symbol", "change_type", "summary", "changed_fields"),
    icon="timeline",
    notes=(
        "Written only by the bounded daily intelligence refresh after a source update.",
        "No page request performs this calculation.",
    ),
    columns=(
        _c("symbol", "Symbol", TEXT, editable=False, required=True, width=130, group="Key"),
        _c("date", "Date", DATE, editable=False, required=True, width=120, group="Key"),
        _c("change_type", "Change Type", TEXT, editable=False, required=True, width=150, group="Key",
           options=("fundamentals", "alpha", "initial_refresh", "no_material_change")),
        _c("summary", "What Changed", TEXT, editable=False, width=420, group="Change"),
        _c("changed_fields", "Changed Fields", JSON, editable=False, width=360, group="Change"),
        _c("previous_snapshot", "Previous Snapshot", JSON, editable=False, width=320, group="Audit"),
        _c("current_snapshot", "Current Snapshot", JSON, editable=False, width=320, group="Audit"),
        _c("refresh_run_id", "Refresh Run", TEXT, editable=False, width=180, group="Audit"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tab 13 — Company Intelligence
# --------------------------------------------------------------------------

COMPANY_INTELLIGENCE = Tab(
    id="company_intelligence",
    label="Company Intelligence",
    description="Generated business understanding — reviewed and editable by admins.",
    mode="generated",
    key=("symbol",),
    order_by=("symbol",),
    search_columns=("symbol", "business_summary", "investment_thesis", "moat"),
    icon="intelligence",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=130, group="Key"),
        _c("business_summary", "Business Summary", TEXT, width=320, group="Business"),
        _c("industry_summary", "Industry Summary", TEXT, width=300, group="Business"),
        _c("investment_thesis", "Investment Thesis", TEXT, width=320, group="View"),
        _c("key_risks", "Key Risks", TEXT, width=260, group="View"),
        _c("catalysts", "Catalysts", TEXT, width=260, group="View"),
        _c("moat", "Moat", TEXT, width=220, group="Quality"),
        _c("competitive_position", "Competitive Position", TEXT, width=240, group="Quality"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tab 14 — Data Quality (internal)
# --------------------------------------------------------------------------

DATA_QUALITY = Tab(
    id="data_quality",
    label="Data Quality",
    description="Internal health board: rows, gaps, freshness and validation status per table.",
    mode="internal",
    key=("table_id",),
    order_by=("table_id",),
    entity_column=None,
    search_columns=("table_id", "validation_status"),
    icon="quality",
    columns=(
        _c("table_id", "Table", TEXT, editable=False, required=True, width=200, group="Key"),
        _computed("rows", "Rows", INTEGER, width=110, group="Volume"),
        _computed("companies", "Companies", INTEGER, width=120, group="Volume"),
        _computed("missing_values", "Missing Values", INTEGER, width=150, group="Gaps"),
        _computed("missing_pct", "Missing %", PERCENT, width=120, group="Gaps"),
        _c("last_refresh", "Last Refresh", DATETIME, editable=False, width=180, group="Freshness"),
        _computed("errors", "Errors", INTEGER, width=100, group="Validation"),
        _c("validation_status", "Validation Status", TEXT, editable=False, width=150,
           group="Validation", options=("ok", "warn", "fail", "empty")),
        _c("freshness", "Freshness", TEXT, editable=False, width=140, group="Freshness"),
        *PROVENANCE_COLUMNS,
    ),
)


# --------------------------------------------------------------------------
# Tab — Institutional Flow (exchange-level FII/DII)
# --------------------------------------------------------------------------

INSTITUTIONAL_FLOW = Tab(
    id="institutional_flow",
    label="Institutional Flow",
    description="Exchange-level FII/DII net flows. Appended daily from Upstox via DQIV gateway.",
    mode="append",
    key=("date", "segment", "interval"),
    order_by=("date DESC",),
    search_columns=("segment",),
    icon="flow",
    columns=(
        _c("date", "Date", DATE, required=True, width=120, group="Key"),
        _c("segment", "Segment", TEXT, required=True, width=190, group="Key", options=("NSE_EQ", "CASH", "NSE_EQ|CASH", "NSE_FO|INDEX_FUTURES", "NSE_FO|STOCK_FUTURES", "NSE_FO|INDEX_OPTIONS", "NSE_FO|STOCK_OPTIONS")),
        _c("interval", "Interval", TEXT, width=90, group="Key", options=("1D", "1M")),
        _c("fii_net", "FII Net (₹ Cr)", NUMBER, width=140, group="Flow"),
        _c("dii_net", "DII Net (₹ Cr)", NUMBER, width=140, group="Flow"),
        _c("fii_buy", "FII Buy", NUMBER, width=120, group="Flow"),
        _c("fii_sell", "FII Sell", NUMBER, width=120, group="Flow"),
        _c("dii_buy", "DII Buy", NUMBER, width=120, group="Flow"),
        _c("dii_sell", "DII Sell", NUMBER, width=120, group="Flow"),
        _c("fii_buy_contracts", "FII Buy Contracts", NUMBER, width=150, group="Derivatives"),
        _c("fii_sell_contracts", "FII Sell Contracts", NUMBER, width=150, group="Derivatives"),
        _c("fii_oi_contracts", "FII OI Contracts", NUMBER, width=150, group="Derivatives"),
        _c("fii_oi_amount", "FII OI Amount", NUMBER, width=140, group="Derivatives"),
        _c("fii_long_contracts", "FII Long Contracts", NUMBER, width=150, group="Derivatives"),
        _c("fii_short_contracts", "FII Short Contracts", NUMBER, width=150, group="Derivatives"),
        _c("fii_call_long_contracts", "FII Call Long", NUMBER, width=140, group="Options"),
        _c("fii_put_long_contracts", "FII Put Long", NUMBER, width=140, group="Options"),
        _c("fii_call_short_contracts", "FII Call Short", NUMBER, width=140, group="Options"),
        _c("fii_put_short_contracts", "FII Put Short", NUMBER, width=140, group="Options"),
        _c("time_stamp", "Provider Timestamp", NUMBER, width=160, group="Provenance"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tab — Valuation Ratios (Upstox key-ratios, append-only snapshots)
# --------------------------------------------------------------------------

VALUATION_RATIOS = Tab(
    id="valuation_ratios",
    label="Valuation Ratios",
    description=(
        "Provider-reported valuation ratios (P/E, P/B, ROA, ROE, ROCE, EV/EBITDA) "
        "with sector benchmarks. Append-only daily snapshots from Upstox via DQIV."
    ),
    mode="append",
    key=("symbol", "ratio_name", "reported_date", "snapshot_id"),
    order_by=("reported_date DESC", "symbol", "ratio_name"),
    search_columns=("symbol", "isin", "ratio_name", "company_id"),
    icon="valuation",
    columns=(
        _c("company_id", "Company ID", TEXT, width=140, group="Identity"),
        _c("symbol", "Symbol", TEXT, required=True, width=120, group="Identity"),
        _c("isin", "ISIN", TEXT, required=True, width=140, group="Identity"),
        _c("instrument_key", "Instrument Key", TEXT, width=180, group="Identity"),
        _c("ratio_name", "Ratio", TEXT, required=True, width=120, group="Ratio",
           options=("pe", "pb", "roa", "roe", "roce", "ev_ebitda")),
        _c("company_value", "Company Value", NUMBER, required=True, width=130, group="Ratio",
           unit=UNIT_RATIO),
        _c("sector_value", "Sector Value", NUMBER, width=130, group="Ratio", unit=UNIT_RATIO),
        _c("reported_date", "Reported Date", DATE, required=True, width=130, group="Snapshot"),
        _c("reported_time", "Reported Time", DATETIME, width=170, group="Snapshot"),
        _c("snapshot_id", "Snapshot ID", TEXT, required=True, width=180, group="Snapshot"),
        _c("provider", "Provider", TEXT, width=120, group="Provenance"),
        _c("provider_version", "Provider Version", TEXT, width=140, group="Provenance"),
        _c("confidence", "Confidence", TEXT, width=110, group="Quality"),
        _c("dqiv_status", "DQIV Status", TEXT, width=120, group="Quality"),
        # Whether the snapshot this row belongs to carried all six ratios.
        #
        # Upstox sometimes returns five. Promoting the five is right - they are
        # real values - but a reader must be able to tell a snapshot that was
        # incomplete from one where the sixth ratio simply does not apply.
        # Without this the gap looks like ordinary absence and nobody questions
        # it.
        _c("snapshot_completeness", "Snapshot", TEXT, width=120, group="Quality",
           options=("complete", "partial")),
        _c("snapshot_ratios_present", "Ratios Present", INTEGER, width=130,
           group="Quality"),
        # A bank without ROCE is complete for a bank; a manufacturer without it
        # has a gap. The same absence, two different facts, and only this column
        # keeps every lender from reading as permanently degraded.
        _c("snapshot_state", "State", TEXT, width=140, group="Quality",
           options=("FRESH", "PARTIAL_VALID", "NOT_APPLICABLE", "STALE")),
        _c("validation_notes", "Validation Notes", TEXT, width=220, group="Quality"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tab — Bootstrap Runs (Phase 7.4d one-shot universe backfill)
# --------------------------------------------------------------------------

BOOTSTRAP_RUNS = Tab(
    id="bootstrap_runs",
    label="Bootstrap Runs",
    description="One-shot Upstox valuation bootstrap run summaries (append-only).",
    mode="append",
    key=("run_id",),
    order_by=("started_at DESC",),
    search_columns=("run_id", "status"),
    icon="ops",
    columns=(
        _c("run_id", "Run ID", TEXT, required=True, width=160, group="Key"),
        _c("started_at", "Start Time", DATETIME, width=170, group="Timing"),
        _c("ended_at", "End Time", DATETIME, width=170, group="Timing"),
        _c("companies", "Companies", INTEGER, width=110, group="Counts"),
        _c("success", "Success", INTEGER, width=100, group="Counts"),
        _c("failed", "Failed", INTEGER, width=100, group="Counts"),
        _c("skipped", "Skipped", INTEGER, width=100, group="Counts"),
        _c("coverage", "Coverage %", NUMBER, width=110, group="Stats"),
        _c("average_speed", "Avg Speed (cpm)", NUMBER, width=130, group="Stats"),
        _c("average_latency", "Avg Latency (ms)", NUMBER, width=140, group="Stats"),
        _c("http_429_count", "429 Count", INTEGER, width=100, group="Stats"),
        _c("retry_count", "Retry Count", INTEGER, width=110, group="Stats"),
        _c("status", "Status", TEXT, width=120, group="Status",
           options=("idle", "running", "paused", "completed", "stopped")),
        *PROVENANCE_COLUMNS,
    ),
)

INGESTION_HEALTH = Tab(
    id="ingestion_health",
    label="Ingestion Health",
    description="Per-feed warehouse ingestion health snapshot for ops dashboards.",
    mode="master",
    # Identity column must not be named "source" — that key is reserved by PROVENANCE_COLUMNS.
    key=("feed",),
    order_by=("feed",),
    search_columns=("feed", "health", "notes"),
    icon="ops",
    columns=(
        _c("feed", "Feed", TEXT, required=True, width=160, group="Key"),
        _c("coverage", "Coverage %", NUMBER, width=120, group="Health"),
        _c("rows", "Rows", INTEGER, width=110, group="Health"),
        _c("successful", "Successful", INTEGER, width=120, group="Health"),
        _c("failed", "Failed", INTEGER, width=100, group="Health"),
        _c("average_latency", "Avg Latency (ms)", NUMBER, width=140, group="Health"),
        _c("last_refresh", "Last Refresh", DATETIME, width=170, group="Health"),
        _c("health", "Health", TEXT, width=110, group="Health",
           options=("ok", "warn", "critical", "empty")),
        _c("notes", "Notes", TEXT, width=280, group="Health"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Tabs — HVIE Continuous Runtime (Phase 8.3R)
# --------------------------------------------------------------------------

HVIE_COMPANY_STATE = Tab(
    id="hvie_company_state",
    label="HVIE Company State",
    description="Per-company HVIE runtime lifecycle: bootstrap once, then daily append.",
    mode="master",
    key=("symbol",),
    order_by=("symbol",),
    search_columns=("symbol", "status", "seeded"),
    icon="ops",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=120, group="Key"),
        _c("status", "Status", TEXT, width=130, group="Lifecycle",
           options=("PENDING", "BOOTSTRAPPING", "SEEDED", "DAILY", "FORWARD_REBUILD",
                    "CA_REBUILD", "FAILED", "SKIPPED")),
        _c("seeded", "Seeded", BOOL, width=100, group="Lifecycle"),
        _c("bootstrap_at", "Bootstrap At", DATETIME, width=170, group="Lifecycle"),
        _c("last_observation_date", "Last Observation", DATE, width=140, group="Lifecycle"),
        _c("last_daily_at", "Last Daily Append", DATETIME, width=170, group="Lifecycle"),
        _c("last_forward_at", "Last Forward Rebuild", DATETIME, width=180, group="Lifecycle"),
        _c("last_ca_at", "Last CA Rebuild", DATETIME, width=170, group="Lifecycle"),
        _c("last_stats_at", "Last Stats Refresh", DATETIME, width=170, group="Lifecycle"),
        _c("observations", "Observations", INTEGER, width=120, group="Coverage"),
        _c("first_observation", "First Observation", DATE, width=140, group="Coverage"),
        _c("primary_metric", "Primary Metric", TEXT, width=130, group="Policy"),
        _c("primary_model", "Primary Model", TEXT, width=160, group="Policy"),
        _c("last_regime", "Last Regime", TEXT, width=140, group="Signals"),
        _c("last_percentile", "Last Percentile", NUMBER, width=140, group="Signals"),
        _c("error", "Error", TEXT, width=280, group="Health"),
        *PROVENANCE_COLUMNS,
    ),
)

HISTORICAL_STATISTICS = Tab(
    id="historical_statistics",
    label="Historical Statistics",
    description="Persisted HVIE rolling statistics by symbol/metric/window (weekly refresh).",
    mode="append",
    key=("symbol", "metric", "window", "as_of"),
    order_by=("as_of DESC", "symbol", "metric"),
    search_columns=("symbol", "metric", "window"),
    icon="valuation",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=120, group="Key"),
        _c("metric", "Metric", TEXT, required=True, width=120, group="Key"),
        _c("window", "Window", TEXT, required=True, width=100, group="Key"),
        _c("as_of", "As Of", DATE, required=True, width=120, group="Key"),
        _c("observation_count", "Observations", INTEGER, width=120, group="Stats"),
        _c("min_value", "Min", NUMBER, width=100, group="Stats"),
        _c("max_value", "Max", NUMBER, width=100, group="Stats"),
        _c("mean_value", "Mean", NUMBER, width=100, group="Stats"),
        _c("median_value", "Median", NUMBER, width=110, group="Stats"),
        _c("stdev", "Stdev", NUMBER, width=100, group="Stats"),
        _c("p25", "P25", NUMBER, width=100, group="Stats"),
        _c("p75", "P75", NUMBER, width=100, group="Stats"),
        _c("current_value", "Current", NUMBER, width=110, group="Stats"),
        _c("current_percentile", "Percentile", NUMBER, width=120, group="Stats"),
        _c("z_score", "Z Score", NUMBER, width=100, group="Stats"),
        _c("premium_to_median_pct", "Premium %", NUMBER, width=120, group="Stats"),
        _c("span_years", "Span Years", NUMBER, width=120, group="Coverage"),
        _c("regime", "Regime", TEXT, width=140, group="Signals"),
        _c("confidence", "Confidence", TEXT, width=110, group="Quality"),
        *PROVENANCE_COLUMNS,
    ),
)

HISTORICAL_SECTOR_MEDIANS = Tab(
    id="historical_sector_medians",
    label="Historical Sector Medians",
    description="Cross-sectional sector median multiples by observation date (weekly).",
    mode="append",
    key=("sector", "metric", "as_of"),
    order_by=("as_of DESC", "sector", "metric"),
    search_columns=("sector", "metric"),
    icon="valuation",
    columns=(
        _c("sector", "Sector", TEXT, required=True, width=160, group="Key"),
        _c("metric", "Metric", TEXT, required=True, width=120, group="Key"),
        _c("as_of", "As Of", DATE, required=True, width=120, group="Key"),
        _c("median_value", "Median", NUMBER, width=120, group="Stats"),
        _c("company_count", "Companies", INTEGER, width=120, group="Stats"),
        *PROVENANCE_COLUMNS,
    ),
)

# ---------------------------------------------------------------------------
# Tab — Historical Import Registry (immutable source fingerprints)
# ---------------------------------------------------------------------------

HISTORICAL_IMPORT_REGISTRY = Tab(
    id="historical_import_registry",
    label="Historical Import Registry",
    description="Auditable fingerprints for seeded historical data sources.",
    mode="append",
    key=("source_name", "source_hash"),
    order_by=("completed_at DESC",),
    search_columns=("source_name", "source_version", "status"),
    icon="audit",
    columns=(
        _c("source_name", "Source", TEXT, editable=False, required=True, width=180, group="Key"),
        _c("source_hash", "SHA256", TEXT, editable=False, required=True, width=240, group="Key"),
        _c("source_version", "Source Version", TEXT, editable=False, width=190, group="Source"),
        _c("rows_read", "Rows Read", INTEGER, editable=False, width=110, group="Counts"),
        _c("rows_imported", "Rows Imported", INTEGER, editable=False, width=130, group="Counts"),
        _c("period_start", "First Period", TEXT, editable=False, width=120, group="Coverage"),
        _c("period_end", "Last Period", TEXT, editable=False, width=120, group="Coverage"),
        _c("status", "Status", TEXT, editable=False, width=120, group="Status",
           options=("COMPLETED", "FAILED")),
        _c("completed_at", "Completed At", DATETIME, editable=False, width=180, group="Timing"),
        _c("error", "Error", TEXT, editable=False, width=300, group="Status"),
        *PROVENANCE_COLUMNS,
    ),
)

HISTORICAL_INDUSTRY_MEDIANS = Tab(
    id="historical_industry_medians",
    label="Historical Industry Medians",
    description="Cross-sectional industry median multiples by observation date.",
    mode="append",
    key=("industry", "metric", "as_of"),
    order_by=("as_of DESC", "industry", "metric"),
    search_columns=("industry", "metric"),
    icon="valuation",
    columns=(
        _c("industry", "Industry", TEXT, required=True, width=180, group="Key"),
        _c("metric", "Metric", TEXT, required=True, width=120, group="Key"),
        _c("as_of", "As Of", DATE, required=True, width=120, group="Key"),
        _c("median_value", "Median", NUMBER, width=120, group="Stats"),
        _c("company_count", "Companies", INTEGER, width=120, group="Stats"),
        *PROVENANCE_COLUMNS,
    ),
)

HISTORICAL_MARKET_MEDIANS = Tab(
    id="historical_market_medians",
    label="Historical Market Medians",
    description="Cross-sectional market median multiples by observation date.",
    mode="append",
    key=("market", "metric", "as_of"),
    order_by=("as_of DESC", "market", "metric"),
    search_columns=("market", "metric"),
    icon="valuation",
    columns=(
        _c("market", "Market", TEXT, required=True, width=140, group="Key"),
        _c("metric", "Metric", TEXT, required=True, width=120, group="Key"),
        _c("as_of", "As Of", DATE, required=True, width=120, group="Key"),
        _c("median_value", "Median", NUMBER, width=120, group="Stats"),
        _c("company_count", "Companies", INTEGER, width=120, group="Stats"),
        *PROVENANCE_COLUMNS,
    ),
)

HVIE_UNIVERSE_QUEUE = Tab(
    id="hvie_universe_queue",
    label="HVIE Universe Queue",
    description="Persisted HVIE universe completion queue — survives redeploys.",
    mode="master",
    key=("symbol",),
    order_by=("queue_status", "symbol"),
    search_columns=("symbol", "queue_status", "lifecycle", "stage", "sector"),
    icon="ops",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=120, group="Key"),
        _c("queue_status", "Queue Status", TEXT, width=130, group="Queue",
           options=("PENDING", "RUNNING", "COMPLETED", "RETRY", "SKIPPED", "FAILED")),
        _c("lifecycle", "Lifecycle", TEXT, width=200, group="Queue",
           options=("NOT_STARTED", "READY", "WAITING_PRICE_HISTORY", "WAITING_STATEMENTS",
                    "WAITING_CORPORATE_ACTIONS", "RUNNING", "FAILED", "COMPLETE")),
        _c("stage", "Stage", TEXT, width=160, group="Pipeline"),
        _c("eligible", "Eligible", BOOL, width=100, group="Eligibility"),
        _c("blocking_reason", "Blocking Reason", TEXT, width=220, group="Eligibility"),
        _c("reason", "Reason", TEXT, width=220, group="Eligibility"),
        _c("history_window_first", "History First", DATE, width=130, group="Coverage"),
        _c("history_window_last", "History Last", DATE, width=130, group="Coverage"),
        _c("observations", "Observations", INTEGER, width=120, group="Coverage"),
        _c("has_statistics", "Statistics", BOOL, width=110, group="Pipeline"),
        _c("has_percentile", "Percentile", BOOL, width=110, group="Pipeline"),
        _c("has_bands", "Bands", BOOL, width=100, group="Pipeline"),
        _c("has_regime", "Regime", BOOL, width=100, group="Pipeline"),
        _c("has_research", "Research", BOOL, width=110, group="Pipeline"),
        _c("last_percentile", "Last Percentile", NUMBER, width=140, group="Signals"),
        _c("last_regime", "Last Regime", TEXT, width=140, group="Signals"),
        _c("primary_metric", "Primary Metric", TEXT, width=130, group="Policy"),
        _c("primary_model", "Primary Model", TEXT, width=160, group="Policy"),
        _c("sector", "Sector", TEXT, width=160, group="Identity"),
        _c("industry", "Industry", TEXT, width=180, group="Identity"),
        _c("attempts", "Attempts", INTEGER, width=100, group="Retry"),
        _c("next_retry_at", "Next Retry", DATETIME, width=170, group="Retry"),
        _c("last_error", "Last Error", TEXT, width=280, group="Health"),
        _c("last_run_at", "Last Run", DATETIME, width=170, group="Health"),
        _c("completed_at", "Completed At", DATETIME, width=170, group="Health"),
        _c("classified_at", "Classified At", DATETIME, width=170, group="Health"),
        *PROVENANCE_COLUMNS,
    ),
)

RIE_COMPANY_DOSSIER = Tab(
    id="rie_company_dossier",
    label="RIE Company Dossier",
    description="Research Intelligence Engine dossier summaries (Phase 8.4) — no recommendations.",
    mode="master",
    key=("symbol",),
    order_by=("as_of DESC", "symbol"),
    search_columns=("symbol", "research_confidence", "status"),
    icon="research",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=120, group="Key"),
        _c("as_of", "As Of", DATE, width=120, group="Key"),
        _c("research_confidence", "Research Confidence", TEXT, width=160, group="Quality",
           options=("High", "Medium", "Low")),
        _c("score", "Score", NUMBER, width=100, group="Quality"),
        _c("coverage_pct", "Coverage %", NUMBER, width=120, group="Quality"),
        _c("status", "Status", TEXT, width=100, group="Quality"),
        _c("dqiv", "DQIV", TEXT, width=100, group="Quality"),
        _c("sections_ok", "Sections OK", INTEGER, width=120, group="Coverage"),
        _c("executive_summary", "Executive Summary", TEXT, width=360, group="Narrative"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Phase 8.5 — Forecast Intelligence Engine warehouse tabs
# --------------------------------------------------------------------------

FORECAST_COMPANY = Tab(
    id="forecast_company",
    label="Forecast Company",
    description="FIE company forecast summary (Phase 8.5). No target prices. No recommendations.",
    mode="master",
    key=("symbol",),
    order_by=("as_of DESC", "symbol"),
    search_columns=("symbol", "forecast_confidence", "status"),
    icon="forecast",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=120, group="Key"),
        _c("as_of", "As Of", DATE, width=120, group="Key"),
        _c("forecast_confidence", "Forecast Confidence", TEXT, width=160, group="Quality",
           options=("High", "Medium", "Low")),
        _c("score", "Score", NUMBER, width=100, group="Quality"),
        _c("coverage_pct", "Coverage %", NUMBER, width=120, group="Quality"),
        _c("status", "Status", TEXT, width=100, group="Quality"),
        _c("dqiv", "DQIV", TEXT, width=100, group="Quality"),
        _c("bull_pct", "Bull %", NUMBER, width=100, group="Scenarios"),
        _c("base_pct", "Base %", NUMBER, width=100, group="Scenarios"),
        _c("bear_pct", "Bear %", NUMBER, width=100, group="Scenarios"),
        _c("modules_ok", "Modules OK", INTEGER, width=120, group="Coverage"),
        _c("version", "Version", TEXT, width=100, group="Provenance"),
        _c("executive_summary", "Executive Summary", TEXT, width=360, group="Narrative"),
        *PROVENANCE_COLUMNS,
    ),
)

FORECAST_HISTORY = Tab(
    id="forecast_history",
    label="Forecast History",
    description="Append-only FIE forecast vintages. Never overwrite prior versions.",
    mode="append",
    key=("symbol", "as_of", "generated_at", "event"),
    order_by=("as_of DESC", "symbol"),
    search_columns=("symbol", "event", "status"),
    icon="forecast",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=120, group="Key"),
        _c("as_of", "As Of", DATE, width=120, group="Key"),
        _c("generated_at", "Generated At", DATETIME, width=170, group="Key"),
        _c("event", "Event", TEXT, width=120, group="Key",
           options=("generated", "updated", "superseded", "confirmed", "missed")),
        _c("forecast_confidence", "Forecast Confidence", TEXT, width=160, group="Quality"),
        _c("score", "Score", NUMBER, width=100, group="Quality"),
        _c("coverage_pct", "Coverage %", NUMBER, width=120, group="Quality"),
        _c("status", "Status", TEXT, width=100, group="Quality"),
        _c("dqiv", "DQIV", TEXT, width=100, group="Quality"),
        _c("bull_pct", "Bull %", NUMBER, width=100, group="Scenarios"),
        _c("base_pct", "Base %", NUMBER, width=100, group="Scenarios"),
        _c("bear_pct", "Bear %", NUMBER, width=100, group="Scenarios"),
        _c("modules_ok", "Modules OK", INTEGER, width=120, group="Coverage"),
        _c("version", "Version", TEXT, width=100, group="Provenance"),
        _c("executive_summary", "Executive Summary", TEXT, width=360, group="Narrative"),
        *PROVENANCE_COLUMNS,
    ),
)

FORECAST_SCENARIOS = Tab(
    id="forecast_scenarios",
    label="Forecast Scenarios",
    description="Append-only bull/base/bear scenario snapshots from FIE.",
    mode="append",
    key=("symbol", "as_of", "scenario"),
    order_by=("as_of DESC", "symbol"),
    search_columns=("symbol", "scenario"),
    icon="forecast",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=120, group="Key"),
        _c("as_of", "As Of", DATE, width=120, group="Key"),
        _c("scenario", "Scenario", TEXT, required=True, width=100, group="Key",
           options=("bull", "base", "bear")),
        _c("probability_pct", "Probability %", NUMBER, width=130, group="Scenarios"),
        _c("payload_summary", "Payload Summary", TEXT, width=280, group="Narrative"),
        _c("status", "Status", TEXT, width=100, group="Quality"),
        *PROVENANCE_COLUMNS,
    ),
)

FORECAST_ASSUMPTIONS = Tab(
    id="forecast_assumptions",
    label="Forecast Assumptions",
    description="Append-only disclosed assumptions for each FIE vintage.",
    mode="append",
    key=("symbol", "generated_at", "horizon", "scenario", "name"),
    order_by=("as_of DESC", "symbol"),
    search_columns=("symbol", "name"),
    icon="forecast",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=120, group="Key"),
        _c("as_of", "As Of", DATE, width=120, group="Key"),
        _c("generated_at", "Generated At", DATETIME, required=True, width=170, group="Key"),
        _c("name", "Name", TEXT, required=True, width=160, group="Key"),
        _c("metric", "Metric", TEXT, width=140, group="Key"),
        _c("horizon", "Horizon", TEXT, required=True, width=100, group="Key"),
        _c("scenario", "Scenario", TEXT, required=True, width=100, group="Key"),
        _c("value", "Value", TEXT, width=160, group="Assumption"),
        _c("basis", "Basis", TEXT, width=160, group="Assumption"),
        _c("assumption_type", "Type", TEXT, width=110, group="Assumption"),
        _c("expected_consequence", "Expected Consequence", NUMBER, width=170, group="Assumption"),
        _c("confidence", "Confidence", TEXT, width=120, group="Quality"),
        _c("status", "Status", TEXT, width=100, group="Quality"),
        *PROVENANCE_COLUMNS,
    ),
)

FORECAST_CONFIDENCE = Tab(
    id="forecast_confidence",
    label="Forecast Confidence",
    description="Append-only FIE confidence snapshots.",
    mode="append",
    key=("symbol", "as_of"),
    order_by=("as_of DESC", "symbol"),
    search_columns=("symbol", "forecast_confidence"),
    icon="forecast",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=120, group="Key"),
        _c("as_of", "As Of", DATE, width=120, group="Key"),
        _c("forecast_confidence", "Forecast Confidence", TEXT, width=160, group="Quality"),
        _c("score", "Score", NUMBER, width=100, group="Quality"),
        _c("coverage_pct", "Coverage %", NUMBER, width=120, group="Quality"),
        _c("high_n", "High N", INTEGER, width=100, group="Distribution"),
        _c("medium_n", "Medium N", INTEGER, width=100, group="Distribution"),
        _c("low_n", "Low N", INTEGER, width=100, group="Distribution"),
        *PROVENANCE_COLUMNS,
    ),
)

FORECAST_METRIC_PREDICTIONS = Tab(
    id="forecast_metric_predictions",
    label="Forecast Metric Predictions",
    description="Immutable line-item forecast vintages used for later outcome measurement.",
    mode="append",
    key=("symbol", "generated_at", "horizon", "scenario", "metric"),
    entity_column="symbol",
    order_by=("generated_at DESC", "symbol"),
    search_columns=("symbol", "metric", "scenario"),
    icon="forecast",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=120, group="Key"),
        _c("forecast_as_of", "Forecast As Of", DATE, width=140, group="Key"),
        _c("generated_at", "Generated At", DATETIME, required=True, width=170, group="Key"),
        _c("base_period", "Base Period", TEXT, width=120, group="Period"),
        _c("target_period", "Target Period", TEXT, width=120, group="Period"),
        _c("horizon", "Horizon", TEXT, required=True, width=100, group="Period"),
        _c("scenario", "Scenario", TEXT, required=True, width=100, group="Forecast"),
        _c("metric", "Metric", TEXT, required=True, width=140, group="Forecast"),
        _c("base_value", "Base Value", NUMBER, width=130, group="Forecast"),
        _c("forecast_value", "Forecast Value", NUMBER, width=140, group="Forecast"),
        _c("historical_cagr_pct", "Historical CAGR %", NUMBER, width=150, group="Assumptions"),
        _c("scenario_multiplier", "Scenario Multiplier", NUMBER, width=150, group="Assumptions"),
        _c("margin_assumption_pp", "Margin Assumption pp", NUMBER, width=160, group="Assumptions"),
        _c("probability_pct", "Probability %", NUMBER, width=130, group="Forecast"),
        _c("forecast_confidence", "Confidence", TEXT, width=120, group="Quality"),
        _c("confidence_score", "Confidence Score", NUMBER, width=130, group="Quality"),
        _c("model_version", "Model Version", TEXT, width=120, group="Lineage"),
        _c("status", "Status", TEXT, width=100, group="Quality"),
        *PROVENANCE_COLUMNS,
    ),
)

FORECAST_SNAPSHOTS = Tab(
    id="forecast_snapshots",
    label="Forecast Snapshots",
    description="Point-in-time registry of the evidence versions available to each forecast vintage.",
    mode="append",
    key=("snapshot_id",),
    entity_column="symbol",
    order_by=("forecast_timestamp DESC", "symbol"),
    search_columns=("symbol", "snapshot_id", "engine_version"),
    icon="forecast",
    columns=(
        _c("snapshot_id", "Snapshot ID", TEXT, required=True, width=220, group="Key"),
        _c("symbol", "Symbol", TEXT, required=True, width=120, group="Key"),
        _c("forecast_timestamp", "Forecast Timestamp", DATETIME, required=True, width=180, group="Time"),
        _c("data_cutoff_timestamp", "Data Cutoff", DATETIME, width=180, group="Time"),
        _c("financial_data_version", "Financial Version", TEXT, width=220, group="Versions"),
        _c("valuation_data_version", "Valuation Version", TEXT, width=220, group="Versions"),
        _c("consensus_version", "Consensus Version", TEXT, width=220, group="Versions"),
        _c("research_version", "Research Version", TEXT, width=220, group="Versions"),
        _c("macro_version", "Macro Version", TEXT, width=220, group="Versions"),
        _c("forecast_version", "Forecast Version", TEXT, width=140, group="Engine"),
        _c("engine_version", "Engine Version", TEXT, width=140, group="Engine"),
        _c("input_manifest", "Input Manifest", JSON, width=260, group="Lineage"),
        *PROVENANCE_COLUMNS,
    ),
)

FORECAST_EVALUATIONS = Tab(
    id="forecast_evaluations",
    label="Forecast Evaluations",
    description="Governed outcome registry. Only VALID evaluations may feed accuracy and learning.",
    mode="append",
    key=("symbol", "generated_at", "target_period", "horizon", "scenario", "metric", "outcome_status"),
    entity_column="symbol",
    order_by=("evaluated_at DESC", "symbol"),
    search_columns=("symbol", "metric", "outcome_status", "sector"),
    icon="forecast",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=120, group="Key"),
        _c("generated_at", "Forecast Generated At", DATETIME, required=True, width=170, group="Key"),
        _c("forecast_as_of", "Forecast As Of", DATE, width=130, group="Key"),
        _c("target_period", "Target Period", TEXT, required=True, width=120, group="Key"),
        _c("actual_period", "Actual Period", TEXT, width=120, group="Outcome"),
        _c("horizon", "Horizon", TEXT, required=True, width=100, group="Key"),
        _c("scenario", "Scenario", TEXT, required=True, width=100, group="Key"),
        _c("metric", "Metric", TEXT, required=True, width=140, group="Key"),
        _c("forecast_value", "Forecast Value", NUMBER, width=140, group="Outcome"),
        _c("actual_value", "Actual Value", NUMBER, width=140, group="Outcome"),
        _c("outcome_status", "Outcome Status", TEXT, required=True, width=150, group="Governance"),
        _c("validation_reason", "Validation Reason", TEXT, width=260, group="Governance"),
        _c("requires_review", "Requires Review", BOOL, width=140, group="Governance"),
        _c("sector", "Sector", TEXT, width=140, group="Dimensions"),
        _c("regime", "Regime", TEXT, width=120, group="Dimensions"),
        _c("forecast_confidence", "Confidence", TEXT, width=120, group="Dimensions"),
        _c("model_version", "Model Version", TEXT, width=120, group="Dimensions"),
        _c("actual_source", "Actual Source", TEXT, width=180, group="Lineage"),
        _c("evaluated_at", "Evaluated At", DATETIME, width=170, group="Lineage"),
        *PROVENANCE_COLUMNS,
    ),
)

FORECAST_LEARNINGS = Tab(
    id="forecast_learnings",
    label="Forecast Learnings",
    description="Governed, evidence-backed proposed learnings. No automatic FIE parameter changes.",
    mode="append",
    key=("learning_id",),
    entity_column=None,
    order_by=("last_observed DESC", "learning_id"),
    search_columns=("learning_id", "applicable_sector", "status"),
    icon="forecast",
    columns=(
        _c("learning_id", "Learning ID", TEXT, required=True, width=220, group="Key"),
        _c("observation", "Observation", TEXT, required=True, width=320, group="Learning"),
        _c("observation_count", "Observations", INTEGER, width=120, group="Evidence"),
        _c("supporting_forecasts", "Supporting Forecasts", JSON, width=240, group="Evidence"),
        _c("supporting_outcomes", "Supporting Outcomes", JSON, width=240, group="Evidence"),
        _c("statistical_strength", "Statistical Strength", NUMBER, width=150, group="Evidence"),
        _c("applicable_sector", "Applicable Sector", TEXT, width=150, group="Scope"),
        _c("applicable_condition", "Applicable Condition", TEXT, width=220, group="Scope"),
        _c("first_observed", "First Observed", DATETIME, width=170, group="Time"),
        _c("last_observed", "Last Observed", DATETIME, width=170, group="Time"),
        _c("confidence", "Confidence", TEXT, width=120, group="Governance"),
        _c("status", "Status", TEXT, required=True, width=110, group="Governance",
           options=("PROPOSED", "VALIDATED", "ACTIVE", "RETIRED")),
        *PROVENANCE_COLUMNS,
    ),
)

FORECAST_ACCURACY = Tab(
    id="forecast_accuracy",
    label="Forecast Accuracy",
    description="Append-only forecast vs actual error tracking. Never rewrites history.",
    mode="append",
    key=("symbol", "generated_at", "actual_period", "horizon", "scenario", "metric"),
    entity_column="symbol",
    order_by=("forecast_as_of DESC", "symbol"),
    search_columns=("symbol", "metric"),
    icon="forecast",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=120, group="Key"),
        _c("forecast_as_of", "Forecast As Of", DATE, width=140, group="Key"),
        _c("generated_at", "Forecast Generated At", DATETIME, required=True, width=170, group="Key"),
        _c("actual_period", "Actual Period", TEXT, width=130, group="Key"),
        _c("horizon", "Horizon", TEXT, required=True, width=100, group="Key"),
        _c("scenario", "Scenario", TEXT, required=True, width=100, group="Key"),
        _c("metric", "Metric", TEXT, required=True, width=120, group="Key"),
        _c("base_value", "Base Value", NUMBER, width=130, group="Error"),
        _c("forecast_value", "Forecast Value", NUMBER, width=140, group="Error"),
        _c("actual_value", "Actual Value", NUMBER, width=140, group="Error"),
        _c("absolute_error", "Absolute Error", NUMBER, width=130, group="Error"),
        _c("error_pct", "Error %", NUMBER, width=120, group="Error"),
        _c("ape_pct", "Absolute % Error", NUMBER, width=140, group="Error"),
        _c("direction_correct", "Direction Correct", BOOL, width=140, group="Quality"),
        _c("accuracy_band", "Accuracy Band", TEXT, width=120, group="Quality"),
        _c("forecast_confidence", "Confidence", TEXT, width=120, group="Calibration"),
        _c("confidence_score", "Confidence Score", NUMBER, width=130, group="Calibration"),
        _c("calibration_status", "Calibration", TEXT, width=140, group="Calibration"),
        _c("model_version", "Model Version", TEXT, width=120, group="Lineage"),
        _c("actual_source", "Actual Source", TEXT, width=180, group="Lineage"),
        _c("evaluated_at", "Evaluated At", DATETIME, width=170, group="Lineage"),
        _c("attribution", "Attribution", JSON, width=240, group="Learning"),
        _c("status", "Status", TEXT, width=100, group="Quality"),
        *PROVENANCE_COLUMNS,
    ),
)

FORECAST_RUNTIME = Tab(
    id="forecast_runtime",
    label="Forecast Runtime",
    description="FIE universe bootstrap queue — waiting HVIE / RIE / statements.",
    mode="master",
    key=("symbol",),
    order_by=("updated_at DESC", "symbol"),
    search_columns=("symbol", "queue_status", "lifecycle"),
    icon="forecast",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=120, group="Key"),
        _c("queue_status", "Queue Status", TEXT, width=130, group="Queue"),
        _c("lifecycle", "Lifecycle", TEXT, width=160, group="Queue"),
        _c("sector", "Sector", TEXT, width=140, group="Identity"),
        _c("industry", "Industry", TEXT, width=160, group="Identity"),
        _c("last_error", "Last Error", TEXT, width=280, group="Health"),
        _c("last_run_at", "Last Run", DATETIME, width=170, group="Health"),
        _c("completed_at", "Completed At", DATETIME, width=170, group="Health"),
        _c("updated_at", "Updated At", DATETIME, width=170, group="Health"),
        *PROVENANCE_COLUMNS,
    ),
)

STRATEGY_PAPER_SNAPSHOTS = Tab(
    id="strategy_paper_snapshots",
    label="Strategy Paper Snapshots",
    description="Immutable forward-only research signals captured before outcomes are known.",
    mode="append",
    key=("strategy_id", "signal_as_of", "ticker"),
    entity_column="ticker",
    order_by=("signal_as_of DESC", "strategy_id", "ticker"),
    search_columns=("strategy_id", "ticker", "research_direction"),
    icon="strategy",
    columns=(
        _c("strategy_id", "Strategy", TEXT, required=True, width=180, group="Key"),
        _c("strategy_version", "Strategy Version", TEXT, width=180, group="Key"),
        _c("signal_as_of", "Signal As Of", DATE, required=True, width=130, group="Key"),
        _c("ticker", "Ticker", TEXT, required=True, width=120, group="Key"),
        _c("research_direction", "Direction", TEXT, required=True, width=130, group="Signal"),
        _c("signal", "Signal", TEXT, width=100, group="Signal"),
        _c("score", "Score", NUMBER, width=110, group="Signal"),
        _c("signal_price", "Signal Price", NUMBER, required=True, width=130, group="Signal"),
        _c("horizon_sessions", "Horizon Sessions", INTEGER, width=140, group="Evaluation"),
        _c("captured_at", "Captured At", DATETIME, width=170, group="Lineage"),
        *PROVENANCE_COLUMNS,
    ),
)

STRATEGY_PAPER_OUTCOMES = Tab(
    id="strategy_paper_outcomes",
    label="Strategy Paper Outcomes",
    description="Costed future outcomes for immutable paper signals; never backfilled before capture.",
    mode="append",
    key=("strategy_id", "signal_as_of", "ticker", "horizon_sessions"),
    entity_column="ticker",
    order_by=("evaluated_as_of DESC", "strategy_id", "ticker"),
    search_columns=("strategy_id", "ticker", "research_direction"),
    icon="strategy",
    columns=(
        _c("strategy_id", "Strategy", TEXT, required=True, width=180, group="Key"),
        _c("strategy_version", "Strategy Version", TEXT, width=180, group="Key"),
        _c("signal_as_of", "Signal As Of", DATE, required=True, width=130, group="Key"),
        _c("evaluated_as_of", "Evaluated As Of", DATE, required=True, width=140, group="Outcome"),
        _c("ticker", "Ticker", TEXT, required=True, width=120, group="Key"),
        _c("research_direction", "Direction", TEXT, width=130, group="Signal"),
        _c("signal_price", "Signal Price", NUMBER, width=130, group="Outcome"),
        _c("outcome_price", "Outcome Price", NUMBER, width=130, group="Outcome"),
        _c("horizon_sessions", "Horizon Sessions", INTEGER, required=True, width=140, group="Outcome"),
        _c("gross_return_pct", "Gross Return %", NUMBER, width=140, group="Outcome"),
        _c("round_trip_cost_bps", "Round Trip Cost bps", NUMBER, width=170, group="Costs"),
        _c("net_return_pct", "Net Return %", NUMBER, width=130, group="Outcome"),
        _c("profitable", "Profitable", BOOL, width=110, group="Outcome"),
        _c("evaluated_at", "Evaluated At", DATETIME, width=170, group="Lineage"),
        *PROVENANCE_COLUMNS,
    ),
)

PORTFOLIO_SNAPSHOTS = Tab(
    id="portfolio_snapshots",
    label="Portfolio Snapshots",
    description="Immutable point-in-time portfolio mandates and aggregate state.",
    mode="append",
    key=("portfolio_id", "as_of"),
    entity_column="portfolio_id",
    order_by=("as_of DESC", "portfolio_id"),
    search_columns=("portfolio_id", "name", "benchmark"),
    icon="portfolio",
    columns=(
        _c("portfolio_id", "Portfolio ID", TEXT, required=True, width=180, group="Key"),
        _c("as_of", "As Of", DATE, required=True, width=130, group="Key"),
        _c("name", "Name", TEXT, width=220, group="Mandate"),
        _c("objective", "Objective", TEXT, width=280, group="Mandate"),
        _c("benchmark", "Benchmark", TEXT, width=160, group="Mandate"),
        _c("base_currency", "Base Currency", TEXT, width=120, group="Mandate"),
        _c("risk_tolerance", "Risk Tolerance", TEXT, width=140, group="Limits"),
        _c("max_drawdown", "Max Drawdown", NUMBER, width=130, group="Limits"),
        _c("single_name_limit", "Single Name Limit", NUMBER, width=150, group="Limits"),
        _c("sector_limits", "Sector Limits", JSON, width=220, group="Limits"),
        _c("benchmark_sector_weights", "Benchmark Sector Weights", JSON, width=240, group="Benchmark"),
        _c("cash_weight", "Cash Weight", NUMBER, width=120, group="State"),
        _c("status", "Status", TEXT, width=110, group="State"),
        *PROVENANCE_COLUMNS,
    ),
)

PORTFOLIO_HOLDINGS = Tab(
    id="portfolio_holdings",
    label="Portfolio Holdings",
    description="Immutable holdings belonging to a dated portfolio snapshot.",
    mode="append",
    key=("portfolio_id", "as_of", "ticker"),
    entity_column="portfolio_id",
    order_by=("as_of DESC", "portfolio_id", "ticker"),
    search_columns=("portfolio_id", "ticker", "sector"),
    icon="portfolio",
    columns=(
        _c("portfolio_id", "Portfolio ID", TEXT, required=True, width=180, group="Key"),
        _c("as_of", "As Of", DATE, required=True, width=130, group="Key"),
        _c("ticker", "Ticker", TEXT, required=True, width=120, group="Key"),
        _c("weight", "Weight", NUMBER, required=True, width=110, group="Position"),
        _c("shares", "Shares", NUMBER, width=120, group="Position"),
        _c("market_value", "Market Value", NUMBER, width=140, group="Position"),
        _c("sector", "Sector", TEXT, width=150, group="Exposure"),
        _c("industry", "Industry", TEXT, width=170, group="Exposure"),
        _c("country", "Country", TEXT, width=100, group="Exposure"),
        _c("beta", "Beta", NUMBER, width=100, group="Risk"),
        _c("factors", "Factor Exposures", JSON, width=220, group="Risk"),
        _c("conviction", "Conviction", TEXT, width=120, group="Research"),
        *PROVENANCE_COLUMNS,
    ),
)

PORTFOLIO_DAILY_RETURNS = Tab(
    id="portfolio_daily_returns",
    label="Portfolio Daily Returns",
    description="Dated portfolio and benchmark returns used for empirical risk and attribution.",
    mode="append",
    key=("portfolio_id", "date"),
    entity_column="portfolio_id",
    order_by=("date DESC", "portfolio_id"),
    search_columns=("portfolio_id",),
    icon="portfolio",
    columns=(
        _c("portfolio_id", "Portfolio ID", TEXT, required=True, width=180, group="Key"),
        _c("date", "Date", DATE, required=True, width=130, group="Key"),
        _c("return_pct", "Return %", NUMBER, required=True, width=120, group="Performance"),
        _c("benchmark_return_pct", "Benchmark Return %", NUMBER, width=170, group="Performance"),
        _c("nav", "NAV", NUMBER, width=120, group="Performance"),
        _c("gross_exposure", "Gross Exposure", NUMBER, width=140, group="Exposure"),
        _c("net_exposure", "Net Exposure", NUMBER, width=130, group="Exposure"),
        *PROVENANCE_COLUMNS,
    ),
)

PORTFOLIO_ATTRIBUTION = Tab(
    id="portfolio_attribution",
    label="Portfolio Attribution",
    description="Dated holding-level performance attribution with explicit residual.",
    mode="append",
    key=("portfolio_id", "date", "ticker"),
    entity_column="portfolio_id",
    order_by=("date DESC", "portfolio_id", "ticker"),
    search_columns=("portfolio_id", "ticker", "sector"),
    icon="portfolio",
    columns=(
        _c("portfolio_id", "Portfolio ID", TEXT, required=True, width=180, group="Key"),
        _c("date", "Date", DATE, required=True, width=130, group="Key"),
        _c("ticker", "Ticker", TEXT, required=True, width=120, group="Key"),
        _c("sector", "Sector", TEXT, width=150, group="Exposure"),
        _c("starting_weight", "Starting Weight", NUMBER, width=150, group="Attribution"),
        _c("security_return_pct", "Security Return %", NUMBER, width=160, group="Attribution"),
        _c("contribution_pct", "Contribution %", NUMBER, width=150, group="Attribution"),
        _c("benchmark_contribution_pct", "Benchmark Contribution %", NUMBER, width=210, group="Attribution"),
        _c("active_contribution_pct", "Active Contribution %", NUMBER, width=190, group="Attribution"),
        *PROVENANCE_COLUMNS,
    ),
)

# --------------------------------------------------------------------------
# Phase 9.0 — Macro Intelligence Engine warehouse tabs
# --------------------------------------------------------------------------

MACRO_SERIES = Tab(
    id="macro_series",
    label="Macro Series",
    description="Canonical macro series catalogue / observations for MIE (Phase 9.0).",
    mode="append",
    key=("series_id", "as_of", "country"),
    order_by=("as_of DESC", "series_id"),
    search_columns=("series_id", "domain", "country"),
    icon="macro",
    columns=(
        _c("series_id", "Series ID", TEXT, required=True, width=140, group="Key"),
        _c("country", "Country", TEXT, width=120, group="Key"),
        _c("domain", "Domain", TEXT, width=120, group="Key"),
        _c("as_of", "As Of", DATE, width=120, group="Key"),
        _c("value", "Value", NUMBER, width=120, group="Observation"),
        _c("unit", "Unit", TEXT, width=100, group="Observation"),
        _c("direction", "Direction", TEXT, width=100, group="Observation",
           options=("up", "down", "flat")),
        # Do not add a custom "source" column — reserved by PROVENANCE_COLUMNS.
        *PROVENANCE_COLUMNS,
    ),
)

MACRO_LATEST = Tab(
    id="macro_latest",
    label="Macro Latest",
    description="Latest value per macro series (MIE Phase 9.0).",
    mode="master",
    key=("series_id", "country"),
    order_by=("domain", "series_id"),
    search_columns=("series_id", "domain", "country"),
    icon="macro",
    columns=(
        _c("series_id", "Series ID", TEXT, required=True, width=140, group="Key"),
        _c("country", "Country", TEXT, width=120, group="Key"),
        _c("domain", "Domain", TEXT, width=120, group="Key"),
        _c("as_of", "As Of", DATE, width=120, group="Key"),
        _c("value", "Value", NUMBER, width=120, group="Observation"),
        _c("unit", "Unit", TEXT, width=100, group="Observation"),
        _c("direction", "Direction", TEXT, width=100, group="Observation"),
        # Do not add a custom "source" column — reserved by PROVENANCE_COLUMNS.
        *PROVENANCE_COLUMNS,
    ),
)

MACRO_EVENTS = Tab(
    id="macro_events",
    label="Macro Events",
    description="Append-only macro policy / release events for MIE attribution.",
    mode="append",
    key=("country", "as_of", "event"),
    order_by=("as_of DESC", "country"),
    search_columns=("country", "event", "title"),
    icon="macro",
    columns=(
        _c("country", "Country", TEXT, required=True, width=120, group="Key"),
        _c("as_of", "As Of", DATE, width=120, group="Key"),
        _c("event", "Event", TEXT, required=True, width=160, group="Key"),
        _c("title", "Title", TEXT, width=240, group="Narrative"),
        _c("severity", "Severity", TEXT, width=100, group="Quality"),
        *PROVENANCE_COLUMNS,
    ),
)

MACRO_REGIMES = Tab(
    id="macro_regimes",
    label="Macro Regimes",
    description="MIE regime / cycle snapshots (append-oriented).",
    mode="append",
    key=("country", "as_of", "regime"),
    order_by=("as_of DESC", "country"),
    search_columns=("country", "regime", "cycle"),
    icon="macro",
    columns=(
        _c("country", "Country", TEXT, required=True, width=120, group="Key"),
        _c("as_of", "As Of", DATE, width=120, group="Key"),
        _c("regime", "Regime", TEXT, width=140, group="Regime"),
        _c("cycle", "Cycle", TEXT, width=140, group="Regime"),
        _c("macro_confidence", "Macro Confidence", TEXT, width=160, group="Quality"),
        _c("score", "Score", NUMBER, width=100, group="Quality"),
        _c("bull_pct", "Bull %", NUMBER, width=100, group="Scenarios"),
        _c("base_pct", "Base %", NUMBER, width=100, group="Scenarios"),
        _c("bear_pct", "Bear %", NUMBER, width=100, group="Scenarios"),
        _c("status", "Status", TEXT, width=100, group="Quality"),
        _c("dqiv", "DQIV", TEXT, width=100, group="Quality"),
        _c("version", "Version", TEXT, width=100, group="Provenance"),
        _c("executive_summary", "Executive Summary", TEXT, width=360, group="Narrative"),
        *PROVENANCE_COLUMNS,
    ),
)

MACRO_HISTORY = Tab(
    id="macro_history",
    label="Macro History",
    description="Append-only MIE vintage history. Never overwrite prior versions.",
    mode="append",
    key=("country", "as_of", "generated_at", "event"),
    order_by=("as_of DESC", "country"),
    search_columns=("country", "event", "regime"),
    icon="macro",
    columns=(
        _c("country", "Country", TEXT, required=True, width=120, group="Key"),
        _c("as_of", "As Of", DATE, width=120, group="Key"),
        _c("generated_at", "Generated At", DATETIME, width=170, group="Key"),
        _c("event", "Event", TEXT, width=120, group="Key"),
        _c("regime", "Regime", TEXT, width=140, group="Regime"),
        _c("cycle", "Cycle", TEXT, width=140, group="Regime"),
        _c("macro_confidence", "Macro Confidence", TEXT, width=160, group="Quality"),
        _c("score", "Score", NUMBER, width=100, group="Quality"),
        _c("bull_pct", "Bull %", NUMBER, width=100, group="Scenarios"),
        _c("base_pct", "Base %", NUMBER, width=100, group="Scenarios"),
        _c("bear_pct", "Bear %", NUMBER, width=100, group="Scenarios"),
        _c("status", "Status", TEXT, width=100, group="Quality"),
        _c("dqiv", "DQIV", TEXT, width=100, group="Quality"),
        _c("version", "Version", TEXT, width=100, group="Provenance"),
        _c("executive_summary", "Executive Summary", TEXT, width=360, group="Narrative"),
        *PROVENANCE_COLUMNS,
    ),
)

MACRO_FORECASTS = Tab(
    id="macro_forecasts",
    label="Macro Forecasts",
    description="Directional macro scenario forecasts from MIE (not point GDP predictions).",
    mode="append",
    key=("country", "as_of", "horizon"),
    order_by=("as_of DESC", "country"),
    search_columns=("country", "horizon", "status"),
    icon="macro",
    columns=(
        _c("country", "Country", TEXT, required=True, width=120, group="Key"),
        _c("as_of", "As Of", DATE, width=120, group="Key"),
        _c("horizon", "Horizon", TEXT, width=120, group="Key"),
        _c("gdp_direction", "GDP Direction", TEXT, width=160, group="Directions"),
        _c("inflation_direction", "Inflation Direction", TEXT, width=160, group="Directions"),
        _c("rates_direction", "Rates Direction", TEXT, width=160, group="Directions"),
        _c("liquidity_direction", "Liquidity Direction", TEXT, width=160, group="Directions"),
        _c("currency_direction", "Currency Direction", TEXT, width=160, group="Directions"),
        _c("commodity_direction", "Commodity Direction", TEXT, width=160, group="Directions"),
        _c("status", "Status", TEXT, width=100, group="Quality"),
        _c("version", "Version", TEXT, width=100, group="Provenance"),
        *PROVENANCE_COLUMNS,
    ),
)

MACRO_RELATIONSHIPS = Tab(
    id="macro_relationships",
    label="Macro Relationships",
    description="Persisted macro→market relationship strength / confidence.",
    mode="append",
    key=("country", "as_of", "pair"),
    order_by=("as_of DESC", "pair"),
    search_columns=("country", "pair", "strength"),
    icon="macro",
    columns=(
        _c("country", "Country", TEXT, required=True, width=120, group="Key"),
        _c("as_of", "As Of", DATE, width=120, group="Key"),
        _c("pair", "Pair", TEXT, required=True, width=200, group="Key"),
        _c("strength", "Strength", TEXT, width=120, group="Quality"),
        _c("confidence", "Confidence", TEXT, width=120, group="Quality"),
        _c("observation_count", "Observations", INTEGER, width=120, group="Quality"),
        *PROVENANCE_COLUMNS,
    ),
)

MACRO_ALERTS = Tab(
    id="macro_alerts",
    label="Macro Alerts",
    description="Open macro risk alerts from MIE risk engine.",
    mode="append",
    key=("country", "as_of", "alert"),
    order_by=("as_of DESC", "country"),
    search_columns=("country", "alert", "level"),
    icon="macro",
    columns=(
        _c("country", "Country", TEXT, required=True, width=120, group="Key"),
        _c("as_of", "As Of", DATE, width=120, group="Key"),
        _c("alert", "Alert", TEXT, required=True, width=200, group="Key"),
        _c("level", "Level", TEXT, width=100, group="Quality"),
        _c("status", "Status", TEXT, width=100, group="Quality"),
        *PROVENANCE_COLUMNS,
    ),
)

MACRO_CALENDAR = Tab(
    id="macro_calendar",
    label="Macro Calendar",
    description="Macro release calendar for freshness monitoring.",
    mode="append",
    key=("country", "release_date", "indicator"),
    order_by=("release_date DESC", "country"),
    search_columns=("country", "indicator", "status"),
    icon="macro",
    columns=(
        _c("country", "Country", TEXT, required=True, width=120, group="Key"),
        _c("release_date", "Release Date", DATE, width=130, group="Key"),
        _c("indicator", "Indicator", TEXT, required=True, width=160, group="Key"),
        _c("status", "Status", TEXT, width=100, group="Quality"),
        # Do not add a custom "source" column — reserved by PROVENANCE_COLUMNS.
        *PROVENANCE_COLUMNS,
    ),
)

MACRO_RUNTIME = Tab(
    id="macro_runtime",
    label="Macro Runtime",
    description="MIE runtime queue / country refresh state.",
    mode="master",
    key=("country",),
    order_by=("updated_at DESC", "country"),
    search_columns=("country", "queue_status", "lifecycle"),
    icon="macro",
    columns=(
        _c("country", "Country", TEXT, required=True, width=120, group="Key"),
        _c("queue_status", "Queue Status", TEXT, width=140, group="Runtime"),
        _c("lifecycle", "Lifecycle", TEXT, width=140, group="Runtime"),
        _c("macro_confidence", "Macro Confidence", TEXT, width=160, group="Quality"),
        _c("last_mode", "Last Mode", TEXT, width=120, group="Runtime"),
        _c("last_error", "Last Error", TEXT, width=280, group="Health"),
        _c("last_run_at", "Last Run", DATETIME, width=170, group="Health"),
        _c("completed_at", "Completed At", DATETIME, width=170, group="Health"),
        _c("updated_at", "Updated At", DATETIME, width=170, group="Health"),
        *PROVENANCE_COLUMNS,
    ),
)

# Manual evidence workbook for the completed sector-valuation curricula.  This
# is deliberately separate from certification: a filled cell is evidence, not
# permission to promote an investment model.
SECTOR_EVIDENCE_MATRIX = Tab(
    id="sector_evidence_matrix",
    label="Sector Missing Data",
    description="Company x KPI evidence gaps for completed valuation phases. Fill manually or import CSV.",
    mode="master",
    key=("phase", "symbol", "subsector", "metric"),
    order_by=("phase", "subsector", "symbol", "metric"),
    entity_column="symbol",
    search_columns=("phase", "symbol", "subsector", "metric", "source", "status"),
    icon="spreadsheet",
    notes=(
        "Manual evidence does not certify a company or strategy.",
        "Use decimal units for ratios unless the source explicitly reports percentages.",
        "Every supported value requires period, PIT date and source.",
    ),
    columns=(
        _c("company_name", "Company Name", TEXT, editable=False, width=240, group="Company"),
        _c("symbol", "NSE Symbol", TEXT, editable=False, required=True, width=130, group="Company"),
        _c("phase", "Phase", TEXT, editable=False, required=True, width=150, group="Curriculum"),
        _c("subsector", "Subsector", TEXT, editable=False, required=True, width=210, group="Curriculum"),
        _c("metric", "Required KPI", TEXT, editable=False, required=True, width=220, group="Evidence"),
        _c("metric_label", "What To Fill", TEXT, editable=False, width=230, group="Evidence"),
        _c("definition", "Meaning / Definition", TEXT, editable=False, width=360, group="Evidence"),
        _c("input_type", "Input Type", TEXT, editable=False, width=120, group="Evidence",
           options=("REPORTED", "CALCULATED", "MARKET", "ASSUMPTION")),
        _c("expected_unit", "Expected Unit", TEXT, editable=False, width=140, group="Instructions"),
        _c("expected_period", "Expected Period", TEXT, editable=False, width=150, group="Instructions"),
        _c("source_guidance", "Where To Find It", TEXT, editable=False, width=320, group="Instructions"),
        _c("required", "Required", BOOL, editable=False, width=90, group="Evidence"),
        _c("available", "Available", BOOL, width=100, group="Evidence"),
        _c("value", "Value", NUMBER, width=130, group="Manual Entry"),
        _c("unit", "Unit", TEXT, width=120, group="Manual Entry"),
        _c("period", "Period", TEXT, width=130, group="Manual Entry"),
        _c("publication_date", "Publication Date", DATE, width=150, group="Point in Time"),
        _c("as_of_date", "As Of Date", DATE, width=130, group="Point in Time"),
        _c("pit_valid", "PIT Valid", BOOL, width=100, group="Point in Time"),
        _c("source", "Source / URL", TEXT, width=260, group="Provenance"),
        _c("evidence", "Evidence Note", TEXT, width=320, group="Provenance"),
        _c("quality", "Quality", TEXT, width=120, group="Validation",
           options=("HIGH", "MEDIUM", "LOW", "UNREVIEWED")),
        _c("status", "Status", TEXT, required=True, width=140, group="Validation",
           options=("SUPPORTED", "PARTIAL", "DATA_REQUIRED", "CONFLICT", "STALE", "PIT_INVALID")),
        _c("review_notes", "Review Notes", TEXT, width=280, group="Validation"),
        _c("last_updated", "Last Updated", DATETIME, editable=False, width=170, group="Provenance"),
    ),
)

VENDOR_RISK_METRICS = Tab(
    id="vendor_risk_metrics",
    label="Vendor Risk Metrics",
    description="Per-name beta and technical state from vendor exports. Beta is the "
                "input that makes portfolio-beta neutralisation expressible.",
    mode="append",
    key=("symbol", "as_of"),
    order_by=("as_of DESC", "symbol"),
    search_columns=("symbol",),
    icon="valuation",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=130, group="Key"),
        _c("as_of", "As Of", DATE, required=True, width=120, group="Key"),
        _c("isin", "ISIN", TEXT, width=140, group="Key"),
        _c("beta_1m", "Beta 1M", NUMBER, width=100, group="Risk"),
        _c("beta_3m", "Beta 3M", NUMBER, width=100, group="Risk"),
        _c("beta_1y", "Beta 1Y", NUMBER, width=100, group="Risk"),
        _c("beta_3y", "Beta 3Y", NUMBER, width=100, group="Risk"),
        _c("atr", "ATR", NUMBER, width=100, group="Risk"),
        _c("adx", "ADX", NUMBER, width=100, group="Trend"),
        _c("rsi", "RSI", NUMBER, width=100, group="Trend"),
        _c("mfi", "MFI", NUMBER, width=100, group="Trend"),
        _c("macd", "MACD", NUMBER, width=110, group="Trend"),
        _c("macd_signal", "MACD Signal", NUMBER, width=120, group="Trend"),
        _c("sma50", "SMA50", NUMBER, width=110, group="Levels"),
        _c("sma200", "SMA200", NUMBER, width=110, group="Levels"),
        _c("ema20", "EMA20", NUMBER, width=110, group="Levels"),
        _c("ema50", "EMA50", NUMBER, width=110, group="Levels"),
        _c("pivot", "Pivot", NUMBER, width=110, group="Levels"),
        _c("roc21", "ROC 21", NUMBER, width=100, group="Momentum"),
        _c("roc125", "ROC 125", NUMBER, width=110, group="Momentum"),
        _c("momentum_score", "Momentum Score", NUMBER, width=140, group="Momentum"),
        _c("momentum_score_norm", "Momentum (Norm)", NUMBER, width=150, group="Momentum"),
        _c("momentum_score_prev_month", "Momentum (Prev M)", NUMBER, width=160, group="Momentum"),
        *PROVENANCE_COLUMNS,
    ),
)

VENDOR_LIQUIDITY = Tab(
    id="vendor_liquidity",
    label="Vendor Liquidity",
    description="Average daily traded value. Required before any strategy can be "
                "sized against capacity or an ADV participation limit.",
    mode="append",
    key=("symbol", "as_of"),
    order_by=("as_of DESC", "symbol"),
    search_columns=("symbol",),
    icon="valuation",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=130, group="Key"),
        _c("as_of", "As Of", DATE, required=True, width=120, group="Key"),
        _c("adv_3m", "ADV 3M", NUMBER, width=140, group="Liquidity"),
        # Current membership only. Not point-in-time, so this cannot be used to
        # reconstruct a survivorship-free historical universe.
        _c("index_membership", "Index Membership", TEXT, width=280, group="Classification"),
        *PROVENANCE_COLUMNS,
    ),
)

VENDOR_PRICE_HISTORY = Tab(
    id="vendor_price_history",
    label="Vendor Price History",
    description="Multi-horizon returns, ranges and traded volume from vendor exports.",
    mode="append",
    key=("symbol", "as_of"),
    order_by=("as_of DESC", "symbol"),
    search_columns=("symbol",),
    icon="valuation",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=130, group="Key"),
        _c("as_of", "As Of", DATE, required=True, width=120, group="Key"),
        _c("isin", "ISIN", TEXT, width=140, group="Key"),
        _c("vwap_day", "VWAP", NUMBER, width=110, group="Price"),
        _c("market_cap", "Market Cap", NUMBER, width=140, group="Price"),
        _c("return_1d", "1D %", NUMBER, width=90, group="Returns"),
        _c("return_1m", "1M %", NUMBER, width=90, group="Returns"),
        _c("return_3m", "3M %", NUMBER, width=90, group="Returns"),
        _c("return_1y", "1Y %", NUMBER, width=90, group="Returns"),
        _c("return_2y", "2Y %", NUMBER, width=90, group="Returns"),
        _c("return_3y", "3Y %", NUMBER, width=90, group="Returns"),
        _c("return_5y", "5Y %", NUMBER, width=90, group="Returns"),
        _c("return_10y", "10Y %", NUMBER, width=95, group="Returns"),
        _c("high_1y", "1Y High", NUMBER, width=110, group="Range"),
        _c("low_1y", "1Y Low", NUMBER, width=110, group="Range"),
        _c("high_5y", "5Y High", NUMBER, width=110, group="Range"),
        _c("low_5y", "5Y Low", NUMBER, width=110, group="Range"),
        _c("high_10y", "10Y High", NUMBER, width=115, group="Range"),
        _c("low_10y", "10Y Low", NUMBER, width=115, group="Range"),
        _c("volume_day", "Volume", NUMBER, width=120, group="Volume"),
        _c("volume_week_avg", "Volume W Avg", NUMBER, width=130, group="Volume"),
        _c("volume_month_avg", "Volume M Avg", NUMBER, width=130, group="Volume"),
        *PROVENANCE_COLUMNS,
    ),
)

VENDOR_INDUSTRY_CONTEXT = Tab(
    id="vendor_industry_context",
    label="Vendor Industry Context",
    description="Each company's own vendor-published industry and sector aggregates, "
                "attached per symbol. The vendor taxonomy does not match the engine's "
                "GICS-style names, so consumers must join on symbol, never on industry.",
    mode="append",
    key=("symbol", "as_of"),
    order_by=("as_of DESC", "symbol"),
    search_columns=("symbol", "vendor_industry", "vendor_sector"),
    icon="valuation",
    columns=(
        _c("symbol", "Symbol", TEXT, required=True, width=130, group="Key"),
        _c("as_of", "As Of", DATE, required=True, width=120, group="Key"),
        _c("isin", "ISIN", TEXT, width=140, group="Key"),
        _c("vendor_industry", "Vendor Industry", TEXT, width=200, group="Classification"),
        _c("vendor_sector", "Vendor Sector", TEXT, width=190, group="Classification"),
        _c("company_pe", "PE", NUMBER, width=100, group="Company"),
        _c("company_pb", "P/B", NUMBER, width=100, group="Company"),
        _c("company_peg", "PEG", NUMBER, width=100, group="Company"),
        _c("company_roe", "ROE", NUMBER, width=100, group="Company"),
        _c("company_roa", "ROA", NUMBER, width=100, group="Company"),
        _c("industry_pe", "Industry PE", NUMBER, width=120, group="Industry"),
        _c("industry_pb", "Industry P/B", NUMBER, width=125, group="Industry"),
        _c("industry_peg", "Industry PEG", NUMBER, width=125, group="Industry"),
        _c("industry_roe", "Industry ROE", NUMBER, width=125, group="Industry"),
        _c("industry_roa", "Industry ROA", NUMBER, width=125, group="Industry"),
        _c("sector_pe", "Sector PE", NUMBER, width=115, group="Sector"),
        _c("sector_pb", "Sector P/B", NUMBER, width=115, group="Sector"),
        _c("sector_peg", "Sector PEG", NUMBER, width=120, group="Sector"),
        _c("sector_roe", "Sector ROE", NUMBER, width=120, group="Sector"),
        _c("sector_roa", "Sector ROA", NUMBER, width=120, group="Sector"),
        *PROVENANCE_COLUMNS,
    ),
)


TABS: tuple[Tab, ...] = (
    COMPANY_MASTER,
    PROFILE_HISTORY,
    DAILY_MARKET_HISTORY,
    EXCHANGE_SESSIONS,
    FINANCIALS_ANNUAL,
    FINANCIALS_QUARTERLY,
    COMPANY_IDENTITY_MAP,
    CAPIQ_METRIC_MAPPING,
    FINANCIAL_IMPORT_AUDIT,
    SHARE_COUNT_HISTORY,
    HISTORICAL_RATIOS,
    ANNUAL_SECTOR_RATIOS,
    SECTOR_RATIO_HISTORY,
    HISTORICAL_VALUATION,
    LIVE_VALUATION_STATE,
    VALUATION_SNAPSHOTS,
    CONSENSUS,
    CONSENSUS_METRIC_VINTAGES,
    RESEARCH_INTELLIGENCE,
    RESEARCH_TIMELINE,
    CORPORATE_ACTIONS,
    OWNERSHIP,
    INSIDER_TRADES,
    FUNDAMENTALS_REFRESH_QUEUE,
    PEER_RELATIONSHIPS,
    FWCP_IMPORT_QUEUE,
    INSTITUTIONAL_FLOW,
    VALUATION_RATIOS,
    BOOTSTRAP_RUNS,
    INGESTION_HEALTH,
    HVIE_COMPANY_STATE,
    HISTORICAL_STATISTICS,
    HISTORICAL_SECTOR_MEDIANS,
    HISTORICAL_IMPORT_REGISTRY,
    HISTORICAL_INDUSTRY_MEDIANS,
    HISTORICAL_MARKET_MEDIANS,
    VENDOR_RISK_METRICS,
    VENDOR_LIQUIDITY,
    VENDOR_PRICE_HISTORY,
    VENDOR_INDUSTRY_CONTEXT,
    HVIE_UNIVERSE_QUEUE,
    DAILY_INTELLIGENCE_CHANGES,
    RIE_COMPANY_DOSSIER,
    FORECAST_COMPANY,
    FORECAST_HISTORY,
    FORECAST_SCENARIOS,
    FORECAST_ASSUMPTIONS,
    FORECAST_CONFIDENCE,
    FORECAST_METRIC_PREDICTIONS,
    FORECAST_SNAPSHOTS,
    FORECAST_EVALUATIONS,
    FORECAST_ACCURACY,
    FORECAST_LEARNINGS,
    FORECAST_RUNTIME,
    STRATEGY_PAPER_SNAPSHOTS,
    STRATEGY_PAPER_OUTCOMES,
    PORTFOLIO_SNAPSHOTS,
    PORTFOLIO_HOLDINGS,
    PORTFOLIO_DAILY_RETURNS,
    PORTFOLIO_ATTRIBUTION,
    MACRO_SERIES,
    MACRO_LATEST,
    MACRO_EVENTS,
    MACRO_REGIMES,
    MACRO_HISTORY,
    MACRO_FORECASTS,
    MACRO_RELATIONSHIPS,
    MACRO_ALERTS,
    MACRO_CALENDAR,
    MACRO_RUNTIME,
    SECTOR_EVIDENCE_MATRIX,
    HEDGE_FUND_FACTORS,
    COMPANY_INTELLIGENCE,
    DATA_QUALITY,
)

_BY_ID = {t.id: t for t in TABS}


def _assert_unique_columns() -> None:
    """Fail fast if any tab declares duplicate column keys (breaks CREATE TABLE)."""
    for t in TABS:
        seen: set[str] = set()
        for col in t.columns:
            key = str(col.key)
            if key in seen:
                raise ValueError(f"duplicate_column:{t.id}.{key}")
            seen.add(key)


_assert_unique_columns()


def tab(tab_id: str) -> Tab:
    key = (tab_id or "").strip().lower()
    if key not in _BY_ID:
        raise KeyError(f"unknown_warehouse_tab:{tab_id}")
    return _BY_ID[key]


def tab_ids() -> list[str]:
    return [t.id for t in TABS]


def find_tab(tab_id: str) -> Optional[Tab]:
    return _BY_ID.get((tab_id or "").strip().lower())


def workbook() -> dict[str, Any]:
    """Full workbook description for the admin workspace."""
    return {
        "ok": True,
        "workbook": "AGI Institutional Data Warehouse",
        "tab_count": len(TABS),
        "tabs": [t.to_dict() for t in TABS],
        "system_columns": list(SYSTEM_COLUMNS),
    }


def entity_tabs() -> Iterable[Tab]:
    """Tabs that carry a company entity column (used by global search / company view)."""
    return (t for t in TABS if t.entity_column)
