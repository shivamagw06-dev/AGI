"""The five modules, and the promise that none of them concludes beyond its evidence."""

from __future__ import annotations

import os
import tempfile
from datetime import date

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="hie_mod_"))

from historical_intelligence import comparison, composer, events, production, trend, valuation  # noqa: E402
from institutional_warehouse import db, store  # noqa: E402


@pytest.fixture(autouse=True)
def warehouse(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    db.reset_backend()
    db.init(force=True)
    store.upsert(
        "company_master",
        [{"company_id": s, "symbol": s, "company_name": f"{s} Ltd", "sector": "Industrials",
          "industry": "Machinery"} for s in ("DEEP", "THIN", "PEER")],
        source="test", actor="tester",
    )
    yield
    db.reset_backend()


def _prices(symbol: str, start_year: int, years: int, base: float, growth: float = 1.01):
    rows, price = [], base
    for year in range(start_year, start_year + years):
        for month in range(1, 13):
            rows.append({"symbol": symbol, "date": date(year, month, 28).isoformat(),
                         "close": round(price, 2)})
            price *= growth
    store.upsert("daily_market_history", rows, source="test", actor="tester")


def _valuation(symbol: str, series: list[tuple[str, float]], *, sector_median: float | None = None):
    rows = []
    for stamp, pe in series:
        row = {"symbol": symbol, "date": stamp, "pe": pe, "pb": round(pe / 8.0, 3)}
        if sector_median is not None:
            row["sector_median"] = sector_median
            row["percentile"] = 50.0
        rows.append(row)
    store.upsert("historical_valuation", rows, source="test", actor="tester")


def _annuals(symbol: str, start_year: int, years: int, revenue: float, growth: float):
    rows, value = [], revenue
    for year in range(start_year, start_year + years):
        rows.append({"symbol": symbol, "fiscal_year": f"FY{str(year)[-2:]}",
                     "revenue": round(value, 2), "pat": round(value * 0.1, 2),
                     "equity": round(value * 0.5, 2), "shares_outstanding": 100.0})
        value *= growth
    store.upsert("financials_annual", rows, source="test", actor="tester")


# --------------------------------------------------------------------------
# Module 1 — Trend
# --------------------------------------------------------------------------


def test_trend_describes_compounding_and_names_the_window():
    _prices("DEEP", 2006, 20, 100.0)
    result = trend.analyse("DEEP", "price")
    assert result["ok"] is True
    assert result["cagr_pct"] is not None and result["cagr_pct"] > 0
    assert result["points"] == 240
    assert "2006" in result["observation_window"]
    joined = " ".join(result["conclusions"])
    assert "compounding" in joined
    assert "range" in joined


def test_trend_finds_the_turn_in_a_series_that_reverses():
    rows, price = [], 100.0
    for year in range(2010, 2018):          # eight years up
        for month in range(1, 13):
            rows.append({"symbol": "DEEP", "date": date(year, month, 28).isoformat(),
                         "close": round(price, 2)})
            price *= 1.02
    for year in range(2018, 2026):          # eight years down
        for month in range(1, 13):
            rows.append({"symbol": "DEEP", "date": date(year, month, 28).isoformat(),
                         "close": round(price, 2)})
            price *= 0.985
    store.upsert("daily_market_history", rows, source="test", actor="tester")

    result = trend.analyse("DEEP", "price")
    assert result["legs"], "a reversing series must produce legs"
    assert result["inflection_points"], "the turn must be named"
    assert any(str(p).startswith("2017") or str(p).startswith("2018")
               for p in result["inflection_points"])


def test_trend_refuses_when_the_asked_period_is_unobserved():
    _prices("THIN", 2023, 3, 100.0)
    from historical_intelligence import intent

    result = trend.analyse("THIN", "price", period=intent.extract_period("price during the GFC"))
    assert result["conclusions"] == []
    assert "not observed" in result["finding"]


def test_trend_never_reports_a_cagr_for_a_metric_it_has_no_history_for():
    result = trend.analyse("THIN", "revenue")
    assert result["conclusions"] == []
    assert result.get("cagr_pct") is None
    assert "no historical" in result["finding"]


# --------------------------------------------------------------------------
# Module 2 — Valuation
# --------------------------------------------------------------------------


def test_valuation_places_today_against_its_own_median():
    _prices("DEEP", 2016, 10, 100.0)
    _valuation("DEEP", [(f"{y}-03-28", pe) for y, pe in
                        zip(range(2016, 2026), [10, 12, 14, 16, 18, 20, 22, 24, 26, 15])])
    result = valuation.analyse("DEEP", "pe")
    assert result["ok"] is True
    assert result["median"] is not None
    assert result["percentile"] is not None
    joined = " ".join(result["conclusions"])
    assert "median" in joined
    assert "percentile" in joined


def test_valuation_detects_multiple_expansion():
    _prices("DEEP", 2016, 10, 100.0)
    _valuation("DEEP", [(f"{y}-03-28", pe) for y, pe in
                        zip(range(2016, 2026), [8, 9, 10, 11, 20, 22, 24, 26, 28, 30])])
    result = valuation.analyse("DEEP", "pe")
    assert result["rerating"]["direction"] == "expansion"
    assert "re-rated" in result["rerating"]["sentence"]


def test_valuation_says_so_when_there_are_too_few_observations():
    _prices("THIN", 2024, 2, 100.0)
    _valuation("THIN", [("2025-03-28", 12.0), ("2026-03-28", 14.0)])
    result = valuation.analyse("THIN", "pe")
    joined = " ".join(result["conclusions"])
    assert "too few" in joined


def test_valuation_declines_a_cheapest_ever_claim_on_a_short_window():
    """The Axis Bank failure mode, asserted directly."""
    _prices("THIN", 2023, 3, 100.0)
    _valuation("THIN", [("2023-06-28", 3.0), ("2024-06-28", 2.5), ("2026-06-28", 1.7)])
    from historical_intelligence import intent

    result = trend.extreme("THIN", "pb", want="low",
                           period=intent.extract_period("cheapest ever on price to book"))
    joined = " ".join(result["conclusions"])
    assert "observed window only" in joined or "within the observed" in joined
    assert "full listing history" in joined
    assert "cheapest ever" not in joined.lower()


# --------------------------------------------------------------------------
# Module 3 — Events
# --------------------------------------------------------------------------


def test_event_timeline_aligns_actions_with_the_price_move_around_them():
    _prices("DEEP", 2020, 6, 100.0)
    store.upsert(
        "corporate_actions",
        [{"symbol": "DEEP", "action_date": "2022-06-28", "action_type": "dividend",
          "dividend": 5.0},
         {"symbol": "DEEP", "action_date": "2023-06-28", "action_type": "split",
          "split": "2:1"}],
        source="test", actor="tester",
    )
    result = events.timeline("DEEP")
    assert result["event_count"] == 2
    assert any(e.get("move_pct") is not None for e in result["events"])
    joined = " ".join(result["conclusions"])
    assert "does not establish that the event caused it" in joined


def test_named_period_analysis_reports_what_happened_inside_it():
    _prices("DEEP", 2018, 8, 100.0)
    from historical_intelligence import intent

    result = events.around("DEEP", intent.extract_period("what happened during COVID"))
    assert result["ok"] is True
    assert result["change_pct"] is not None
    joined = " ".join(result["conclusions"])
    assert "COVID" in joined
    assert "range" in joined


# --------------------------------------------------------------------------
# Module 4 — Comparison
# --------------------------------------------------------------------------


def test_comparison_uses_only_the_shared_window():
    _prices("DEEP", 2006, 20, 100.0, growth=1.012)
    _prices("PEER", 2020, 6, 100.0, growth=1.004)
    result = comparison.compare(["DEEP", "PEER"], "price")
    assert result["ok"] is True
    assert result["overlap"]["start"].startswith("2020")
    assert result["ranking"][0] == "DEEP"
    joined = " ".join(result["conclusions"])
    assert "window both were observed" in joined
    # DEEP holds far more history than PEER, so the answer must say it is ignored.
    assert "deliberately ignores history" in joined


def test_comparison_declines_when_histories_barely_overlap():
    _prices("DEEP", 2006, 5, 100.0)      # 2006-2010
    _prices("PEER", 2024, 2, 100.0)      # 2024-2025
    result = comparison.compare(["DEEP", "PEER"], "price")
    assert "not supported" in result["finding"]


def test_comparison_reports_a_company_with_no_history():
    _prices("DEEP", 2020, 5, 100.0)
    result = comparison.compare(["DEEP", "THIN"], "price")
    assert "THIN" in result["without_history"]
    assert "fewer than two" in result["finding"]


# --------------------------------------------------------------------------
# Module 5 + composer
# --------------------------------------------------------------------------


def test_every_answer_carries_window_evidence_and_confidence():
    _prices("DEEP", 2006, 20, 100.0)
    result = composer.answer("Show DEEP price trend since 2010", symbol="DEEP")
    assert result["ok"] is True
    closing = result["explain"]
    assert closing["observation_window"]
    assert closing["evidence"] and closing["evidence"][0]["source"].startswith("warehouse.")
    assert closing["confidence"] in ("strong", "moderate", "weak")
    assert "Observed history:" in result["answer"]


def test_a_coverage_limited_question_answers_honestly_rather_than_guessing():
    _prices("THIN", 2023, 3, 100.0)
    result = composer.answer("Show THIN price since 2005", symbol="THIN")
    assert result["ok"] is True
    assert result["coverage_limited"] is True
    assert "2023" in result["answer"]
    assert "unavailable" in result["answer"] or "not available" in result["answer"] \
        or "no claim" in result["answer"]


def test_an_unanswerable_question_returns_the_disclosure_as_the_answer():
    _prices("THIN", 2023, 3, 100.0)
    result = composer.answer("What was THIN doing during the GFC?", symbol="THIN")
    assert result["ok"] is True
    assert "not observed" in result["answer"]
    assert result["conclusions"] == []


def test_composer_needs_a_company():
    result = composer.answer("Show revenue growth since 2005")
    assert result["ok"] is False
    assert result["error"] == "no_company_resolved"


def test_company_history_cards_and_declared_deferrals():
    _prices("DEEP", 2010, 15, 100.0)
    _annuals("DEEP", 2016, 9, 1000.0, 1.15)
    card = composer.company_history("DEEP")
    assert card["ok"] is True
    assert "price" in card["trend_cards"]
    assert card["trend_cards"]["price"]["cagr_pct"] is not None
    # Absent modules are declared, so a consumer knows they are deferred not broken.
    assert "consensus_evolution" in card["deferred_modules"]
    assert "management_evolution" in card["deferred_modules"]


def test_health_declares_modules_and_deferrals():
    report = production.health()
    assert report["engine"] == "historical_intelligence"
    assert "trend" in report["modules"]
    assert set(report["deferred_modules"]) == {
        "consensus_evolution", "management_evolution", "business_evolution", "cycle_intelligence"
    }
    assert report["reads_from"] == "institutional_warehouse"
