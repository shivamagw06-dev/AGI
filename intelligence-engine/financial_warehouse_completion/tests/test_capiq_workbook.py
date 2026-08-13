from __future__ import annotations

from financial_warehouse_completion import capiq_workbook


def test_preview_reads_completed_capital_iq_sheets():
    result = capiq_workbook.preview()
    assert result["ok"] is True
    assert result["unit"] == "INR million"
    assert result["years"]["2017"] > 3000
    assert result["years"]["2024"] > 3000
    assert result["years"]["2026"] > 3000


def test_sheet_rows_normalise_ticker_and_stamp_identity():
    row = next(item for item in capiq_workbook._master_rows(path=capiq_workbook.WORKBOOK_PATH)
               if item["symbol"] == "TCS" and item["fiscal_year"] == "FY2024")
    assert row["fiscal_year"] == "FY2024"
    assert row["statement_type"] == "UNKNOWN"
    assert row["statement_frequency"] == "ANNUAL"
    assert row["revenue"] > 0
    assert row["pat"] > 0
    assert row["accounts_receivable"] >= 0
