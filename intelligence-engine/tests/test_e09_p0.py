"""E09 P0 — E09-001–005 CTA Trend Engine."""

from __future__ import annotations

import ast
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.contracts.engine_state import EngineState, empty_evidence_pack, validate_engine_state
from app.cre.flags import CREFlags
from app.cre.service import CREService
from app.engines.e01.service import E01Service
from app.engines.e09.consumer import register_e09_with_orch
from app.engines.e09.flags import E09Flags
from app.engines.e09.mapping import FORMULA_ID
from app.engines.e09.service import E09Service
from app.engines.e14.service import E14Service
from app.features.service import FeatureRegistryService
from app.main import app
from app.orch.l2.executor import L2FeatureBuildService
from app.orch.l2.models import FeatureReadyEvent
from app.orch.ledger import OrchLedger
from app.validation.flags import ValidationFlags
from app.validation.service import ValidationService

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "e09"
FIXED = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)


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
            "timestamp_generated": FIXED.isoformat(),
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
            "timestamp_generated": FIXED.isoformat(),
        }
    )


def test_golden_cta_trend_states():
    registry = FeatureRegistryService()
    e09 = E09Service(registry, flags=E09Flags())
    g = _golden()
    out = e09.run_universe(
        as_of=g["as_of"],
        panels=g["panels"],
        e01_state=_mini_e01(g["as_of"]),
        e14_state=_mini_e14(g["as_of"]),
        universe_id=g["universe_id"],
    )
    assert set(out) == {"TCS", "RELIANCE", "TRENDLONG", "TRENDSHORT"}
    assert out["TRENDLONG"].composite_score > out["TRENDSHORT"].composite_score
    assert out["TRENDLONG"].ts_momentum > out["TRENDSHORT"].ts_momentum
    assert out["TRENDLONG"].side == "long"
    assert out["TRENDSHORT"].side == "short"
    assert out["TCS"].formula_id == FORMULA_ID
    assert out["TCS"].persistence >= 0.0
    assert out["TCS"].exhaustion >= 0.0
    assert "vol_scaled_signal" in out["TCS"].metrics


def test_determinism_replay():
    registry = FeatureRegistryService()
    e09 = E09Service(registry)
    g = _golden()
    a = e09.run_universe(as_of=g["as_of"], panels=g["panels"], generated_at=FIXED)
    b = e09.run_universe(as_of=g["as_of"], panels=g["panels"], generated_at=FIXED)
    assert a["TCS"].composite_score == b["TCS"].composite_score
    assert a["TCS"].hash == b["TCS"].hash
    sa = e09.get_state("TCS")
    sb = e09.store.get_state("TCS")
    assert sa is not None and sb is not None
    assert sa.hash == sb.hash
    assert sa.input_hash == sb.input_hash


def test_engine_state_schema_and_conf():
    registry = FeatureRegistryService()
    e09 = E09Service(registry)
    g = _golden()
    e09.run_universe(
        as_of=g["as_of"],
        panels=g["panels"],
        e01_state=_mini_e01(g["as_of"]),
        e14_state=_mini_e14(g["as_of"]),
        generated_at=FIXED,
    )
    state = e09.get_state("TCS")
    assert state is not None
    payload = state.model_dump(mode="json")
    assert payload["engine"] == "E09"
    assert payload["confidence"]["method_version"] == "conf-1.0"
    assert validate_engine_state(payload) == []
    assert "positive" in payload["evidence"]
    assert payload["metadata"]["formula_id"] == FORMULA_ID


def test_warm_cache_under_25ms():
    registry = FeatureRegistryService()
    e09 = E09Service(registry)
    g = _golden()
    e09.run_universe(as_of=g["as_of"], panels=g["panels"])
    for _ in range(30):
        t0 = time.perf_counter()
        trend = e09.get_trend_state("TCS")
        assert trend is not None
        assert (time.perf_counter() - t0) * 1000 < 25.0
    assert e09.metrics.snapshot()["cache_hits"] >= 30


def test_flags_and_no_market_data():
    flags = E09Flags.from_settings()
    assert flags.e09_p0 is True
    assert flags.e09_breakout is False
    assert flags.e09_cross_asset is False
    assert flags.e09_ml is False
    registry = FeatureRegistryService()
    e09 = E09Service(registry)
    health = e09.health()
    assert health["market_data_access"] is False
    assert health["polling"] is False
    assert health["ml"] is False
    assert health["adaptive_optimisation"] is False
    assert health["portfolio_logic"] is False
    assert health["cross_asset_execution"] is False


def test_placeholder_flags_raise():
    registry = FeatureRegistryService()
    e09 = E09Service(registry, flags=E09Flags(e09_p0=True, e09_ml=True))
    g = _golden()
    with pytest.raises(RuntimeError, match="E09_ML"):
        e09.run_universe(as_of=g["as_of"], panels=g["panels"])


def test_tech_vol_registry_features():
    registry = FeatureRegistryService()
    bars = [{"high": 110 + i, "low": 100 + i, "close": 105 + i * 0.3, "volume": 1e6} for i in range(80)]
    for fid in ("TECH_ROC_10", "TECH_EMA_12", "TECH_EMA_26", "VOL_REALIZED_20"):
        fv = registry.compute(fid, symbol="TCS", as_of="2026-07-24", ctx={"bars": bars})
        assert fv is not None
        assert fv.value is not None


def test_orch_passive_consumer():
    registry = FeatureRegistryService()
    ledger = OrchLedger()
    l2 = L2FeatureBuildService(registry, orch_ledger=ledger)
    e01 = E01Service(registry, orch_ledger=ledger)
    e14 = E14Service(registry, e01=e01, orch_ledger=ledger)
    e09 = E09Service(registry, e01=e01, e14=e14, orch_ledger=ledger)
    g = _golden()
    e09.run_universe(as_of=g["as_of"], panels=g["panels"])
    register_e09_with_orch(l2, e09, e01, e14)
    ready = FeatureReadyEvent(
        batch_id="b-e09",
        as_of=g["as_of"],
        symbol="TCS",
        feature_ids=["TECH_ROC_10", "VOL_REALIZED_20"],
        succeeded=["TECH_ROC_10"],
    )
    for handler in l2._ready_handlers:
        handler(ready)
    assert e09.get_trend_state("TCS") is not None
    e01.store.put(_mini_e01(g["as_of"]))
    e09.on_e01_ready(_mini_e01(g["as_of"]))
    e09.on_e14_ready(_mini_e14(g["as_of"]))
    state = e09.get_state("TCS")
    assert state is not None
    assert state.metadata["e09_state"]["e01_ref"]["primary_regime"] == "expansion_risk_on"


def test_history_multi_day():
    registry = FeatureRegistryService()
    e09 = E09Service(registry)
    g = _golden()
    e09.run_universe(as_of="2026-07-23", panels=g["panels"])
    e09.run_universe(as_of="2026-07-24", panels=g["panels"])
    hist = e09.history("TCS", limit=10)
    assert len(hist) == 2
    assert hist[0].as_of >= hist[1].as_of


def test_no_market_data_imports():
    root = Path(__file__).resolve().parents[1] / "app" / "engines" / "e09"
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


def test_replay_and_cre_integration():
    validation = ValidationService(flags=ValidationFlags(backtest=True, live=False))
    result = validation.run_replay("golden_p0_v1", generated_at=FIXED)
    assert result.run.status == "succeeded"
    assert "E09" in result.run.engine_versions
    assert "TM_AGI_CTA" in result.run.formula_versions
    assert result.days[0].e09_hashes
    assert result.days[0].e09_scores

    cre = CREService(flags=CREFlags(cre=True, promotion=False))
    eval_result = cre.evaluate("golden_p0_v1", generated_at=FIXED)
    engines = {c.engine for c in eval_result.engine_scorecards}
    assert "E09" in engines
    assert eval_result.promotion is not None
    assert eval_result.promotion.ready is False
    card = next(c for c in eval_result.engine_scorecards if c.engine == "E09")
    assert "cta_trend" in card.notes


@pytest.mark.asyncio
async def test_e09_api():
    from app.api import routes as api_routes

    registry = FeatureRegistryService()
    api_routes._e09 = E09Service(registry)
    g = _golden()
    api_routes._e09.run_universe(as_of=g["as_of"], panels=g["panels"], generated_at=FIXED)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/e09/health")
        assert health.status_code == 200
        body = health.json()
        assert body["engine"] == "E09"
        assert body["flags"]["E09_P0"] is True
        assert body["flags"]["E09_ML"] is False

        state = await client.get("/v1/e09/state/TCS")
        assert state.status_code == 200
        assert state.json()["symbol"] == "TCS"
        assert "composite_score" in state.json()

        hist = await client.get("/v1/e09/history/TCS")
        assert hist.status_code == 200
        assert len(hist.json()) >= 1
