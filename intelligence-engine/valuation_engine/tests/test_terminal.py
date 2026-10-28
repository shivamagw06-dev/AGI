"""Institutional Valuation Terminal — warehouse → engine → pack."""

from __future__ import annotations

from datetime import datetime, timezone

from valuation_engine import health_score, terminal
from valuation_engine.tests.test_valuation_engine import _record


def test_institutional_table_positions_premium_and_discount():
    metrics = {
        "pe": {"value": 18.0, "available": True, "sources": ["upstox"], "missing": [], "note": ""},
        "pb": {"value": 1.2, "available": True, "sources": ["upstox"], "missing": [], "note": ""},
        "roe": {"value": 14.0, "available": True, "sources": ["engine"], "missing": [], "note": ""},
        "ev_ebitda": {"value": None, "available": False, "sources": [], "missing": ["ebitda"], "note": ""},
        "ev_sales": {"value": 2.0, "available": True, "sources": ["engine"], "missing": [], "note": ""},
        "ps": {"value": 1.5, "available": True, "sources": ["engine"], "missing": [], "note": ""},
        "dividend_yield": {"value": 0.8, "available": True, "sources": ["engine"], "missing": [], "note": ""},
        "forward_pe": {"value": None, "available": False, "sources": [], "missing": ["forward_eps"], "note": ""},
    }
    context = {
        "pe": {"sector_median": 15.0, "historical_median": 16.0, "peer_count": 8, "observations": 40},
        "pb": {"sector_median": 1.5, "historical_median": 1.4, "peer_count": 8, "observations": 40},
        "roe": {"sector_median": 12.0, "historical_median": 11.0, "peer_count": 8, "observations": 40},
        "ev_ebitda": {},
        "ev_sales": {"sector_median": 2.0, "historical_median": 2.1},
        "ps": {"sector_median": 1.5, "historical_median": 1.6},
        "dividend_yield": {"sector_median": 1.0, "historical_median": 0.9},
        "forward_pe": {},
    }
    rows = {r["metric"]: r for r in terminal._institutional_table(metrics, context, "machinery")}
    assert rows["pe"]["position"] == "Premium"
    assert rows["pb"]["position"] == "Discount"
    assert rows["roe"]["position"] == "Above"
    assert rows["pe"]["source"] == "upstox"


def test_health_score_rewards_complete_inputs():
    metrics = {
        "cmp": {"available": True},
        "eps": {"available": True},
        "roe": {"available": True},
        "target_price": {"available": True},
    }
    out = health_score.score(
        metrics=metrics,
        coverage={"pct": 90.0},
        provenance={
            "price": {"source": "upstox"},
            "financials": {"source": "upstox_fundamentals"},
            "consensus": {"source": "capital_iq"},
        },
        history_span_years=8.0,
        history_observations=80,
        conflict_count=0,
        override_count=0,
        quality_flags={"dqiv_passed": True},
    )
    assert out["score"] >= 90
    assert out["band"] == "high"
    assert "Live price" in out["reasons_ok"]
    assert "DQIV Passed" in out["reasons_ok"]


def test_health_score_flags_sparse_coverage():
    out = health_score.score(
        metrics={"cmp": {"available": False}, "roe": {"available": False}},
        coverage={"pct": 40.0},
        provenance={"price": {}, "financials": {}, "consensus": {}},
        history_span_years=1.0,
        history_observations=5,
        conflict_count=2,
        override_count=1,
    )
    assert out["score"] < 60
    assert out["band"] == "low"
    assert any("conflict" in r.lower() or "Conflict" in r for r in out["reasons_missing"])


def test_change_log_attributes_price_move():
    history = [
        {"date": "2026-08-01", "pe": 18.0, "pb": 1.5, "market_cap": 100, "eps": 5.0, "price": 90},
        {"date": "2026-08-02", "pe": 17.0, "pb": 1.5, "market_cap": 95, "eps": 5.0, "price": 85},
    ]
    metrics = {
        "pe": {"value": 17.0},
        "pb": {"value": 1.5},
        "market_cap": {"value": 95},
        "cmp": {"value": 85},
        "eps": {"value": 5.0},
        "ev_ebitda": {"value": None},
        "ev_sales": {"value": None},
        "ps": {"value": None},
        "dividend_yield": {"value": None},
        "enterprise_value": {"value": None},
    }
    log = terminal._change_log("AAA", metrics, history)
    assert log["ok"] is True
    assert log["before_date"] == "2026-08-01"
    assert any(e["metric"] == "pe" for e in log["entries"])


def test_explanation_has_five_sections():
    valuation = {
        "metrics": {
            "pe": {"value": 14.0},
            "pb": {"value": 1.7},
        },
        "context": {
            "pe": {"sector_median": 16.0, "historical_median": 15.0, "historical_percentile": 40},
            "pb": {"sector_median": 1.4, "historical_median": 1.8},
        },
        "coverage": {"pct": 80, "available": 8, "applicable": 10},
        "company": {"sector": "Financials"},
    }
    text = terminal._explanation("AXISBANK", valuation, {"current_rank": 3, "universe": 12, "primary_metric": "pb"})
    assert len(text["sections"]) == 5
    assert text["sections"][0]["title"] == "Current valuation"
    assert text["sections"][-1]["title"] == "Bottom line"


def test_relative_score_prefers_discount_and_roe():
    metrics = {"roe": {"value": 20.0}, "pe": {"value": 10.0}}
    context = {
        "pe": {"premium_pct": -20.0, "historical_percentile": 25.0},
        "pb": {},
        "ev_ebitda": {},
    }
    score = terminal._relative_score(metrics, context)
    assert score is not None
    assert score > 50


def test_json_loader_retired():
    from valuation_terminal.ingest import seed_if_needed

    result = seed_if_needed(force=True)
    assert result.get("retired") is True
    assert result.get("reason") == "json_loader_retired"


def test_position_helpers():
    assert terminal._position("pe", 20, 15) == "Premium"
    assert terminal._position("pe", 12, 15) == "Discount"
    assert terminal._position("roe", 15, 12) == "Above"
    assert terminal._position("roe", 10, 12) == "Below"


def test_peer_rank_prefers_same_industry_over_alphabetical_order():
    target = {"industry_dna": "private_banks", "market_cap": 1_000_000}
    same_industry = {"symbol": "ZZZ", "industry_dna": "private_banks", "market_cap": 900_000}
    sector_only = {"symbol": "AAA", "industry_dna": "public_banks", "market_cap": 1_000_000}
    assert terminal._peer_rank(target, same_industry)[0] > terminal._peer_rank(target, sector_only)[0]


def test_freshness_flags_old_intraday_price():
    now = datetime(2026, 8, 5, 6, 0, tzinfo=timezone.utc)  # 11:30 IST weekday
    out = terminal._freshness({"latest_price": {"last_updated": "2026-08-05T05:00:00+00:00"}}, now=now)
    assert out["price_fresh_limit_hours"] == 0.25
    assert any("price stale" in warning for warning in out["warnings"])
