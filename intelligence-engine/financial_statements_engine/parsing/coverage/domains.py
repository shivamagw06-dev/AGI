"""Evidence domain catalogue — expected metrics, support, presence signals."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.parsing.coverage.schema import DOMAIN_DISPLAY, EVIDENCE_DOMAINS

# Core expected metrics per supported domain (canonical Metric Registry ids).
# Empty expected_metrics ⇒ status driven by presence / support only.
_DOMAIN_SPECS: dict[str, dict[str, Any]] = {
    "income_statement": {
        "expected_metrics": (
            "revenue",
            "profit_before_tax",
            "net_income",
            "tax_expense",
            "finance_cost",
        ),
        "parser_support": "supported",
        "section_aliases": ("income_statement", "profit_and_loss", "statement_of_profit_and_loss", "pnl"),
        "expectation": "core",  # expected in annual/quarterly filings
    },
    "balance_sheet": {
        "expected_metrics": (
            "total_assets",
            "total_equity",
            "total_liabilities",
            "cash",
            "current_assets",
            "current_liabilities",
        ),
        "parser_support": "supported",
        "section_aliases": ("balance_sheet", "statement_of_financial_position", "assets_liabilities"),
        "expectation": "core",
    },
    "cash_flow": {
        "expected_metrics": (
            "operating_cash_flow",
            "investing_cash_flow",
            "financing_cash_flow",
            "net_cash_change",
        ),
        "parser_support": "supported",
        "section_aliases": ("cash_flow", "cash_flow_statement", "statement_of_cash_flows"),
        "expectation": "core",
    },
    "equity_changes": {
        "expected_metrics": ("total_equity", "retained_earnings", "share_capital"),
        "parser_support": "unsupported",
        "section_aliases": ("equity_changes", "statement_of_changes_in_equity", "soci"),
        "expectation": "optional",
    },
    "quarterly_results": {
        "expected_metrics": ("revenue", "net_income"),
        "parser_support": "supported",
        "section_aliases": ("quarterly_results", "quarterly", "q1", "q2", "q3", "q4"),
        "expectation": "period_quarterly",
    },
    "annual_results": {
        "expected_metrics": ("revenue", "net_income", "total_assets"),
        "parser_support": "supported",
        "section_aliases": ("annual_results", "annual", "yearly"),
        "expectation": "period_annual",
    },
    "segment_reporting": {
        "expected_metrics": ("segment_revenue", "segment_profit", "segment_assets"),
        "parser_support": "supported",
        "section_aliases": ("segment", "segment_reporting", "segment_statement"),
        "expectation": "optional",
    },
    "share_capital": {
        "expected_metrics": ("share_capital", "shares_outstanding", "face_value"),
        "parser_support": "supported",
        "section_aliases": ("share_capital", "equity_share_capital"),
        "expectation": "optional",
    },
    "eps": {
        "expected_metrics": ("eps_basic", "eps_diluted"),
        "parser_support": "supported",
        "section_aliases": ("eps", "earnings_per_share"),
        "expectation": "optional",
    },
    "dividend": {
        "expected_metrics": (),
        "parser_support": "unsupported",
        "section_aliases": ("dividend", "dividends"),
        "expectation": "optional",
    },
    "debt_schedule": {
        "expected_metrics": ("total_debt",),
        "parser_support": "unsupported",
        "section_aliases": ("debt", "debt_schedule", "borrowings"),
        "expectation": "optional",
    },
    "lease_liabilities": {
        "expected_metrics": (),
        "parser_support": "unsupported",
        "section_aliases": ("lease", "lease_liabilities", "leases"),
        "expectation": "optional",
    },
    "deferred_tax": {
        "expected_metrics": (),
        "parser_support": "unsupported",
        "section_aliases": ("deferred_tax",),
        "expectation": "optional",
    },
    "working_capital": {
        "expected_metrics": ("working_capital", "receivables", "inventory"),
        "parser_support": "supported",
        "section_aliases": ("working_capital",),
        "expectation": "optional",
    },
    "related_party": {
        "expected_metrics": (),
        "parser_support": "unsupported",
        "section_aliases": ("related_party", "related_party_transactions", "rpt"),
        "expectation": "optional",
    },
    "auditor": {
        "expected_metrics": (),
        "parser_support": "unsupported",
        "section_aliases": ("auditor", "audit_report", "auditors_report"),
        "expectation": "optional",
    },
    "mda": {
        "expected_metrics": (),
        "parser_support": "unsupported",
        "section_aliases": ("mda", "md_a", "management_discussion", "management_discussion_and_analysis"),
        "expectation": "optional",
    },
    "corporate_info": {
        "expected_metrics": (),
        "parser_support": "unsupported",
        "section_aliases": ("corporate_info", "corporate_information", "company_information"),
        "expectation": "optional",
    },
    "notes": {
        "expected_metrics": (),
        "parser_support": "unsupported",
        "section_aliases": ("notes", "notes_to_accounts", "notes_to_financial_statements"),
        "expectation": "optional",
    },
    "accounting_policies": {
        "expected_metrics": (),
        "parser_support": "unsupported",
        "section_aliases": ("accounting_policies", "significant_accounting_policies"),
        "expectation": "optional",
    },
    "contingent_liabilities": {
        "expected_metrics": (),
        "parser_support": "unsupported",
        "section_aliases": ("contingent_liabilities", "contingencies"),
        "expectation": "optional",
    },
    "capital_commitments": {
        "expected_metrics": (),
        "parser_support": "unsupported",
        "section_aliases": ("capital_commitments", "commitments"),
        "expectation": "optional",
    },
    "subsidiaries": {
        "expected_metrics": (),
        "parser_support": "unsupported",
        "section_aliases": ("subsidiaries", "subsidiary"),
        "expectation": "optional",
    },
    "joint_ventures": {
        "expected_metrics": (),
        "parser_support": "unsupported",
        "section_aliases": ("joint_ventures", "joint_venture"),
        "expectation": "optional",
    },
    "associates": {
        "expected_metrics": (),
        "parser_support": "unsupported",
        "section_aliases": ("associates", "associate"),
        "expectation": "optional",
    },
    "financial_instruments": {
        "expected_metrics": (),
        "parser_support": "unsupported",
        "section_aliases": ("financial_instruments",),
        "expectation": "optional",
    },
    "oci": {
        "expected_metrics": (),
        "parser_support": "unsupported",
        "section_aliases": ("oci", "other_comprehensive_income"),
        "expectation": "optional",
    },
}


def assert_domain_catalogue_complete() -> None:
    missing = [d for d in EVIDENCE_DOMAINS if d not in _DOMAIN_SPECS]
    if missing:
        raise RuntimeError(f"coverage_domain_catalogue_incomplete: {missing}")


assert_domain_catalogue_complete()


def domain_spec(domain_key: str) -> dict[str, Any]:
    spec = _DOMAIN_SPECS[domain_key]
    return {
        "domain": domain_key,
        "section_name": DOMAIN_DISPLAY[domain_key],
        "expected_metrics": list(spec["expected_metrics"]),
        "parser_support": spec["parser_support"],
        "section_aliases": list(spec["section_aliases"]),
        "expectation": spec["expectation"],
    }


def all_domain_specs() -> list[dict[str, Any]]:
    return [domain_spec(k) for k in EVIDENCE_DOMAINS]


def normalize_section_token(value: str) -> str:
    return str(value or "").strip().lower().replace(" ", "_").replace("-", "_")


def section_present(domain_key: str, sections_found: list[str] | None) -> bool:
    aliases = {normalize_section_token(a) for a in _DOMAIN_SPECS[domain_key]["section_aliases"]}
    found = {normalize_section_token(s) for s in (sections_found or [])}
    return bool(aliases & found)
