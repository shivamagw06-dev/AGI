"""E08 P0 — E08-001–005 Volatility & Options Intelligence."""

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
from app.engines.e08.consumer import register_e08_with_orch
from app.engines.e08.flags import E08Flags
from app.engines.e08.mapping import FORMULA_ID
from app.engines.e08.service import E08Service
from app.engines.e14.service import E14Service
from app.features.service import FeatureRegistryService
from app.main import app
from app.orch.l2.executor import L2FeatureBuildService
from app.orch.l2.models import FeatureReadyEvent
from app.orch.ledger import OrchLedger
from app.validation.flags import ValidationFlags
from app.validation.service import ValidationService

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "e08"
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


def test_golden_volatility_states():
    registry = FeatureRegistryService()
    e08 = E08Service(registry, flags=E08Flags())
    g = _golden()
    out = e08.run_universe(
        as_of=g["as_of"],
        panels=g["panels"],
        e01_state=_mini_e01(g["as_of"]),
        e14_state=_mini_e14(g["as_of"]),
        universe_id=g["universe_id"],
    )
    assert set(out) == {"TCS", "RELIANCE", "LOWVOL", "HIGHVOL"}
    assert out["HIGHVOL"].composite_score > out["LOWVOL"].composite_score
    assert out["LOWVOL"].compression is True or out["LOWVOL"].vol_regime == "compression"
    assert out["HIGHVOL"].expansion is True or out["HIGHVOL"].vol_regime in {"expansion", "extreme"}
    assert out["TCS"].formula_id == FORMULA_ID
    assert out["TCS"].expected_move is not None
    assert out["TCS"].realized_vol > 0
    assert out["TCS"].historical_vol > 0


def test_determinism_replay():
    registry = FeatureRegistryService()
    e08 = E08Service(registry)
    g = _golden()
    a = e08.run_universe(as_of=g["as_of"], panels=g["panels"], generated_at=FIXED)
    b = e08.run_universe(as_of=g["as_of"], panels=g["panels"], generated_at=FIXED)
    assert a["TCS"].composite_score == b["TCS"].composite_score
    assert a["TCS"].hash == b["TCS"].hash
    sa = e08.get_state("TCS")
    sb = e08.store.get_state("TCS")
    assert sa is not None and sb is not None
    assert sa.hash == sb.hash
    assert sa.input_hash == sb.input_hash


def test_engine_state_schema_and_conf():
    registry = FeatureRegistryService()
    e08 = E08Service(registry)
    g = _golden()
    e08.run_universe(
        as_of=g["as_of"],
        panels=g["panels"],
        e01_state=_mini_e01(g["as_of"]),
        e14_state=_mini_e14(g["as_of"]),
        generated_at=FIXED,
    )
    state = e08.get_state("TCS")
    assert state is not None
    payload = state.model_dump(mode="json")
    assert payload["engine"] == "E08"
    assert payload["confidence"]["method_version"] == "conf-1.0"
    assert validate_engine_state(payload) == []
    assert "positive" in payload["evidence"]
    assert payload["metadata"]["formula_id"] == FORMULA_ID


def test_warm_cache_under_25ms():
    registry = FeatureRegistryService()
    e08 = E08Service(registry)
    g = _golden()
    e08.run_universe(as_of=g["as_of"], panels=g["panels"])
    for _ in range(30):
        t0 = time.perf_counter()
        vol = e08.get_vol_state("TCS")
        assert vol is not None
        assert (time.perf_counter() - t0) * 1000 < 25.0
    assert e08.metrics.snapshot()["cache_hits"] >= 30


def test_flags_and_no_market_data():
    flags = E08Flags.from_settings()
    assert flags.e08_p0 is True
    assert flags.e08_gamma is False
    assert flags.e08_dealer is False
    assert flags.e08_surface is False
    assert flags.e08_ml is False
    registry = FeatureRegistryService()
    e08 = E08Service(registry)
    health = e08.health()
    assert health["market_data_access"] is False
    assert health["polling"] is False
    assert health["ml"] is False
    assert health["dealer_positioning"] is False
    assert health["options_surface"] is False
    assert health["gamma_exposure_model"] is False


def test_placeholder_flags_raise():
    registry = FeatureRegistryService()
    e08 = E08Service(registry, flags=E08Flags(e08_p0=True, e08_ml=True))
    g = _golden()
    with pytest.raises(RuntimeError, match="E08_ML"):
        e08.run_universe(as_of=g["as_of"], panels=g["panels"])


def test_vol_registry_features():
    registry = FeatureRegistryService()
    bars = [{"high": 110 + i, "low": 100 + i, "close": 105 + i * 0.2} for i in range(80)]
    for fid in ("VOL_REALIZED_20", "VOL_HIST_60", "VOL_ATR_14"):
        fv = registry.compute(fid, symbol="TCS", as_of="2026-07-24", ctx={"bars": bars})
        assert fv is not None
        assert fv.value is not None


def test_orch_passive_consumer():
    registry = FeatureRegistryService()
    ledger = OrchLedger()
    l2 = L2FeatureBuildService(registry, orch_ledger=ledger)
    e01 = E01Service(registry, orch_ledger=ledger)
    e14 = E14Service(registry, e01=e01, orch_ledger=ledger)
    e08 = E08Service(registry, e01=e01, e14=e14, orch_ledger=ledger)
    g = _golden()
    e08.run_universe(as_of=g["as_of"], panels=g["panels"])
    register_e08_with_orch(l2, e08, e01, e14)
    ready = FeatureReadyEvent(
        batch_id="b-e08",
        as_of=g["as_of"],
        symbol="TCS",
        feature_ids=["VOL_REALIZED_20", "VOL_HIST_60"],
        succeeded=["VOL_REALIZED_20"],
    )
    for handler in l2._ready_handlers:
        handler(ready)
    assert e08.get_vol_state("TCS") is not None
    e01.store.put(_mini_e01(g["as_of"]))
    e08.on_e01_ready(_mini_e01(g["as_of"]))
    e08.on_e14_ready(_mini_e14(g["as_of"]))
    state = e08.get_state("TCS")
    assert state is not None
    assert state.metadata["e08_state"]["e01_ref"]["primary_regime"] == "expansion_risk_on"


def test_history_multi_day():
    registry = FeatureRegistryService()
    e08 = E08Service(registry)
    g = _golden()
    e08.run_universe(as_of="2026-07-23", panels=g["panels"])
    e08.run_universe(as_of="2026-07-24", panels=g["panels"])
    hist = e08.history("TCS", limit=10)
    assert len(hist) == 2
    assert hist[0].as_of >= hist[1].as_of


def test_no_market_data_imports():
    root = Path(__file__).resolve().parents[1] / "app" / "engines" / "e08"
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
    assert "E08" in result.run.engine_versions
    assert "VM_AGI_VOL" in result.run.formula_versions
    assert result.days[0].e08_hashes
    assert result.days[0].e08_scores

    cre = CREService(flags=CREFlags(cre=True, promotion=False))
    eval_result = cre.evaluate("golden_p0_v1", generated_at=FIXED)
    engines = {c.engine for c in eval_result.engine_scorecards}
    assert "E08" in engines
    assert eval_result.promotion is not None
    assert eval_result.promotion.ready is False
    card = next(c for c in eval_result.engine_scorecards if c.engine == "E08")
    assert "volatility_intelligence" in card.notes


@pytest.mark.asyncio
async def test_e08_api():
    from app.api import routes as api_routes

    registry = FeatureRegistryService()
    api_routes._e08 = E08Service(registry)
    g = _golden()
    api_routes._e08.run_universe(as_of=g["as_of"], panels=g["panels"], generated_at=FIXED)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/e08/health")
        assert health.status_code == 200
        body = health.json()
        assert body["engine"] == "E08"
        assert body["flags"]["E08_P0"] is True
        assert body["flags"]["E08_ML"] is False

        state = await client.get("/v1/e08/state/TCS")
        assert state.status_code == 200
        assert state.json()["symbol"] == "TCS"
        assert "composite_score" in state.json()

        hist = await client.get("/v1/e08/history/TCS")
        assert hist.status_code == 200
        assert len(hist.json()) >= 1
