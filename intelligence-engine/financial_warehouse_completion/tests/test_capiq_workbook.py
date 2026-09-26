from __future__ import annotations

from financial_warehouse_completion import capiq_workbook


def test_preview_reads_completed_capital_iq_sheets():
    result = capiq_workbook.preview()
    assert result["ok"] is True
    assert result["unit"] == "INR million"
    assert result["years"]["2017"] > 3000
    assert result["years"]["2024"] > 3000
    assert result["years"]["2026"] > 3000
    assert result["diagnostics"]["pit_status"] == "PIT_LIMITED"
    assert result["diagnostics"]["sheets"]["Income Statement"]["vendor_error"] == 5550


def test_sheet_rows_normalise_ticker_and_stamp_identity():
    row = next(item for item in capiq_workbook._master_rows(path=capiq_workbook.WORKBOOK_PATH)
               if item["symbol"] == "TCS" and item["fiscal_year"] == "FY2024")
    assert row["fiscal_year"] == "FY2024"
    assert row["statement_type"] == "UNKNOWN"
    assert row["statement_frequency"] == "ANNUAL"
    assert row["revenue"] > 0
    assert row["pat"] > 0
    assert row["accounts_receivable"] >= 0
    assert row["pit_status"] == "PIT_LIMITED"
    assert row["source_document"] == "Master_10Y_India.xlsx"
    assert set(row["source_sheets"]) == {"Income Statement", "Balance Sheet", "Cash Flow"}
    assert row["depreciation"] is not None and row["depreciation_cash_flow"] is not None
    assert row["source_mnemonics"]["depreciation"] != row["source_mnemonics"]["depreciation_cash_flow"]
    assert "minority_interest" in row
    assert "balance_sheet_minority_interest" in row
