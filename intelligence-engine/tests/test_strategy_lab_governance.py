from strategy_lab import production
from datetime import datetime
from zoneinfo import ZoneInfo


def _row(symbol: str, day: str, close: float = 100.0) -> dict:
    return {
        "symbol": symbol,
        "date": day,
        "close": close,
        "adjusted_close": close,
        "high": close + 1,
        "low": close - 1,
        "volume": 100_000,
    }


def test_common_session_excludes_partial_intraday_and_stale_symbols():
    rows = []
    for ticker in ("A", "B", "C", "D", "E"):
        rows.extend([_row(ticker, "2026-08-12"), _row(ticker, "2026-08-13")])
    rows.append(_row("A", "2026-08-14", 101.0))
    rows = [row for row in rows if not (row["symbol"] == "E" and row["date"] == "2026-08-13")]

    series, health = production._series_snapshot(rows, expected_session="2026-08-13")

    assert health["latest_completed_session"] == "2026-08-13"
    assert health["freshness_status"] == "PASS"
    assert health["completeness_status"] == "PASS"
    assert health["mixed_session_blocked"] == 1
    assert "E" not in series
    assert series["A"][-1]["date"] == "2026-08-13"


def test_freshness_is_independent_from_universe_completeness():
    rows = [_row("A", "2026-08-14"), _row("B", "2026-08-13")]

    _, health = production._series_snapshot(rows, expected_session="2026-08-14")
    health["coverage_threshold"] = 160
    health["completeness_status"] = "FAIL"
    health["session_status"] = "FAIL"
    decision = production._registry_decision("time_series_momentum", health)

    assert health["freshness_status"] == "PASS"
    assert decision["evidence"]["data_freshness"]["status"] == "PASSED"
    assert decision["evidence"]["data_completeness"]["status"] == "FAILED"


def test_expected_session_prefers_official_exchange_calendar(monkeypatch):
    monkeypatch.setattr("institutional_warehouse.db.physical_table", lambda _tab: "wh_exchange_sessions")
    monkeypatch.setattr("institutional_warehouse.db.query", lambda _sql, _params: [{
        "date": "2026-08-14",
        "calendar_source": "upstox_holidays_plus_market_timings",
        "observed_at": "2026-08-17T01:00:00Z",
    }])
    now = datetime(2026, 8, 17, 17, 0, tzinfo=ZoneInfo("Asia/Kolkata"))

    receipt = production._expected_completed_session_receipt(now)

    assert receipt["date"] == "2026-08-14"
    assert receipt["status"] == "OFFICIAL"
    assert receipt["source"] == "upstox_holidays_plus_market_timings"


def test_catalog_uses_formal_lifecycle_and_blocks_unimplemented_families():
    assert production.REGISTRY["time_series_momentum"]["lifecycle"] == "IMPLEMENTED"
    assert production.REGISTRY["cross_sectional_momentum"]["lifecycle"] == "IMPLEMENTED"
    assert production.REGISTRY["event_strategies"]["category"] == "BLOCKED"
    assert "EXECUTION_ELIGIBLE" in production.LIFECYCLE


def test_health_reports_the_price_universe_used_by_strategy_lab(monkeypatch):
    monkeypatch.setattr(production, "_canonical_strategy_symbols", lambda: ["A", "B"])
    monkeypatch.setattr("institutional_warehouse.db.physical_table", lambda _tab: "wh_daily_market_history")
    monkeypatch.setattr("institutional_warehouse.db.query", lambda _sql, _params: [{
        "count": 2,
        "latest_session": "2026-08-14",
    }])
    monkeypatch.setattr("strategy_lab.registry_store.table_health", lambda: {"ok": True})

    result = production.health()

    assert result["warehouse_universe"] == 2
    assert result["strategy_universe"] == "canonical_nifty_200"
    assert result["strategy_universe_coverage"] == {
        "count": 2,
        "expected": 2,
        "latest_session": "2026-08-14",
        "source": "warehouse.daily_market_history",
    }


def test_cross_sectional_momentum_has_its_own_governed_backtest(monkeypatch):
    monkeypatch.setattr("hedge_fund_lab.backtests.run_from_warehouse", lambda key, config: {
        "ok": False, "error": key, "validation": {}, "constraints": {}, "metrics": {},
    })
    result = production.backtest("cross_sectional_momentum")
    assert result["strategy_lab_id"] == "cross_sectional_momentum"
    assert result["error"] == "cross_sectional_momentum"
    assert result["validation"]["promotion"] == "DO_NOT_DEPLOY"
    assert result["registry_evidence"]["parameter_stability"]["status"] == "FAILED"


def test_quality_momentum_routes_to_fail_closed_readiness_audit(monkeypatch):
    monkeypatch.setattr("hedge_fund_lab.backtests.run_from_warehouse", lambda key, config: {
        "ok": False, "error": key, "readiness": {"status": "BLOCKED"},
    })
    result = production.backtest("quality_momentum")
    assert result["error"] == "quality_momentum"
    assert result["validation"]["economic_gates_passed"] is False
    assert result["validation"]["promotion"] == "DO_NOT_DEPLOY"

    result = production.scan("event_strategies")

    assert result["ok"] is True
    assert result["status"] == "BLOCKED"
    assert result["signals"] == []
    assert "EVENT_TIMESTAMP_MISSING" in result["reason_codes"]


def test_signal_governance_cannot_self_promote():
    signal = production._govern_signal({
        "signal": "BUY",
        "score": 72,
        "data": {"liquid": True},
        "governance": {},
        "reason_codes": ["POSITIVE_ABSOLUTE_TREND"],
    })

    assert signal["research_direction"] == "LONG"
    assert signal["eligibility"] == "BLOCKED"
    assert signal["trade_eligible"] is False
    assert signal["governance"]["execution"] == "BLOCKED"
    assert "BACKTEST_INSUFFICIENT" in signal["reason_codes"]
    assert "CORPORATE_ACTION_UNVERIFIED" in signal["reason_codes"]


def test_registry_separates_lifecycle_from_current_health():
    decision = production._registry_decision("trend_following", {
        "session_status": "PASS",
        "latest_completed_session": "2026-08-14",
        "session_coverage": 180,
        "coverage_threshold": 160,
    })

    assert decision["requested_lifecycle"] == "OPERATIONAL"
    assert decision["lifecycle"] == "OPERATIONAL"
    assert decision["health"] == "HEALTHY"
    assert decision["execution"] == "BLOCKED"
