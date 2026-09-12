"""FDI — statement diff."""

from __future__ import annotations

from filing_diff.comparator.periods import load_comparison_context
from filing_diff.statement_diff.diff import statement_diff
from filing_intelligence.ingestion.store import reset_for_tests


def setup_function() -> None:
    reset_for_tests()


def test_nim_and_casa_compression():
    ctx = load_comparison_context("HDFCBANK")
    rows = {r.metric: r for r in statement_diff(ctx)}
    assert rows["NIM"].change_type == "margin_compression"
    assert rows["CASA"].change_type == "casa_decline"
    assert rows["NIM"].previous_value == 3.40
    assert rows["NIM"].current_value == 3.26
