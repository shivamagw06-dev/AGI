"""E01 P0 — E01-001–005 threshold vertical slice."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.contracts.engine_state import validate_engine_state
from app.engines.e01.consumer import register_e01_with_orch_l2
from app.engines.e01.flags import E01Flags
from app.engines.e01.service import E01Service, snapshot_from_macro_dict
from app.features.service import FeatureRegistryService
from app.main import app
from app.orch.l2.executor import L2FeatureBuildService
from app.orch.l2.models import FeatureReadyEvent
from app.orch.ledger import OrchLedger

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "e01"


def _load_fixture(name: str) -> tuple[str, dict[str, float]]:
    payload = json.loads((FIXTURES / name).read_text(encoding="utf-8"))
    return payload["as_of"], payload["features"]


def test_covid_fixture_crisis_or_crisis_vol():
    registry = FeatureRegistryService()
    e01 = E01Service(registry, flags=E01Flags(e01_p0=True, e01_hmm=False, e01_ml=False))
    as_of, feats = _load_fixture("covid_2020_03.json")
    state = e01.run(as_of=as_of, snapshot=snapshot_from_macro_dict(as_of, feats))
    primary = state.metadata["primary_regime"]
    axes = state.metadata["axes"]
    assert primary in {"crisis", "crisis_vol"} or axes["R_STRESS"]["state"] == "crisis"
    assert axes["R_VOL"]["state"] in {"crisis_vol", "high_vol"}
    assert axes["R_STRESS"]["confidence"] >= 0.6 or axes["R_VOL"]["confidence"] >= 0.6
    assert validate_engine_state(state.model_dump(mode="json")) == []


def test_risk_on_expansion_size_multiplier():
    registry = FeatureRegistryService()
    e01 = E01Service(registry)
    as_of, feats = _load_fixture("risk_on_expansion.json")
    state = e01.run(as_of=as_of, snapshot=snapshot_from_macro_dict(as_of, feats))
    assert state.metadata["axes"]["R_RISK"]["state"] == "risk_on"
    assert state.metadata["axes"]["R_CYCLE"]["state"] == "expansion"
    assert state.metadata["primary_regime"] == "expansion_risk_on"
    assert state.metadata["size_multiplier"] >= 1.0
    assert state.score.normalized_0_100 is not None
    assert state.score.normalized_0_100 >= 50


def test_state_determinism_replay():
    registry = FeatureRegistryService()
    e01 = E01Service(registry)
    as_of, feats = _load_fixture("risk_on_expansion.json")
    snap = snapshot_from_macro_dict(as_of, feats)
    from datetime import datetime, timezone

    fixed = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
    a = e01.run(as_of=as_of, snapshot=snap, generated_at=fixed)
    b = e01.run(as_of=as_of, snapshot=snap, generated_at=fixed)
    assert a.input_hash == b.input_hash
    assert a.hash == b.hash
    assert a.metadata["primary_regime"] == b.metadata["primary_regime"]
    assert a.score.raw == b.score.raw
    assert a.confidence.method_version == "conf-1.0"


def test_schema_and_contract_validation():
    registry = FeatureRegistryService()
    e01 = E01Service(registry)
    as_of, feats = _load_fixture("risk_on_expansion.json")
    state = e01.run(as_of=as_of, snapshot=snapshot_from_macro_dict(as_of, feats))
    payload = state.model_dump(mode="json")
    assert payload["engine"] == "E01"
    assert payload["confidence"]["method_version"] == "conf-1.0"
    assert validate_engine_state(payload) == []
    assert payload["input_hash"].startswith("sha256:")
    assert len(payload["metadata"]["axes"]) == 9


def test_stale_inputs_reduce_confidence():
    registry = FeatureRegistryService()
    e01 = E01Service(registry)
    as_of = "2026-07-24"
    # Minimal sparse snapshot → many missing/stale
    sparse = snapshot_from_macro_dict(as_of, {"yc_slope_us": 0.1})
    state = e01.run(as_of=as_of, snapshot=sparse)
    assert state.stale_inputs
    assert state.metadata.get("degraded") is True
    assert "degraded_stale_inputs" in state.warnings
    assert state.confidence.value < 0.7


def test_cache_warm_lookup_under_25ms():
    registry = FeatureRegistryService()
    e01 = E01Service(registry)
    as_of, feats = _load_fixture("risk_on_expansion.json")
    e01.run(as_of=as_of, snapshot=snapshot_from_macro_dict(as_of, feats))
    for _ in range(30):
        t0 = time.perf_counter()
        state = e01.get_state()
        assert state is not None
        assert (time.perf_counter() - t0) * 1000 < 25.0
    assert e01.metrics.snapshot()["cache_hits"] >= 30


def test_feature_registry_mapping_no_provider_access():
    registry = FeatureRegistryService()
    as_of, feats = _load_fixture("risk_on_expansion.json")
    # Materialize mapped registry feature at the same PIT as_of
    registry.compute(
        "MACRO_YIELD_CURVE_10Y2Y",
        symbol=None,
        as_of=as_of,
        ctx={"macro": {"US10Y": 4.2, "US2Y": 3.8}},
    )
    e01 = E01Service(registry)
    # Remove yc_slope from snapshot — must come from registry mapping
    feats = dict(feats)
    feats.pop("yc_slope_us", None)
    state = e01.run(as_of=as_of, snapshot=snapshot_from_macro_dict(as_of, feats))
    assert "yc_slope_us" in state.metadata["feature_sources"]
    assert state.metadata["feature_sources"]["yc_slope_us"] == "MACRO_YIELD_CURVE_10Y2Y"


def test_orch_integration_passive_consumer():
    registry = FeatureRegistryService()
    ledger = OrchLedger()
    l2 = L2FeatureBuildService(registry, orch_ledger=ledger)
    e01 = E01Service(registry, orch_ledger=ledger)
    as_of, feats = _load_fixture("risk_on_expansion.json")
    snap = snapshot_from_macro_dict(as_of, feats)

    def provider(ready: FeatureReadyEvent):
        return snap

    register_e01_with_orch_l2(l2, e01, snapshot_provider=provider)
    # Emit ready directly (simulates L2 completion)
    ready = FeatureReadyEvent(
        batch_id="batch-1",
        as_of=as_of,
        feature_ids=["MACRO_YIELD_CURVE_10Y2Y", "VOL_REALIZED_20"],
        succeeded=["MACRO_YIELD_CURVE_10Y2Y"],
        snapshot_id=snap.snapshot_id,
    )
    for handler in l2._ready_handlers:
        handler(ready)
    state = e01.get_state()
    assert state is not None
    assert state.engine == "E01"
    assert state.metadata["primary_regime"] == "expansion_risk_on"
    # ORCH ledger recorded E01_MACRO node
    summary = ledger.status_summary()
    assert summary["runs_tracked"] >= 1


def test_hmm_ml_flags_default_off():
    flags = E01Flags.from_settings()
    assert flags.e01_p0 is True
    assert flags.e01_hmm is False
    assert flags.e01_ml is False


def test_history_persistence():
    registry = FeatureRegistryService()
    e01 = E01Service(registry)
    as_of, feats = _load_fixture("risk_on_expansion.json")
    e01.run(as_of="2026-07-23", snapshot=snapshot_from_macro_dict("2026-07-23", feats))
    e01.run(as_of="2026-07-24", snapshot=snapshot_from_macro_dict("2026-07-24", feats))
    hist = e01.history(limit=10)
    assert len(hist) == 2
    assert hist[0].as_of >= hist[1].as_of


@pytest.mark.asyncio
async def test_e01_api_health_state_history():
    # Seed via service singleton used by app routes — run through internal import
    from app.api import routes as api_routes

    as_of, feats = _load_fixture("risk_on_expansion.json")
    api_routes._e01.run(as_of=as_of, snapshot=snapshot_from_macro_dict(as_of, feats))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/e01/health")
        assert health.status_code == 200
        body = health.json()
        assert body["engine"] == "E01"
        assert body["flags"]["E01_P0"] is True
        assert body["flags"]["E01_HMM"] is False
        assert body["market_data_access"] is False
        assert body["polling"] is False

        state = await client.get("/v1/e01/state")
        assert state.status_code == 200
        payload = state.json()
        assert payload["engine"] == "E01"
        assert validate_engine_state(payload) == []

        hist = await client.get("/v1/e01/history", params={"limit": 5})
        assert hist.status_code == 200
        assert len(hist.json()) >= 1
