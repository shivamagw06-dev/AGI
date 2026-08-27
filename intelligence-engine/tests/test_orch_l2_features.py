"""ORCH-003–005 — Layer 2 Feature Build orchestration."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.features.graph import DependencyCycleError
from app.features.models import FeatureMetadata, FeatureValue
from app.features.service import FeatureRegistryService
from app.main import app
from app.orch.l2.executor import L2FeatureBuildService
from app.orch.l2.models import MarketDataUpdateEvent
from app.orch.l2.queue import FeatureBuildQueue


def _bars(n: int = 60, start: float = 100.0) -> list[dict]:
    bars = []
    price = start
    for i in range(n):
        price += 0.5 if i % 3 else -0.2
        bars.append(
            {
                "ts": f"2026-05-{(i % 28) + 1:02d}",
                "open": price - 0.1,
                "high": price + 1.0,
                "low": price - 1.0,
                "close": price,
                "volume": 1000 + i,
            }
        )
    return bars


def test_dirty_ohlcv_marks_tech_not_fund():
    features = FeatureRegistryService()
    l2 = L2FeatureBuildService(features)
    event = MarketDataUpdateEvent(update_type="ohlcv", symbol="RELIANCE", as_of="2026-07-24")
    seeds = l2.dirty.seeds_for_update(event)
    assert "TECH_EMA_12" in seeds
    assert "TECH_MACD" in seeds or "TECH_RSI_14" in seeds
    assert "FUND_ROE" not in seeds


def test_dependency_propagation_partial_recompute():
    features = FeatureRegistryService()
    l2 = L2FeatureBuildService(features)
    ctx = {"bars": _bars(80)}
    # Warm EMA_26 so incremental path can reuse it
    features.compute("TECH_EMA_26", symbol="INFY", as_of="2026-07-24", ctx=ctx)

    compute_calls: list[str] = []
    original = features.recompute_impacted

    def _wrap(feature_ids, **kwargs):
        compute_calls.extend(sorted(feature_ids))
        return original(feature_ids, **kwargs)

    features.recompute_impacted = _wrap  # type: ignore[method-assign]

    l2.enqueue_manual(
        as_of="2026-07-24",
        symbol="INFY",
        feature_ids=["TECH_EMA_12"],
        ctx=ctx,
    )
    result = l2.drain(parallel=False)
    assert result is not None
    assert "TECH_EMA_12" in result.impacted
    assert "TECH_MACD" in result.impacted
    assert "TECH_RSI_14" not in result.impacted
    assert "TECH_EMA_26" not in result.impacted
    assert "TECH_EMA_12" in result.ready.succeeded
    assert "TECH_MACD" in result.ready.succeeded


def test_duplicate_suppression():
    q = FeatureBuildQueue()
    a = q.enqueue(as_of="2026-07-24", symbol="TCS", feature_ids=["TECH_EMA_12"])
    b = q.enqueue(as_of="2026-07-24", symbol="TCS", feature_ids=["TECH_EMA_12", "TECH_MACD"])
    assert a.job_id == b.job_id
    assert q.size() == 1
    assert q.stats()["suppressed"] == 1
    assert "TECH_MACD" in b.feature_ids


def test_cycle_rejection_in_l2_graph():
    features = FeatureRegistryService(register_builtins=False)
    features.graph.set_dependencies("A", ["B"])
    with pytest.raises(DependencyCycleError):
        features.graph.set_dependencies("B", ["A"])


def test_failure_recovery_and_retry():
    features = FeatureRegistryService(register_builtins=False)

    class _Flaky:
        def __init__(self) -> None:
            self.calls = 0
            self.metadata = FeatureMetadata(
                feature_id="TECH_FLAKY",
                category="TECH_",
                description="flaky",
                owner="test",
                formula_version="1.0.0",
                refresh_frequency="1d",
                source="test",
                inputs=["ohlcv.close"],
            )

        def compute(self, *, symbol, as_of, available_at, ctx, dep_values):
            self.calls += 1
            if self.calls < 3:
                raise RuntimeError("transient")
            return FeatureValue(
                feature_id="TECH_FLAKY",
                formula_version="1.0.0",
                symbol=symbol,
                as_of=as_of,
                available_at=available_at,
                value=1.0,
                source="test",
            )

    flaky = _Flaky()
    features.register_calculator(flaky)
    l2 = L2FeatureBuildService(features, max_attempts=3, feature_timeout_s=2.0)
    l2.enqueue_manual(as_of="2026-07-24", symbol="X", feature_ids=["TECH_FLAKY"], ctx={})
    result = l2.drain(parallel=False)
    assert result is not None
    assert result.status == "succeeded"
    assert flaky.calls == 3
    assert l2.metrics.snapshot()["retries"] >= 2
    build = result.builds[0]
    assert build.status == "succeeded"
    assert build.attempt == 3
    assert build.build_id
    assert build.formula_version == "1.0.0"
    assert build.input_snapshot


def test_failure_isolation_skips_dependents():
    features = FeatureRegistryService(register_builtins=False)

    class _Boom:
        metadata = FeatureMetadata(
            feature_id="TECH_BOOM",
            category="TECH_",
            description="boom",
            owner="test",
            formula_version="1.0.0",
            refresh_frequency="1d",
            source="test",
            inputs=["ohlcv.close"],
        )

        def compute(self, *, symbol, as_of, available_at, ctx, dep_values):
            raise RuntimeError("permanent")

    class _Child:
        metadata = FeatureMetadata(
            feature_id="TECH_CHILD",
            category="TECH_",
            description="child",
            owner="test",
            formula_version="1.0.0",
            dependencies=["TECH_BOOM"],
            refresh_frequency="1d",
            source="test",
            inputs=["ohlcv.close"],
        )

        def compute(self, *, symbol, as_of, available_at, ctx, dep_values):
            return FeatureValue(
                feature_id="TECH_CHILD",
                formula_version="1.0.0",
                symbol=symbol,
                as_of=as_of,
                available_at=available_at,
                value=2.0,
                source="test",
            )

    features.register_calculator(_Boom())
    features.register_calculator(_Child())
    l2 = L2FeatureBuildService(features, max_attempts=1)
    l2.enqueue_manual(
        as_of="2026-07-24",
        symbol="Y",
        feature_ids=["TECH_BOOM"],
        ctx={},
    )
    result = l2.drain(parallel=False)
    assert result is not None
    assert "TECH_BOOM" in result.ready.failed
    assert "TECH_CHILD" in result.ready.skipped


def test_parallel_execution_wave():
    features = FeatureRegistryService()
    l2 = L2FeatureBuildService(features)
    ready_events = []
    l2.on_ready(ready_events.append)
    l2.enqueue_manual(
        as_of="2026-07-24",
        symbol="REL",
        feature_ids=["TECH_EMA_12", "TECH_EMA_26", "TECH_RSI_14"],
        ctx={"bars": _bars(80)},
    )
    result = l2.drain(parallel=True, max_workers=3)
    assert result is not None
    assert result.status == "succeeded"
    assert len(ready_events) == 1
    assert set(result.ready.succeeded) >= {"TECH_EMA_12", "TECH_EMA_26", "TECH_RSI_14"}


def test_market_data_update_triggers_dirty_queue():
    features = FeatureRegistryService()
    l2 = L2FeatureBuildService(features)
    event = MarketDataUpdateEvent(update_type="ohlcv", symbol="AAA", as_of="2026-07-24")
    result = l2.on_market_data_update(
        event,
        ctx={"bars": _bars(80)},
        drain=True,
        parallel=True,
    )
    assert result is not None
    assert result.impacted
    assert "TECH_" in "".join(result.impacted)
    assert l2.build_ledger.stats()["builds"] >= 1


@pytest.mark.asyncio
async def test_orch_l2_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/orch/l2/health")
        assert health.status_code == 200
        assert health.json()["node_id"] == "L2_FEATURES"
        denied = await client.post("/v1/orch/l2/trigger", json={"as_of": "2026-07-24"})
        assert denied.status_code == 401
        resp = await client.post(
            "/v1/orch/l2/trigger",
            headers={"Authorization": "Bearer dev-intelligence-token"},
            json={
                "as_of": "2026-07-24",
                "symbol": "TCS",
                "feature_ids": ["TECH_EMA_20"],
                "ctx": {"bars": _bars(40)},
                "parallel": False,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["ok"] is True
        assert "TECH_EMA_20" in body["impacted"]
        assert body["builds"]
        assert body["builds"][0]["feature_id"] == "TECH_EMA_20"
