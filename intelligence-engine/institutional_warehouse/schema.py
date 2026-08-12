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
    _c("filing_date", "Filing Date", DATE, width=120, group="Filing"),
    _c("effective_date", "Effective Date", DATE, width=130, group="Filing"),
    _c("restated", "Restated", BOOL, width=100, group="Filing",
       help="Set when this filing revises figures the company published earlier."),
)

_STATEMENT_COLUMNS: tuple[Column, ...] = (
    _c("revenue", "Revenue", CURRENCY, width=130, group="P&L", unit=_MN),
    _c("gross_profit", "Gross Profit", CURRENCY, width=130, group="P&L", unit=_MN),
    _c("ebitda", "EBITDA", CURRENCY, width=120, group="P&L", unit=_MN),
    _c("ebit", "EBIT", CURRENCY, width=120, group="P&L", unit=_MN),
    _c("pbt", "PBT", CURRENCY, width=120, group="P&L", unit=_MN),
    _c("pat", "PAT", CURRENCY, width=120, group="P&L", unit=_MN),
    # Per share, not an aggregate: rescaling this to millions would make every
    # earnings per share read as zero.
    _c("eps", "EPS", NUMBER, width=100, group="P&L", unit=UNIT_INR),
    _c("assets", "Assets", CURRENCY, width=130, group="Balance Sheet", unit=_MN),
    _c("equity", "Equity", CURRENCY, width=130, group="Balance Sheet", unit=_MN),
    _c("debt", "Debt", CURRENCY, width=120, group="Balance Sheet", unit=_MN),
    _c("cash", "Cash", CURRENCY, width=120, group="Balance Sheet", unit=_MN),
    _c("current_assets", "Current Assets", CURRENCY, width=140, group="Balance Sheet", unit=_MN),
    _c("current_liabilities", "Current Liabilities", CURRENCY, width=160, group="Balance Sheet",
       unit=_MN),
    _c("inventory", "Inventory", CURRENCY, width=120, group="Balance Sheet", unit=_MN),
    _c("working_capital", "Working Capital", CURRENCY, width=150, group="Balance Sheet", unit=_MN,
       help="Current Assets - Current Liabilities when both are supplied"),
    _c("capex", "Capex", CURRENCY, width=120, group="Cash Flow", unit=_MN),
    _c("cfo", "CFO", CURRENCY, width=120, group="Cash Flow", unit=_MN),
    _c("cfi", "CFI", CURRENCY, width=120, group="Cash Flow", unit=_MN),
    _c("cff", "CFF", CURRENCY, width=120, group="Cash Flow", unit=_MN),
    _computed("free_cash_flow", "Free Cash Flow", CURRENCY, width=140, group="Cash Flow", unit=_MN,
              help="CFO - Capex"),
    _c("shares_outstanding", "Shares Outstanding", NUMBER, width=160, group="Per Share",
       unit=UNIT_COUNT),
    _computed("book_value", "Book Value", NUMBER, width=120, group="Per Share", unit=UNIT_INR,
              help="Equity / Shares Outstanding"),
    *_FILING_COLUMNS,
    *PROVENANCE_COLUMNS,
    _c("statement_version", "Statement Version", TEXT, editable=False, width=150, group="Provenance"),
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

TABS: tuple[Tab, ...] = (
    COMPANY_MASTER,
    PROFILE_HISTORY,
    DAILY_MARKET_HISTORY,
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
    CONSENSUS,
    RESEARCH_INTELLIGENCE,
    RESEARCH_TIMELINE,
    CORPORATE_ACTIONS,
    OWNERSHIP,
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
