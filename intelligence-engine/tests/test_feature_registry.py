"""WS03 Feature Registry tests — WBS FEAT-001–005."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.features.calculators.tech_math import ema, rsi_wilder
from app.features.graph import DependencyCycleError, FeatureDependencyGraph
from app.features.models import FeatureMetadata, FeatureValue
from app.features.service import FeatureRegistryService
from app.main import app


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


def test_builtin_features_registered():
    svc = FeatureRegistryService()
    ids = {m.feature_id for m in svc.list_features()}
    for required in (
        "TECH_EMA_20",
        "TECH_MACD",
        "TECH_RSI_14",
        "TECH_ADX_14",
        "MACRO_YIELD_CURVE_10Y2Y",
        "FUND_ROE",
        "UNIV_MEMBER_NIFTY500",
        "VOL_REALIZED_20",
        "OPTIONS_IV_RANK",
        "SENT_NEWS",
        "EVENT_EPS_SURPRISE",
        "RVAL_HALF_LIFE",
    ):
        assert required in ids


def test_external_category_stubs_have_no_calculator():
    svc = FeatureRegistryService()
    assert "OPTIONS_IV_RANK" not in svc._calculators
    assert "RVAL_SPREAD" not in svc._calculators
    order = svc.dependency_order(["RVAL_HALF_LIFE"])
    assert order.index("RVAL_SPREAD") < order.index("RVAL_HALF_LIFE")


def test_macd_depends_on_emas():
    svc = FeatureRegistryService()
    order = svc.dependency_order(["TECH_MACD"])
    assert order.index("TECH_EMA_12") < order.index("TECH_MACD")
    assert order.index("TECH_EMA_26") < order.index("TECH_MACD")


def test_dependency_cycle_rejected():
    g = FeatureDependencyGraph()
    g.set_dependencies("A", ["B"])
    with pytest.raises(DependencyCycleError):
        g.set_dependencies("B", ["A"])


def test_tech_features_deterministic_replay():
    svc = FeatureRegistryService()
    ctx = {"bars": _bars(80)}
    a = svc.compute("TECH_RSI_14", symbol="RELIANCE", as_of="2026-07-24", ctx=ctx)
    b = svc.compute("TECH_RSI_14", symbol="RELIANCE", as_of="2026-07-24", ctx=ctx)
    assert a.value == b.value
    assert a.formula_version == "1.0.0"
    assert a.quality_flag == "ok"
    # Cross-check helper
    closes = [float(x["close"]) for x in ctx["bars"]]
    expected = next(x for x in reversed(rsi_wilder(closes, 14)) if x is not None)
    assert a.value == pytest.approx(expected)


def test_ema_math_seed():
    values = [float(i) for i in range(1, 31)]
    series = ema(values, 12)
    assert series[11] == pytest.approx(sum(values[:12]) / 12)


def test_cache_lookup_under_10ms():
    svc = FeatureRegistryService(cache_ttl_s=120)
    ctx = {"bars": _bars(80)}
    svc.compute("TECH_EMA_20", symbol="TCS", as_of="2026-07-24", ctx=ctx)
    # warm lookups
    for _ in range(20):
        v = svc.get("TECH_EMA_20", symbol="TCS", as_of="2026-07-24")
        assert v is not None
    p95 = svc.metrics.snapshot()["lookup_p95_ms"]
    assert p95 is not None
    assert p95 < 10.0


def test_pit_rejects_future_available_at():
    svc = FeatureRegistryService(register_builtins=False)
    svc.register_metadata(
        FeatureMetadata(
            feature_id="X_TEST",
            category="TECH_",
            description="test",
            owner="test",
            formula_version="1.0.0",
            refresh_frequency="1d",
            source="test",
        )
    )
    future = FeatureValue(
        feature_id="X_TEST",
        formula_version="1.0.0",
        symbol="AAA",
        as_of="2026-07-01",
        available_at=datetime(2026, 7, 10, tzinfo=timezone.utc),
        value=1.0,
        source="test",
    )
    svc.store.put_value(future)
    assert svc.get("X_TEST", symbol="AAA", as_of="2026-07-01", pit_mode=True) is None
    assert svc.get("X_TEST", symbol="AAA", as_of="2026-07-01", pit_mode=False) is not None


def test_dependency_invalidation():
    svc = FeatureRegistryService()
    ctx = {"bars": _bars(80)}
    svc.compute("TECH_MACD", symbol="INFY", as_of="2026-07-24", ctx=ctx)
    assert svc.cache.stats()["size"] >= 1
    removed = svc.invalidate("TECH_EMA_12")
    assert removed["feature"] + removed["dependents"] >= 1


def test_universe_membership_feature():
    svc = FeatureRegistryService()
    ctx = {"universe_membership": {"NIFTY500": ["RELIANCE", "TCS"]}}
    yes = svc.compute("UNIV_MEMBER_NIFTY500", symbol="RELIANCE", as_of="2026-07-24", ctx=ctx)
    no = svc.compute("UNIV_MEMBER_NIFTY500", symbol="ZZZZ", as_of="2026-07-24", ctx=ctx)
    assert yes.value == 1
    assert no.value == 0


def test_macro_and_fund_features():
    svc = FeatureRegistryService()
    macro = svc.compute(
        "MACRO_YIELD_CURVE_10Y2Y",
        symbol=None,
        as_of="2026-07-24",
        ctx={"macro": {"US10Y": 4.2, "US2Y": 3.8}},
    )
    assert macro.value == pytest.approx(0.4)
    fund = svc.compute(
        "FUND_ROE",
        symbol="RELIANCE",
        as_of="2026-07-24",
        ctx={"fundamentals": {"roe": 0.18, "roic": 0.12, "pegRatio": 1.1}},
    )
    assert fund.value == pytest.approx(0.18)
    assert fund.feature_id == "FUND_ROE"


def test_version_is_on_values():
    svc = FeatureRegistryService()
    v = svc.compute("TECH_EMA_12", symbol="X", as_of="2026-07-24", ctx={"bars": _bars(40)})
    assert v.formula_version == "1.0.0"
    meta = svc.get_metadata("TECH_EMA_12")
    assert meta is not None
    assert meta.formula_version == v.formula_version


def test_history_series():
    svc = FeatureRegistryService()
    ctx = {"bars": _bars(40)}
    svc.compute("TECH_ROC_10", symbol="Y", as_of="2026-07-23", ctx=ctx)
    svc.compute("TECH_ROC_10", symbol="Y", as_of="2026-07-24", ctx=ctx)
    hist = svc.history("TECH_ROC_10", symbol="Y")
    assert len(hist.points) == 2


def test_adx_compute():
    svc = FeatureRegistryService()
    v = svc.compute("TECH_ADX_14", symbol="RELIANCE", as_of="2026-07-24", ctx={"bars": _bars(80)})
    assert v.quality_flag == "ok"
    assert v.value is not None
    assert 0 <= float(v.value) <= 100


def test_calculation_scheduler_topo_and_incremental():
    svc = FeatureRegistryService()
    plan = svc.scheduler.plan(
        as_of="2026-07-24",
        feature_ids=["TECH_MACD"],
        symbols=["RELIANCE"],
    )
    assert plan.feature_ids.index("TECH_EMA_12") < plan.feature_ids.index("TECH_MACD")
    assert len(plan.feature_ids) == len(set(plan.feature_ids))

    ctx = {"bars": _bars(80)}
    result = svc.scheduler.run(plan, ctx=ctx)
    assert result.plans_executed == 1
    assert "TECH_MACD" in result.snapshots[0].values

    # Second run is incremental via cache (no duplicate calc work)
    before_hits = svc.cache.hits
    result2 = svc.scheduler.run(plan, ctx=ctx)
    assert result2.snapshots[0].values["TECH_MACD"].value == result.snapshots[0].values["TECH_MACD"].value
    assert svc.cache.hits > before_hits

    freqs = svc.scheduler.frequencies()
    assert "1d" in freqs
    assert "TECH_EMA_20" in freqs["1d"]


def test_scheduler_invalidation_seed():
    svc = FeatureRegistryService()
    ctx = {"bars": _bars(80)}
    plan = svc.scheduler.plan(as_of="2026-07-24", feature_ids=["TECH_MACD"], symbols=["TCS"])
    svc.scheduler.run(plan, ctx=ctx)
    result = svc.scheduler.run(plan, ctx=ctx, invalidate_seeds=["TECH_EMA_12"])
    assert result.invalidated["TECH_EMA_12"] >= 1


def test_formula_version_change_isolates_cache():
    svc = FeatureRegistryService(register_builtins=False)

    class _Const:
        def __init__(self, version: str, value: float) -> None:
            self.metadata = FeatureMetadata(
                feature_id="TECH_CONST",
                category="TECH_",
                description="const",
                owner="test",
                formula_version=version,
                refresh_frequency="1d",
                source="test",
            )
            self._value = value

        def compute(self, *, symbol, as_of, available_at, ctx, dep_values):
            return FeatureValue(
                feature_id="TECH_CONST",
                formula_version=self.metadata.formula_version,
                symbol=symbol,
                as_of=as_of,
                available_at=available_at,
                value=self._value,
                source="test",
            )

    svc.register_calculator(_Const("1.0.0", 1.0))
    a = svc.compute("TECH_CONST", symbol="Z", as_of="2026-07-24", ctx={})
    assert a.value == 1.0
    svc.register_calculator(_Const("1.0.1", 2.0))
    b = svc.compute("TECH_CONST", symbol="Z", as_of="2026-07-24", ctx={})
    assert b.value == 2.0
    assert b.formula_version == "1.0.1"
    hist = svc.history("TECH_CONST", symbol="Z")
    versions = {p.formula_version for p in hist.points}
    assert versions == {"1.0.0", "1.0.1"}


@pytest.mark.asyncio
async def test_features_api_health_and_list():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/features/health")
        assert health.status_code == 200
        assert health.json()["feature_count"] > 0
        denied = await client.get("/v1/features")
        assert denied.status_code == 401
        listed = await client.get(
            "/v1/features",
            headers={"Authorization": "Bearer dev-intelligence-token"},
        )
        assert listed.status_code == 200
        ids = {row["feature_id"] for row in listed.json()}
        assert "TECH_MACD" in ids
        order = await client.get(
            "/v1/features/dependency-order",
            params={"feature_id": "TECH_MACD"},
            headers={"Authorization": "Bearer dev-intelligence-token"},
        )
        assert order.status_code == 200
        assert "TECH_EMA_12" in order.json()["order"]
        sched = await client.get(
            "/v1/features/schedule/plan",
            params={"as_of": "2026-07-24", "feature_id": "TECH_MACD"},
            headers={"Authorization": "Bearer dev-intelligence-token"},
        )
        assert sched.status_code == 200
        assert "TECH_EMA_12" in sched.json()["feature_ids"]
