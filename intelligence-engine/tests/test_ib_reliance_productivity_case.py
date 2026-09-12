"""IB-01 productivity case — Reliance investment note metrics."""

from __future__ import annotations

from institutional_grade_benchmark.cases.reliance_productivity import (
    FACTUAL_CORRECTIONS,
    RELIANCE_TICKER,
    run_reliance_productivity_case,
)
from institutional_grade_benchmark.production import reliance_productivity_api, reset_for_tests


def setup_function():
    reset_for_tests()


def test_reliance_case_metrics_shape():
    out = run_reliance_productivity_case(generate_draft=True)
    assert out["ticker"] == RELIANCE_TICKER
    m = out["metrics"]
    assert m["time_to_first_draft_ms"] is not None
    assert m["time_to_first_draft_ms"] < 60_000
    assert m["factual_corrections"] == len(FACTUAL_CORRECTIONS) == 8
    assert m["completeness_score"] == 78
    assert m["blind_reviewer_quality_score"] == 72
    assert m["confidence_level"] == 0.45
    assert m["sources_cited"] == 5
    assert m["primary_filings_attached"] == 0
    assert out["verdict"]["materially_more_productive"] is True
    assert out["verdict"]["replaces_analyst"] is False
    assert out["verdict"]["beats_bloomberg_this_run"] is False


def test_corrections_include_bank_language_and_stance_conflict():
    issues = " ".join(c["issue"].lower() for c in FACTUAL_CORRECTIONS)
    assert "nim" in issues or "npa" in issues or "bank" in issues
    assert "sell" in issues and "neutral" in issues


def test_api_facade():
    out = reliance_productivity_api({"generate_draft": True})
    assert out["ok"] is True
    assert out["case_id"] == "IB-PROD-RELIANCE-001"
    assert out["artifacts"]["investment_note"].endswith("RELIANCE_INVESTMENT_NOTE.md")


def test_skip_draft_still_returns_scorecard():
    out = run_reliance_productivity_case(generate_draft=False)
    assert out["metrics"]["factual_corrections"] == 8
    assert out["draft"]["ok"] is False
