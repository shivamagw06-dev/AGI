"""E02 P0 — E02-001–005 Factor & Style Engine."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.contracts.engine_state import EngineState, empty_evidence_pack, validate_engine_state
from app.engines.e01.service import E01Service
from app.engines.e02.consumer import register_e02_with_orch
from app.engines.e02.flags import E02Flags
from app.engines.e02.mapping import P0_FACTORS
from app.engines.e02.models.normalise import winsorise, zscore
from app.engines.e02.service import E02Service
from app.engines.e14.service import E14Service
from app.features.service import FeatureRegistryService
from app.main import app
from app.orch.l2.executor import L2FeatureBuildService
from app.orch.l2.models import FeatureReadyEvent
from app.orch.ledger import OrchLedger

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "e02"


def _golden() -> dict:
    return json.loads((FIXTURES / "golden_universe.json").read_text(encoding="utf-8"))


def _mini_e01(as_of: str) -> EngineState:
    return EngineState.model_validate(
        {
            "engine": "E01",
            "version": "1.0.0",
            "model_version": "e01-p0-axes-0.1.0",
            "as_of": as_of,
            "score": {"raw": 60.0, "normalized_0_100": 60.0, "normalized_signed": 0.2, "unit": "score"},
            "confidence": {
                "value": 0.7,
                "components": {"C_coverage": 0.8, "C_freshness": 0.8, "C_stability": 0.7},
                "method_version": "conf-1.0",
            },
            "metadata": {"primary_regime": "expansion_risk_on", "risk_level": "low", "size_multiplier": 1.0},
            "evidence": empty_evidence_pack(),
            "explanation": {"summary": "fixture"},
            "warnings": [],
            "stale_inputs": [],
            "input_hash": "sha256:" + ("a" * 64),
            "hash": "sha256:" + ("b" * 64),
            "timestamp_generated": datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc).isoformat(),
        }
    )


def _mini_e14(as_of: str) -> EngineState:
    return EngineState.model_validate(
        {
            "engine": "E14",
            "version": "1.0.0",
            "model_version": "e14-p0-rules-0.1.0",
            "as_of": as_of,
            "score": {"raw": 40.0, "normalized_0_100": 40.0, "normalized_signed": 0.2, "unit": "score"},
            "confidence": {
                "value": 0.7,
                "components": {"C_coverage": 0.7, "C_freshness": 0.8, "C_model": 0.7},
                "method_version": "conf-1.0",
            },
            "metadata": {
                "playbook": "normal",
                "risk_level": "moderate",
                "confidence_adjustment": 0.95,
                "size_multiplier": 0.9,
            },
            "evidence": empty_evidence_pack(),
            "explanation": {"summary": "fixture"},
            "warnings": [],
            "stale_inputs": [],
            "input_hash": "sha256:" + ("c" * 64),
            "hash": "sha256:" + ("d" * 64),
            "timestamp_generated": datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc).isoformat(),
        }
    )


def test_winsorise_and_z_deterministic():
    vals = [1.0, 2.0, 3.0, 4.0, 100.0]
    w = winsorise(vals)
    assert max(w) < 100.0
    z = zscore(w)
    assert abs(sum(z)) < 1e-9


def test_golden_universe_factor_calculations():
    registry = FeatureRegistryService()
    e02 = E02Service(registry, flags=E02Flags())
    g = _golden()
    out = e02.run_universe(
        as_of=g["as_of"],
        panels=g["panels"],
        e01_state=_mini_e01(g["as_of"]),
        e14_state=_mini_e14(g["as_of"]),
        universe_id=g["universe_id"],
    )
    assert set(out) == {"TCS", "RELIANCE", "SMALLCAP1", "VALUECO"}
    tcs = out["TCS"]
    for f in P0_FACTORS:
        assert f in tcs.scores
        assert f in tcs.loadings
        assert -3.0 <= tcs.loadings[f] <= 3.0
        assert 0.0 <= tcs.scores[f] <= 100.0
    # Small cap should rank higher on F_SIZE than TCS (large)
    assert out["SMALLCAP1"].scores["F_SIZE"] > out["TCS"].scores["F_SIZE"]
    # VALUECO should score higher on F_VALUE than TCS
    assert out["VALUECO"].scores["F_VALUE"] > out["TCS"].scores["F_VALUE"]
    # Intermediate FACTOR_* features present
    assert "FACTOR_MOMENTUM" in tcs.factor_features


def test_sector_relative_quality():
    registry = FeatureRegistryService()
    e02 = E02Service(registry)
    g = _golden()
    out = e02.run_universe(as_of=g["as_of"], panels=g["panels"])
    # Both IT names get quality scores; TCS fundamentals stronger → higher quality than SMALLCAP1
    assert out["TCS"].scores["F_QUALITY"] > out["SMALLCAP1"].scores["F_QUALITY"]


def test_determinism_replay():
    registry = FeatureRegistryService()
    e02 = E02Service(registry)
    g = _golden()
    fixed = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
    a = e02.run_universe(as_of=g["as_of"], panels=g["panels"], generated_at=fixed)
    b = e02.run_universe(as_of=g["as_of"], panels=g["panels"], generated_at=fixed)
    assert a["TCS"].scores == b["TCS"].scores
    assert a["TCS"].loadings == b["TCS"].loadings
    sa = e02.get_state("TCS")
    sb = e02.store.get_state("TCS")
    assert sa is not None and sb is not None
    assert sa.hash == sb.hash
    assert sa.input_hash == sb.input_hash


def test_engine_state_schema_and_conf():
    registry = FeatureRegistryService()
    e02 = E02Service(registry)
    g = _golden()
    e02.run_universe(
        as_of=g["as_of"],
        panels=g["panels"],
        e01_state=_mini_e01(g["as_of"]),
        e14_state=_mini_e14(g["as_of"]),
    )
    state = e02.get_state("TCS")
    assert state is not None
    payload = state.model_dump(mode="json")
    assert payload["engine"] == "E02"
    assert payload["confidence"]["method_version"] == "conf-1.0"
    assert validate_engine_state(payload) == []
    assert "positive" in payload["evidence"]
    assert payload["symbol"] == "TCS"


def test_warm_cache_under_25ms():
    registry = FeatureRegistryService()
    e02 = E02Service(registry)
    g = _golden()
    e02.run_universe(as_of=g["as_of"], panels=g["panels"])
    for _ in range(30):
        t0 = time.perf_counter()
        exp = e02.get_exposure("TCS")
        assert exp is not None
        assert (time.perf_counter() - t0) * 1000 < 25.0
    assert e02.metrics.snapshot()["cache_hits"] >= 30


def test_no_market_data_access_flags():
    flags = E02Flags.from_settings()
    assert flags.e02_p0 is True
    assert flags.e02_timing is False
    assert flags.e02_rotation is False
    assert flags.e02_smart_beta is False
    assert flags.e02_ml is False
    registry = FeatureRegistryService()
    e02 = E02Service(registry)
    assert e02.health()["market_data_access"] is False
    assert e02.health()["polling"] is False


def test_feature_registry_fund_mapping():
    registry = FeatureRegistryService()
    registry.compute(
        "FUND_ROE",
        symbol="TCS",
        as_of="2026-07-24",
        ctx={"fundamentals": {"roe": 0.42, "roic": 0.3}},
    )
    e02 = E02Service(registry)
    # Minimal 2-name universe so z/percentile defined; ROE for TCS from registry
    panels = {
        "TCS": {"sector_id": "IT", "ret_12_1": 0.1, "ret_6_1": 0.05, "ret_3_0": 0.02, "log_mcap": 29.0, "adv_value_20d": 1e9, "amihud_60d": 0.0001, "float_share": 0.7, "beta": 0.9, "sigma_60": 0.2, "ep_ttm": 0.04, "bp": 0.2, "ev_ebitda_inv": 0.07, "fcf_yield": 0.03, "sp": 0.3},
        "PEER": {"sector_id": "IT", "ret_12_1": 0.0, "ret_6_1": 0.0, "ret_3_0": 0.0, "log_mcap": 28.0, "adv_value_20d": 5e8, "amihud_60d": 0.0002, "float_share": 0.5, "beta": 1.1, "sigma_60": 0.3, "roe": 0.10, "roic": 0.08, "gross_margin": 0.2, "oper_margin": 0.1, "accruals": 0.05, "leverage": 0.5, "earn_stability": 0.4, "ep_ttm": 0.03, "bp": 0.3, "ev_ebitda_inv": 0.05, "fcf_yield": 0.02, "sp": 0.4},
    }
    out = e02.run_universe(as_of="2026-07-24", panels=panels)
    assert "F_QUALITY" in out["TCS"].scores


def test_orch_integration():
    registry = FeatureRegistryService()
    ledger = OrchLedger()
    l2 = L2FeatureBuildService(registry, orch_ledger=ledger)
    e01 = E01Service(registry, orch_ledger=ledger)
    e14 = E14Service(registry, e01=e01, orch_ledger=ledger)
    e02 = E02Service(registry, e01=e01, e14=e14, orch_ledger=ledger)
    g = _golden()
    # Seed panels via universe run once
    e02.run_universe(as_of=g["as_of"], panels=g["panels"])
    register_e02_with_orch(l2, e02, e01, e14)
    ready = FeatureReadyEvent(
        batch_id="b1",
        as_of=g["as_of"],
        symbol="TCS",
        feature_ids=["FUND_ROE", "VOL_REALIZED_20"],
        succeeded=["FUND_ROE"],
    )
    for handler in l2._ready_handlers:
        handler(ready)
    assert e02.get_exposure("TCS") is not None
    # E01 ready path
    e01.store.put(_mini_e01(g["as_of"]))
    e02.on_e01_ready(_mini_e01(g["as_of"]))
    e02.on_e14_ready(_mini_e14(g["as_of"]))
    state = e02.get_state("TCS")
    assert state is not None
    assert state.metadata["e02_exposure"]["e01_ref"]["primary_regime"] == "expansion_risk_on"


def test_history():
    registry = FeatureRegistryService()
    e02 = E02Service(registry)
    g = _golden()
    e02.run_universe(as_of="2026-07-23", panels=g["panels"])
    e02.run_universe(as_of="2026-07-24", panels=g["panels"])
    hist = e02.history("TCS")
    assert len(hist) == 2


@pytest.mark.asyncio
async def test_e02_api():
    from app.api import routes as api_routes

    g = _golden()
    api_routes._e02.run_universe(as_of=g["as_of"], panels=g["panels"])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/e02/health")
        assert health.status_code == 200
        body = health.json()
        assert body["engine"] == "E02"
        assert body["flags"]["E02_P0"] is True
        assert body["flags"]["E02_ML"] is False
        assert body["market_data_access"] is False
        exp = await client.get("/v1/e02/exposure/TCS")
        assert exp.status_code == 200
        payload = exp.json()
        assert payload["engine"] == "E02"
        assert "F_MOMENTUM" in payload["scores"]
        hist = await client.get("/v1/e02/history/TCS")
        assert hist.status_code == 200
        assert len(hist.json()) >= 1
        assert validate_engine_state(hist.json()[0]) == []
