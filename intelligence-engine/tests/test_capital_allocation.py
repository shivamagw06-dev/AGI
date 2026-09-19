"""FIL — capital allocation engine."""

from __future__ import annotations

from filing_intelligence.ingestion.store import reset_for_tests
from filing_intelligence.pipeline import analyse_ticker


def setup_function() -> None:
    reset_for_tests()


def test_hdfc_capital_rationale():
    out = analyse_ticker("HDFCBANK")
    caps = out["capital_allocation"]
    assert caps
    rationale = next((c for c in caps if c["metric"] == "Allocation_Rationale"), None)
    assert rationale is not None
    assert "resilience" in str(rationale["value"]).lower() or "organic" in str(rationale["value"]).lower()
