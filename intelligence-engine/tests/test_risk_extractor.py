"""FIL — risk extractor."""

from __future__ import annotations

from filing_intelligence.pipeline import analyse_ticker
from filing_intelligence.ingestion.store import reset_for_tests


def setup_function() -> None:
    reset_for_tests()


def test_hdfc_risk_register():
    out = analyse_ticker("HDFCBANK")
    reg = out["risk_register"]
    assert reg["count"] >= 1
    assert reg["current"]
