import math
import sqlite3
import time

import pytest

from options_lab import price_option_snapshot
from options_lab.dashboard import validation_dashboard
from options_lab.store import OptionEvidenceStore
from options_lab.upstox_live import LiveConfig


def _request(**overrides):
    payload = {
        "option_type": "call",
        "spot": 100.0,
        "strike": 100.0,
        "days_to_expiry": 365.0,
        "risk_free_rate_pct": 5.0,
        "dividend_yield_pct": 0.0,
        "model_volatility_pct": 20.0,
        "contract_multiplier": 1.0,
    }
    payload.update(overrides)
    return payload


def test_known_black_scholes_call_value():
    result = price_option_snapshot(_request())

    assert result["valuation"]["model_value"] == pytest.approx(10.4506, abs=1e-4)
    assert result["greeks"]["delta"] == pytest.approx(0.63683, abs=1e-5)
    assert result["model"]["local_only"] is True


def test_call_put_parity_holds():
    call = price_option_snapshot(_request(option_type="call"))
    put = price_option_snapshot(_request(option_type="put"))
    lhs = call["valuation"]["model_value"] - put["valuation"]["model_value"]
    rhs = 100.0 - 100.0 * math.exp(-0.05)

    assert lhs == pytest.approx(rhs, abs=2e-4)


def test_implied_volatility_recovers_market_volatility():
    result = price_option_snapshot(_request(bid=10.45058, ask=10.45059))

    assert result["implied_volatility"]["mid_pct"] == pytest.approx(20.0, abs=1e-3)
    assert result["quality"]["status"] == "usable"
    assert result["valuation"]["assessment"] == "fair"


def test_invalid_market_quote_is_not_given_an_implied_volatility():
    result = price_option_snapshot(_request(bid=150.0, ask=151.0))

    assert result["implied_volatility"]["mid_pct"] is None
    assert result["quality"]["status"] == "invalid_market_quote"
    assert any("no-arbitrage" in warning for warning in result["quality"]["warnings"])


def test_scenarios_are_contract_scaled_and_complete():
    result = price_option_snapshot(_request(bid=10.0, ask=11.0, contract_multiplier=75))

    assert len(result["scenarios"]) == 7
    assert all("pnl_per_contract" in scenario for scenario in result["scenarios"])
    assert result["quality"]["input_provenance"] == "manual_local_snapshot"


def test_crossed_market_is_rejected():
    with pytest.raises(ValueError, match="ask must be greater"):
        price_option_snapshot(_request(bid=12.0, ask=11.0))


def test_validation_dashboard_reads_while_collector_holds_write_lock(tmp_path, monkeypatch):
    database_path = tmp_path / "options.sqlite3"
    store = OptionEvidenceStore(database_path)
    with store.connect() as connection:
        connection.execute(
            """
            INSERT INTO collector_runs(
                run_id, started_at, completed_at, status, expiries_json, counts_json
            ) VALUES ('run-1', '2026-08-24T03:45:00+00:00',
                      '2026-08-24T03:46:00+00:00', 'success', '[]', '{}')
            """
        )

    config = LiveConfig(
        database_path=database_path,
        report_directory=tmp_path / "reports",
    )
    monkeypatch.setattr(
        LiveConfig,
        "from_environment",
        classmethod(lambda cls: config),
    )

    writer = sqlite3.connect(database_path)
    writer.execute("BEGIN IMMEDIATE")
    writer.execute(
        "UPDATE collector_runs SET status = 'running' WHERE run_id = 'run-1'"
    )
    try:
        started = time.monotonic()
        dashboard = validation_dashboard()
        elapsed = time.monotonic() - started
    finally:
        writer.rollback()
        writer.close()

    assert elapsed < 2
    assert dashboard["ok"] is True
    assert dashboard["worker"]["latest_run"]["status"] == "success"
