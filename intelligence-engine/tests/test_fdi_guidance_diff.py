"""FDI — guidance diff."""

from __future__ import annotations

from filing_diff.comparator.periods import load_comparison_context
from filing_diff.guidance_diff.diff import guidance_diff
from filing_intelligence.ingestion.store import reset_for_tests


def setup_function() -> None:
    reset_for_tests()


def test_guidance_maintained():
    ctx = load_comparison_context("HDFCBANK")
    rows = guidance_diff(ctx)
    assert rows
    assert rows[0].change_type == "maintained"
    assert rows[0].domain == "guidance"
