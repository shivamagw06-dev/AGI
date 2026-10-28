"""Coverage engine, intent parsing and the span guard — the honesty machinery."""

from __future__ import annotations

import os
import tempfile
from datetime import date, datetime, timedelta, timezone

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="hie_cov_"))

from historical_intelligence import coverage, intent, span_guard  # noqa: E402
from institutional_warehouse import db, store  # noqa: E402


@pytest.fixture(autouse=True)
def warehouse(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    db.reset_backend()
    db.init(force=True)
    store.upsert(
        "company_master",
        [{"company_id": "DEEP", "symbol": "DEEP", "company_name": "Deep History Ltd",
          "sector": "Industrials"},
         {"company_id": "THIN", "symbol": "THIN", "company_name": "Thin History Ltd",
          "sector": "Industrials"}],
        source="test", actor="tester",
    )
    # DEEP: twenty years of monthly prices. THIN: three years.
    _seed_prices("DEEP", 2006, 20)
    _seed_prices("THIN", 2023, 3)
    yield
    db.reset_backend()


def _seed_prices(symbol: str, start_year: int, years: int, base: float = 100.0) -> None:
    rows, price = [], base
    for year in range(start_year, start_year + years):
        for month in range(1, 13):
            rows.append({"symbol": symbol, "date": date(year, month, 28).isoformat(),
                         "close": round(price, 2)})
            price *= 1.01
    store.upsert("daily_market_history", rows, source="test", actor="tester")


# --------------------------------------------------------------------------
# Coverage
# --------------------------------------------------------------------------


def test_coverage_reports_span_density_and_confidence():
    cover = coverage.metric_coverage("DEEP", "price")
    assert cover["ok"] is True
    assert cover["earliest"].startswith("2006")
    assert cover["observations"] == 240
    assert cover["years"] > 19
    assert cover["confidence"] == coverage.STRONG
    assert "2006" in cover["window_label"]


def test_a_short_series_gets_lower_confidence_than_a_long_one():
    deep = coverage.metric_coverage("DEEP", "price")
    thin = coverage.metric_coverage("THIN", "price")
    assert deep["confidence_score"] > thin["confidence_score"]
    assert thin["confidence"] in (coverage.MODERATE, coverage.WEAK)


def test_coverage_is_per_metric_not_per_dataset():
    """Price and P/B live in different tabs and must report different spans."""
    store.upsert(
        "historical_valuation",
        [{"symbol": "DEEP", "date": "2024-06-28", "pb": 2.0},
         {"symbol": "DEEP", "date": "2025-06-28", "pb": 2.4}],
        source="test", actor="tester",
    )
    price = coverage.metric_coverage("DEEP", "price")
    pb = coverage.metric_coverage("DEEP", "pb")
    assert price["earliest"] < pb["earliest"]
    assert price["observations"] > pb["observations"]
    assert pb["earliest"].startswith("2024")


def test_a_metric_with_no_history_reports_none():
    cover = coverage.metric_coverage("THIN", "revenue")
    assert cover["observations"] == 0
    assert cover["confidence"] == coverage.NONE
    assert cover["window_label"] == "no observations"


def test_company_coverage_summarises_in_a_readable_line():
    report = coverage.company_coverage("DEEP")
    assert "DEEP" in report["summary"]
    assert "price" in report["summary"]
    assert "price" in report["metrics_with_history"]
    assert "revenue" in report["metrics_without_history"]


# --------------------------------------------------------------------------
# Intent
# --------------------------------------------------------------------------


@pytest.mark.parametrize("question", [
    "Show Infosys revenue growth since 2005",
    "When was Axis Bank historically cheapest on price to book?",
    "How has TCS valuation changed over twenty years?",
    "What was Asian Paints doing during COVID?",
    "Compare Reliance before and after Jio",
    "HDFC Bank ROE trend",
])
def test_historical_questions_are_detected(question):
    assert intent.is_historical(question) is True


@pytest.mark.parametrize("question", [
    "Is Axis Bank expensive?",
    "How does Reliance make money?",
    "What is the target price for TCS?",
])
def test_current_state_questions_are_not_historical(question):
    assert intent.is_historical(question) is False


def test_period_extraction_handles_since_rolling_named_and_year():
    today = date(2026, 8, 3)
    assert intent.extract_period("revenue since 2005", today=today)["start"] == "2005-01-01"
    rolling = intent.extract_period("ROE over the last 10 years", today=today)
    assert rolling["start"] == (today - timedelta(days=3652)).isoformat()
    covid = intent.extract_period("valuation during COVID", today=today)
    assert covid["start"] == "2020-02-01" and covid["kind"] == "named"
    assert intent.extract_period("margin in 2019", today=today)["start"] == "2019-01-01"
    assert intent.extract_period("cheapest ever", today=today)["kind"] == "all_time"


def test_metric_extraction_prefers_the_specific_term():
    assert intent.extract_metric("cheapest on price to book") == "pb"
    assert intent.extract_metric("EV/EBITDA history") == "ev_ebitda"
    assert intent.extract_metric("revenue growth") == "revenue"
    assert intent.extract_metric("return on equity trend") == "roe"
    assert intent.extract_metric("how has valuation changed") == "pe"


def test_classification_routes_to_the_right_module():
    assert intent.classify("When was Axis Bank cheapest on P/B?")["module"] == "valuation_extreme"
    assert intent.classify("Compare TCS versus Infosys revenue")["module"] == "comparison"
    assert intent.classify("Show the dividend timeline")["module"] == "events"
    assert intent.classify("Revenue trend since 2010")["module"] == "trend"


# --------------------------------------------------------------------------
# Span guard
# --------------------------------------------------------------------------


def test_guard_allows_a_conclusion_when_the_period_is_covered():
    cover = coverage.metric_coverage("DEEP", "price")
    period = intent.extract_period("price since 2010")
    verdict = span_guard.guard(cover, period)
    assert verdict["verdict"] == span_guard.COVERED
    assert verdict["may_conclude"] is True
    assert "2006" in verdict["disclosure"]


def test_guard_flags_partial_coverage_and_states_the_overlap():
    """The Axis Bank case: asked since 2005, observed from 2023."""
    cover = coverage.metric_coverage("THIN", "price")
    period = intent.extract_period("price since 2005")
    verdict = span_guard.guard(cover, period)
    assert verdict["verdict"] == span_guard.PARTIAL
    assert verdict["overlap_pct"] < 30
    assert "not available" in verdict["disclosure"] or "unavailable" in verdict["disclosure"]
    assert verdict["full_history_claim_allowed"] is False


def test_guard_refuses_when_the_asked_period_is_entirely_unobserved():
    cover = coverage.metric_coverage("THIN", "price")
    period = intent.extract_period("what happened during the GFC")
    verdict = span_guard.guard(cover, period)
    assert verdict["verdict"] == span_guard.OUTSIDE
    assert verdict["may_conclude"] is False
    assert "not observed" in verdict["disclosure"]


def test_guard_refuses_when_there_is_no_history_at_all():
    cover = coverage.metric_coverage("THIN", "revenue")
    verdict = span_guard.guard(cover, intent.extract_period("revenue since 2005"))
    assert verdict["verdict"] == span_guard.NO_DATA
    assert verdict["may_conclude"] is False
    assert "no historical" in verdict["disclosure"]


def test_an_all_time_claim_needs_the_full_window():
    thin = coverage.metric_coverage("THIN", "price")
    partial = span_guard.guard(thin, intent.extract_period("cheapest since 2005"))
    assert span_guard.extreme_claim_allowed(partial) is False
    assert "observed window only" in span_guard.qualify_extreme(partial, thin)

    deep = coverage.metric_coverage("DEEP", "price")
    covered = span_guard.guard(deep, intent.extract_period("cheapest since 2010"))
    assert span_guard.extreme_claim_allowed(covered) is True
