from __future__ import annotations

import pytest

from financial_warehouse_completion.capiq_normalization import (
    audit_and_prepare,
    reconcile_derived_fields,
    resolve_identity,
)


def _masters():
    return {
        "TCS": {
            "company_id": "1", "symbol": "TCS", "isin": "INE467B01029",
            "company_name": "Tata Consultancy Services Limited", "sector": "Information Technology",
        },
        "ICICIBANK": {
            "company_id": "2", "symbol": "ICICIBANK", "isin": "INE090A01021",
            "company_name": "ICICI Bank Limited", "sector": "Financials",
        },
    }


def test_exact_symbol_identity_is_verified_and_classified():
    result = resolve_identity({"symbol": "ICICIBANK"}, _masters())
    assert result["identity_status"] == "VERIFIED"
    assert result["identity_map"]["match_method"] == "SYMBOL_EXACT"
    assert result["identity_map"]["company_type"] == "BANK"


def test_unmatched_company_is_held_not_written():
    prepared = audit_and_prepare(
        [{"symbol": "UNKNOWN", "fiscal_year": "FY2025", "pat": 10, "assets": 20, "equity": 5}],
        field_map={"PAT": "pat", "Total Assets": "assets", "Total Equity": "equity"},
        source_file="2016-2026.xlsx", masters=_masters(),
    )
    assert prepared["accepted"] == []
    assert prepared["audits"][0]["overall_status"] == "REVIEW_REQUIRED"
    assert prepared["audits"][0]["write_status"] == "QUARANTINED"


def test_verified_company_period_has_all_required_fields_before_release():
    prepared = audit_and_prepare(
        [{"symbol": "TCS", "fiscal_year": "FY2025", "pat": 100, "assets": 500, "equity": 300, "revenue": 1000}],
        field_map={"PAT": "pat", "Total Assets": "assets", "Total Equity": "equity", "Revenue": "revenue"},
        source_file="2016-2026.xlsx", masters=_masters(),
    )
    assert len(prepared["accepted"]) == 1
    assert prepared["audits"][0]["overall_status"] == "VERIFIED"
    assert prepared["audits"][0]["required_fields_found"] == 3


def test_stale_workbook_formulas_are_rebuilt_from_statement_components():
    row, repaired = reconcile_derived_fields({
        "current_assets": 103193.1, "current_liabilities": 37331.0,
        "working_capital": -103165.96, "cfo": -24108.7, "capex": -552.4,
        "free_cash_flow": -2479.76,
    })
    assert row["working_capital"] == 65862.1
    assert row["free_cash_flow"] == pytest.approx(-24661.1)
    assert repaired == ["working_capital", "free_cash_flow"]


def test_accepted_row_and_audit_carry_reconciled_values():
    prepared = audit_and_prepare(
        [{"symbol": "TCS", "fiscal_year": "FY2025", "pat": 100, "assets": 500,
          "equity": 300, "current_assets": 200, "current_liabilities": 80,
          "working_capital": -999}],
        field_map={"PAT": "pat", "Total Assets": "assets", "Total Equity": "equity",
                   "Working Capital": "working_capital"},
        source_file="2016-2026.xlsx", masters=_masters(),
    )
    assert prepared["accepted"][0]["working_capital"] == 120
    assert prepared["audits"][0]["reconciliation"] == "REPAIRED"
    assert prepared["audits"][0]["repaired_fields"] == ["working_capital"]


def test_negative_equity_is_retained_as_a_warning_not_quarantined():
    prepared = audit_and_prepare(
        [{"symbol": "TCS", "fiscal_year": "FY2025", "pat": -10, "assets": 500,
          "equity": -30, "revenue": 1000}],
        field_map={"PAT": "pat", "Total Assets": "assets", "Total Equity": "equity",
                   "Revenue": "revenue"},
        source_file="2016-2026.xlsx", masters=_masters(),
    )
    assert len(prepared["accepted"]) == 1
    assert prepared["audits"][0]["data_warnings"] == ["equity", "pat"]
    assert prepared["audits"][0]["quarantine_reasons"] == []


def test_zero_assets_remains_quarantined():
    prepared = audit_and_prepare(
        [{"symbol": "TCS", "fiscal_year": "FY2025", "pat": 10, "assets": 0,
          "equity": -30, "revenue": 1000}],
        field_map={"PAT": "pat", "Total Assets": "assets", "Total Equity": "equity",
                   "Revenue": "revenue"},
        source_file="2016-2026.xlsx", masters=_masters(),
    )
    assert prepared["accepted"] == []
    assert "suspicious_zeros:assets" in prepared["audits"][0]["quarantine_reasons"]
