"""FSE-04.2 Evidence Coverage Matrix contracts."""

from __future__ import annotations

WORKSTREAM_ID = "FSE-04.2"
VERSION = "1.0.0"
SUBSYSTEM = "evidence_coverage_matrix"
PROGRAMME = "Financial Statements Engine"

# Exact extraction statuses — every section has exactly one
EXTRACTION_STATUSES = (
    "FOUND",
    "PARTIAL",
    "MISSING",
    "NOT_PRESENT",
    "UNSUPPORTED",
    "PARSE_FAILED",
)

# Domains from the production specification (stable keys)
EVIDENCE_DOMAINS: tuple[str, ...] = (
    "income_statement",
    "balance_sheet",
    "cash_flow",
    "equity_changes",
    "quarterly_results",
    "annual_results",
    "segment_reporting",
    "share_capital",
    "eps",
    "dividend",
    "debt_schedule",
    "lease_liabilities",
    "deferred_tax",
    "working_capital",
    "related_party",
    "auditor",
    "mda",
    "corporate_info",
    "notes",
    "accounting_policies",
    "contingent_liabilities",
    "capital_commitments",
    "subsidiaries",
    "joint_ventures",
    "associates",
    "financial_instruments",
    "oci",
)

DOMAIN_DISPLAY: dict[str, str] = {
    "income_statement": "Income Statement",
    "balance_sheet": "Balance Sheet",
    "cash_flow": "Cash Flow Statement",
    "equity_changes": "Statement of Changes in Equity",
    "quarterly_results": "Quarterly Results",
    "annual_results": "Annual Results",
    "segment_reporting": "Segment Reporting",
    "share_capital": "Share Capital",
    "eps": "EPS",
    "dividend": "Dividend Information",
    "debt_schedule": "Debt Schedule",
    "lease_liabilities": "Lease Liabilities",
    "deferred_tax": "Deferred Tax",
    "working_capital": "Working Capital",
    "related_party": "Related Party Transactions",
    "auditor": "Auditor Information",
    "mda": "Management Discussion",
    "corporate_info": "Corporate Information",
    "notes": "Notes to Accounts",
    "accounting_policies": "Accounting Policies",
    "contingent_liabilities": "Contingent Liabilities",
    "capital_commitments": "Capital Commitments",
    "subsidiaries": "Subsidiaries",
    "joint_ventures": "Joint Ventures",
    "associates": "Associates",
    "financial_instruments": "Financial Instruments",
    "oci": "Other Comprehensive Income",
}

# Operational KPIs (informational — never block publication)
QUALITY_TARGETS: dict[str, float] = {
    "income_statement_coverage": 0.99,
    "balance_sheet_coverage": 0.99,
    "cash_flow_coverage": 0.99,
    "unknown_label_rate": 0.005,
    "unsupported_section_rate": 0.02,
    "coverage_determinism": 1.0,
    "coverage_traceability": 1.0,
    "coverage_history": 1.0,
}

# Material regression threshold for Mission Control alerts (absolute coverage drop)
REGRESSION_ALERT_DROP = 0.05

ISSUES_RECOMMENDATIONS = False
RECOMMENDATION_POLICY = "coverage_never_emits_buy_sell_or_blocks_publication"
