"""E14 P0 — E14-001–005 rule-based risk overlay."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.contracts.engine_state import EngineState, empty_evidence_pack, validate_engine_state
from app.engines.e01.service import E01Service
from app.engines.e14.consumer import register_e14_with_orch
from app.engines.e14.flags import E14Flags
from app.engines.e14.service import E14Service, snapshot_from_risk_dict
from app.features.service import FeatureRegistryService
from app.main import app
from app.orch.l2.executor import L2FeatureBuildService
from app.orch.l2.models import FeatureReadyEvent
from app.orch.ledger import OrchLedger

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "e14"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def _e01_from_fixture(payload: dict) -> EngineState:
    e01 = payload["e01"]
    as_of = payload["as_of"]
    macro = float(e01.get("macro_score", 50))
    body = {
        "engine": "E01",
        "version": "1.0.0",
        "model_version": "e01-p0-axes-0.1.0",
        "as_of": as_of,
        "universe_id": "GLOBAL_MACRO",
        "symbol": None,
        "score": {
            "raw": macro,
            "normalized_0_100": macro,
            "normalized_signed": max(-1.0, min(1.0, (macro - 50) / 50)),
            "unit": "score",
        },
        "confidence": {
            "value": 0.7,
            "components": {"C_coverage": 0.8, "C_freshness": 0.8, "C_stability": 0.7},
            "method_version": "conf-1.0",
        },
        "reliability": {"sample_size": 10, "historical_accuracy": None, "stability": 0.7},
        "metadata": {
            "primary_regime": e01["primary_regime"],
            "macro_score": macro,
            "axes": e01["axes"],
            "risk_level": e01["risk_level"],
            "size_multiplier": e01["size_multiplier"],
            "vol_target": e01["vol_target"],
        },
        "evidence": empty_evidence_pack(),
        "explanation": {"summary": "fixture e01", "top_drivers": [], "falsifiers": []},
        "warnings": [],
        "stale_inputs": [],
        "input_hash": "sha256:" + ("a" * 64),
        "hash": "sha256:" + ("b" * 64),
        "timestamp_generated": datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc).isoformat(),
    }
    return EngineState.model_validate(body)


def test_covid_fixture_hard_derisk_or_high_score():
    registry = FeatureRegistryService()
    e14 = E14Service(registry, flags=E14Flags(e14_p0=True, e14_ml=False, e14_bayes=False))
    payload = _load("covid_2020_03_book.json")
    state = e14.run(
        as_of=payload["as_of"],
        snapshot=snapshot_from_risk_dict(payload["as_of"], payload["features"]),
        e01_state=_e01_from_fixture(payload),
    )
    assert state.metadata["playbook"] == "hard_derisk" or state.metadata["risk_score"] >= 85
    assert state.metadata["size_multiplier"] <= 0.40
    assert state.metadata["gate"] in {"research_hedge_only", "block_promotion"}
    assert validate_engine_state(state.model_dump(mode="json")) == []


def test_calm_book_allow_path():
    registry = FeatureRegistryService()
    e14 = E14Service(registry)
    payload = _load("calm_book.json")
    state = e14.run(
        as_of=payload["as_of"],
        snapshot=snapshot_from_risk_dict(payload["as_of"], payload["features"]),
        e01_state=_e01_from_fixture(payload),
    )
    assert state.metadata["risk_score"] < 60
    assert state.metadata["playbook"] == "normal"
    assert state.metadata["gate"] in {"allow", "allow_with_haircut"}
    assert state.metadata["size_multiplier"] >= 0.75


def test_determinism_replay():
    registry = FeatureRegistryService()
    e14 = E14Service(registry)
    payload = _load("calm_book.json")
    snap = snapshot_from_risk_dict(payload["as_of"], payload["features"])
    e01 = _e01_from_fixture(payload)
    fixed = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
    a = e14.run(as_of=payload["as_of"], snapshot=snap, e01_state=e01, generated_at=fixed)
    b = e14.run(as_of=payload["as_of"], snapshot=snap, e01_state=e01, generated_at=fixed)
    assert a.input_hash == b.input_hash
    assert a.hash == b.hash
    assert a.metadata["risk_score"] == b.metadata["risk_score"]
    assert a.confidence.method_version == "conf-1.0"


def test_schema_contract_validation():
    registry = FeatureRegistryService()
    e14 = E14Service(registry)
    payload = _load("covid_2020_03_book.json")
    state = e14.run(
        as_of=payload["as_of"],
        snapshot=snapshot_from_risk_dict(payload["as_of"], payload["features"]),
        e01_state=_e01_from_fixture(payload),
    )
    payload_json = state.model_dump(mode="json")
    assert payload_json["engine"] == "E14"
    assert validate_engine_state(payload_json) == []
    assert len(payload_json["metadata"]["taxonomy_scores"]) == 18


def test_missing_e01_fail_closed():
    registry = FeatureRegistryService()
    e14 = E14Service(registry)
    as_of = "2026-07-24"
    state = e14.run(
        as_of=as_of,
        snapshot=snapshot_from_risk_dict(as_of, {"crowding_index": 40, "liquidity_index": 70}),
        e01_state=None,
    )
    assert state.metadata["degraded"] is True
    assert state.metadata["confidence_adjustment"] <= 0.70
    assert "e01_missing_fail_closed" in state.warnings
    assessment = e14.assess(
        target_type="signal",
        target_id="E12_cand_1",
        as_of=as_of,
        e01_state=None,
    )
    assert assessment.gate != "allow"


def test_e12_high_risk_blocks_promotion():
    registry = FeatureRegistryService()
    e14 = E14Service(registry)
    payload = _load("covid_2020_03_book.json")
    e14.run(
        as_of=payload["as_of"],
        snapshot=snapshot_from_risk_dict(payload["as_of"], payload["features"]),
        e01_state=_e01_from_fixture(payload),
    )
    assessment = e14.assess(
        target_type="signal",
        target_id="E12_cand_covid",
        as_of=payload["as_of"],
        e01_state=_e01_from_fixture(payload),
        snapshot=snapshot_from_risk_dict(payload["as_of"], payload["features"]),
    )
    assert assessment.risk_score >= 75 or assessment.gate in {"block_promotion", "research_hedge_only"}
    if assessment.risk_score >= 75:
        assert assessment.gate in {"block_promotion", "research_hedge_only"}


def test_liquidity_name_assessment():
    registry = FeatureRegistryService()
    e14 = E14Service(registry)
    payload = _load("calm_book.json")
    e14.run(
        as_of=payload["as_of"],
        snapshot=snapshot_from_risk_dict(payload["as_of"], payload["features"]),
        e01_state=_e01_from_fixture(payload),
    )
    assessment = e14.assess(
        target_type="signal",
        target_id="ILLIQUID_1",
        as_of=payload["as_of"],
        e01_state=_e01_from_fixture(payload),
        target_features={"pct_adv_proposed": 2.5},
    )
    assert assessment.liquidity_score < 40
    assert assessment.max_allocation < 0.08
    assert any(f["taxonomy_id"] == "RK_LIQUIDITY" for f in assessment.risk_flags)


def test_cache_warm_under_25ms():
    registry = FeatureRegistryService()
    e14 = E14Service(registry)
    payload = _load("calm_book.json")
    e14.run(
        as_of=payload["as_of"],
        snapshot=snapshot_from_risk_dict(payload["as_of"], payload["features"]),
        e01_state=_e01_from_fixture(payload),
    )
    for _ in range(30):
        t0 = time.perf_counter()
        state = e14.get_state()
        assert state is not None
        assert (time.perf_counter() - t0) * 1000 < 25.0
    assert e14.metrics.snapshot()["cache_hits"] >= 30


def test_orch_integration_feature_and_e01():
    registry = FeatureRegistryService()
    ledger = OrchLedger()
    l2 = L2FeatureBuildService(registry, orch_ledger=ledger)
    e01 = E01Service(registry, orch_ledger=ledger)
    e14 = E14Service(registry, e01=e01, orch_ledger=ledger)
    payload = _load("calm_book.json")
    # Seed E01 cache
    e01.store.put(_e01_from_fixture(payload))
    snap = snapshot_from_risk_dict(payload["as_of"], payload["features"])

    register_e14_with_orch(l2, e14, e01, snapshot_provider=lambda r: snap)
    ready = FeatureReadyEvent(
        batch_id="b1",
        as_of=payload["as_of"],
        feature_ids=["MACRO_YIELD_CURVE_10Y2Y", "VOL_REALIZED_20"],
        succeeded=["MACRO_YIELD_CURVE_10Y2Y"],
        snapshot_id=snap.snapshot_id,
    )
    for handler in l2._ready_handlers:
        handler(ready)
    state = e14.get_state()
    assert state is not None
    assert state.engine == "E14"
    assert state.metadata["e01_ref"]["primary_regime"] == "expansion_risk_on"
    assert ledger.status_summary()["runs_tracked"] >= 1


def test_flags_default():
    flags = E14Flags.from_settings()
    assert flags.e14_p0 is True
    assert flags.e14_ml is False
    assert flags.e14_bayes is False


def test_history():
    registry = FeatureRegistryService()
    e14 = E14Service(registry)
    payload = _load("calm_book.json")
    e01 = _e01_from_fixture(payload)
    feats = payload["features"]
    e14.run(as_of="2024-06-14", snapshot=snapshot_from_risk_dict("2024-06-14", feats), e01_state=e01)
    e14.run(as_of="2024-06-15", snapshot=snapshot_from_risk_dict("2024-06-15", feats), e01_state=e01)
    assert len(e14.history()) == 2


@pytest.mark.asyncio
async def test_e14_api():
    from app.api import routes as api_routes

    payload = _load("calm_book.json")
    api_routes._e14.run(
        as_of=payload["as_of"],
        snapshot=snapshot_from_risk_dict(payload["as_of"], payload["features"]),
        e01_state=_e01_from_fixture(payload),
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/e14/health")
        assert health.status_code == 200
        body = health.json()
        assert body["engine"] == "E14"
        assert body["flags"]["E14_P0"] is True
        assert body["flags"]["E14_ML"] is False
        assert body["market_data_access"] is False
        state = await client.get("/v1/e14/state")
        assert state.status_code == 200
        assert validate_engine_state(state.json()) == []
        hist = await client.get("/v1/e14/history")
        assert hist.status_code == 200
        assert len(hist.json()) >= 1
