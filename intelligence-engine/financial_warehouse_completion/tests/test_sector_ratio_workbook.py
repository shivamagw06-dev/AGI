from __future__ import annotations

from financial_warehouse_completion import sector_ratio_workbook


def test_preview_reads_ten_year_capiq_sector_ratio_history():
    result = sector_ratio_workbook.preview()
    assert result["ok"] is True
    assert result["companies"] == 2627  # companies with at least one reported ratio
    assert result["rows"] == 139639
    assert result["years"] == [f"FY{year}" for year in range(2016, 2026)]
    assert {"pe", "pb", "ev_ebitda", "roe", "fcf_yield"} <= set(result["metrics"])


def test_tcs_ratio_row_is_normalised_and_source_traceable():
    row = next(
        item for item in sector_ratio_workbook._rows()
        if item["symbol"] == "TCS" and item["fiscal_year"] == "FY2025" and item["metric"] == "pe"
    )
    assert row["sector"] == "Information Technology"
    assert row["source_sector"] == "IT"
    assert row["as_of"] == "2025-03-31"
    assert row["source_version"] == sector_ratio_workbook.SOURCE_VERSION
    assert row["median_eligibility"] == "ELIGIBLE"
    assert row["value"] > 0


def test_vendor_error_markers_are_not_parsed_as_ratios():
    assert sector_ratio_workbook._number("8308") is None
    assert sector_ratio_workbook._number(8308) is None
    assert sector_ratio_workbook._number("#DIV/0!") is None
    assert sector_ratio_workbook._number("  N/A ") is None
    assert sector_ratio_workbook._number(12.5) == 12.5
