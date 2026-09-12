"""FIL — history / time-series engine."""

from __future__ import annotations

from filing_intelligence.ingestion.store import reset_for_tests
from filing_intelligence.pipeline import analyse_ticker


def setup_function() -> None:
    reset_for_tests()


def test_hdfc_cet1_multi_year_from_filings():
    out = analyse_ticker("HDFCBANK")
    series = {s["metric"]: s for s in out["history"]["series"]}
    assert "CET1" in series
    cet1 = series["CET1"]
    assert cet1["latest"] == 17.4
    assert cet1["min"] >= 16.0
    assert cet1["origin"] == "filing_intelligence"
    assert "FY22" in cet1["points"]
    assert cet1["5y_avg"] > 16
