"""Validation & Backtesting P0 — BT-001–005."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.validation.flags import ValidationFlags
from app.validation.golden.loader import load_golden_dataset
from app.validation.service import ValidationService


FIXED = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)


def test_golden_dataset_loader():
    ds = load_golden_dataset("golden_p0_v1")
    assert ds.dataset_id == "golden_p0_v1"
    assert len(ds.days) == 5
    assert len(ds.symbols) == 5
    assert ds.days[0].as_of < ds.days[-1].as_of
    assert "TCS" in ds.days[0].e03_panels
    assert "TCS" in ds.days[0].forward_returns


def test_replay_deterministic_and_metrics():
    svc = ValidationService(flags=ValidationFlags(backtest=True, live=False))
    result = svc.run_replay("golden_p0_v1", generated_at=FIXED)
    assert result.run.status == "succeeded"
    assert result.run.production_influence is False
    assert result.run.live is False
    assert result.run.flags["BACKTEST"] is True
    assert result.run.flags["LIVE"] is False
    assert len(result.days) == 5
    assert result.summary is not None
    assert result.summary.deterministic is True
    assert result.summary.parity_stability >= 0.99
    assert result.summary.passed is True
    assert "E01" in result.run.engine_versions
    assert "E10" in result.run.engine_versions
    assert "SM_AGI_TECH" in result.run.formula_versions
    perf = result.summary.performance
    assert len(perf.daily_returns) == 5
    assert len(perf.benchmark_returns) == 5
    assert perf.turnover is not None
    assert perf.average_confidence is not None
    assert result.summary.calibration.n_observations >= 0
    # Weights + cash sanity on each day
    for day in result.days:
        assert abs(sum(day.portfolio_weights.values()) + day.cash_allocation - 1.0) < 1e-3
        assert day.portfolio_hash
        assert day.e01_hash and day.e14_hash


def test_replay_bit_stable_hashes():
    svc = ValidationService()
    a = svc.run_replay("golden_p0_v1", generated_at=FIXED)
    b = svc.run_replay("golden_p0_v1", generated_at=FIXED)
    assert [d.portfolio_hash for d in a.days] == [d.portfolio_hash for d in b.days]
    assert [d.e01_hash for d in a.days] == [d.e01_hash for d in b.days]
    assert [d.l4_hashes for d in a.days] == [d.l4_hashes for d in b.days]


def test_dashboard_sections():
    svc = ValidationService()
    result = svc.run_replay("golden_p0_v1", generated_at=FIXED)
    dash = result.dashboard
    assert "timeline" in dash
    assert "portfolio_history" in dash
    assert "signal_history" in dash
    assert "l4_vs_e03" in dash
    assert "confidence_distribution" in dash
    assert "risk_distribution" in dash
    assert len(dash["timeline"]) == 5


def test_live_flag_rejected():
    svc = ValidationService(flags=ValidationFlags(backtest=True, live=True))
    with pytest.raises(RuntimeError, match="LIVE"):
        svc.run_replay("golden_p0_v1")


def test_backtest_disabled():
    svc = ValidationService(flags=ValidationFlags(backtest=False, live=False))
    with pytest.raises(RuntimeError, match="BACKTEST"):
        svc.run_replay("golden_p0_v1")


def test_no_market_data_imports():
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app" / "validation"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [a.name for a in node.names]
            else:
                continue
            joined = " ".join(n or "" for n in names)
            assert "market_data" not in joined
            assert "MarketDataClient" not in joined


@pytest.mark.asyncio
async def test_validation_api():
    from app.api import routes as api_routes

    # Use isolated service on routes for clean state
    api_routes._validation = ValidationService()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/validation/health")
        assert health.status_code == 200
        body = health.json()
        assert body["flags"]["BACKTEST"] is True
        assert body["flags"]["LIVE"] is False
        assert body["production_influence"] is False
        assert body["market_data_access"] is False

        datasets = await client.get("/v1/validation/datasets")
        assert datasets.status_code == 200
        assert datasets.json()[0]["dataset_id"] == "golden_p0_v1"

        replay = await client.post("/v1/validation/replay", params={"dataset_id": "golden_p0_v1"})
        assert replay.status_code == 200
        payload = replay.json()
        run_id = payload["run"]["run_id"]
        assert payload["summary"]["deterministic"] is True

        runs = await client.get("/v1/validation/runs")
        assert runs.status_code == 200
        assert any(r["run_id"] == run_id for r in runs.json())

        one = await client.get(f"/v1/validation/runs/{run_id}")
        assert one.status_code == 200
        assert one.json()["run"]["run_id"] == run_id

        dash = await client.get(f"/v1/validation/dashboard/{run_id}")
        assert dash.status_code == 200
        assert "l4_vs_e03" in dash.json()
