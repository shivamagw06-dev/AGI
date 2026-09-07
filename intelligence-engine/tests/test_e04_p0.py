"""E04 P0 — E04-001–005 Statistical Arbitrage & Relative Value."""

from __future__ import annotations

import ast
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.contracts.engine_state import EngineState, empty_evidence_pack, validate_engine_state
from app.cre.flags import CREFlags
from app.cre.service import CREService
from app.engines.e01.service import E01Service
from app.engines.e02.service import E02Service
from app.engines.e03.service import E03Service
from app.engines.e04.consumer import register_e04_with_orch
from app.engines.e04.flags import E04Flags
from app.engines.e04.mapping import FORMULA_ID
from app.engines.e04.models.stats import engle_granger, half_life, ols_hedge, spread_series
from app.engines.e04.service import E04Service
from app.engines.e14.service import E14Service
from app.features.service import FeatureRegistryService
from app.main import app
from app.orch.l2.executor import L2FeatureBuildService
from app.orch.l2.models import FeatureReadyEvent
from app.orch.ledger import OrchLedger
from app.validation.flags import ValidationFlags
from app.validation.service import ValidationService

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "e04"
FIXED = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)


def _golden() -> dict:
    return json.loads((FIXTURES / "golden_pairs.json").read_text(encoding="utf-8"))


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


def test_ols_and_half_life_and_eg():
    # Perfectly cointegrated: y = 2 + 0.5 x
    x = [float(i) for i in range(40, 100)]
    y = [2.0 + 0.5 * v for v in x]
    ols = ols_hedge(y, x)
    assert abs(ols.beta - 0.5) < 1e-6
    assert abs(ols.alpha - 2.0) < 1e-6
    spr = spread_series(y, x, ols.alpha, ols.beta)
    assert max(abs(v) for v in spr) < 1e-8
    # AR(1) mean-reverting spread: S_t = 0.7 S_{t-1} + eps (phi in (0,1))
    s = [1.5]
    for i in range(1, 80):
        eps = 0.02 * ((i % 5) - 2) / 2.0
        s.append(0.7 * s[-1] + eps)
    hl = half_life(s)
    assert hl.valid is True
    assert hl.half_life is not None
    # true HL = -ln(2)/ln(0.7) ≈ 1.94
    assert 1.0 < hl.half_life < 5.0
    # Near-zero residuals are strongly mean-reverting → EG cointegrated
    eg = engle_granger(list(ols.residuals) if ols.residuals else spr)
    assert eg.cointegrated is True
    assert eg.adf_stat < eg.critical_value


def test_golden_pair_states():
    registry = FeatureRegistryService()
    e04 = E04Service(registry, flags=E04Flags())
    g = _golden()
    static = [tuple(p) for p in g["static_pairs"]]
    e04.set_static_pairs(static)
    out = e04.run_universe(
        as_of=g["as_of"],
        panels=g["panels"],
        static_pairs=static,
        e01_state=_mini_e01(g["as_of"]),
        e14_state=_mini_e14(g["as_of"]),
        universe_id=g["universe_id"],
    )
    assert "INFY_TCS" in out  # canonical sorted
    assert "HDFCBANK_SBIN" in out
    tcs_infy = out["INFY_TCS"]
    assert tcs_infy.formula_id == FORMULA_ID
    assert math.isfinite(tcs_infy.z_score)
    assert math.isfinite(tcs_infy.hedge_beta)
    assert tcs_infy.label in {"Rich", "Cheap", "Fair", "Mildly Rich", "Mildly Cheap", "Non-Cointegrated"}
    assert tcs_infy.side in {"long_spread", "short_spread", "flat"}
    assert 0.0 <= tcs_infy.composite_score <= 100.0


def test_determinism_replay():
    registry = FeatureRegistryService()
    e04 = E04Service(registry)
    g = _golden()
    static = [tuple(p) for p in g["static_pairs"]]
    a = e04.run_universe(
        as_of=g["as_of"], panels=g["panels"], static_pairs=static, generated_at=FIXED
    )
    b = e04.run_universe(
        as_of=g["as_of"], panels=g["panels"], static_pairs=static, generated_at=FIXED
    )
    assert a["INFY_TCS"].z_score == b["INFY_TCS"].z_score
    assert a["INFY_TCS"].hash == b["INFY_TCS"].hash
    sa = e04.get_state("INFY_TCS")
    sb = e04.store.get_state("INFY_TCS")
    assert sa is not None and sb is not None
    assert sa.hash == sb.hash


def test_engine_state_schema_and_conf():
    registry = FeatureRegistryService()
    e04 = E04Service(registry)
    g = _golden()
    static = [tuple(p) for p in g["static_pairs"]]
    e04.run_universe(
        as_of=g["as_of"],
        panels=g["panels"],
        static_pairs=static,
        e01_state=_mini_e01(g["as_of"]),
        e14_state=_mini_e14(g["as_of"]),
        generated_at=FIXED,
    )
    state = e04.get_state("INFY_TCS")
    assert state is not None
    payload = state.model_dump(mode="json")
    assert payload["engine"] == "E04"
    assert payload["symbol"] == "INFY_TCS"
    assert payload["confidence"]["method_version"] == "conf-1.0"
    assert validate_engine_state(payload) == []
    assert payload["metadata"]["formula_id"] == FORMULA_ID


def test_warm_cache_under_25ms():
    registry = FeatureRegistryService()
    e04 = E04Service(registry)
    g = _golden()
    static = [tuple(p) for p in g["static_pairs"]]
    e04.run_universe(as_of=g["as_of"], panels=g["panels"], static_pairs=static)
    for _ in range(30):
        t0 = time.perf_counter()
        rv = e04.get_rv_state("INFY_TCS")
        assert rv is not None
        assert (time.perf_counter() - t0) * 1000 < 25.0
    assert e04.metrics.snapshot()["cache_hits"] >= 30


def test_flags_and_no_market_data():
    flags = E04Flags.from_settings()
    assert flags.e04_p0 is True
    assert flags.e04_kalman is False
    assert flags.e04_dynamic_hedge is False
    assert flags.e04_etf_basis is False
    assert flags.e04_ml is False
    registry = FeatureRegistryService()
    e04 = E04Service(registry)
    health = e04.health()
    assert health["market_data_access"] is False
    assert health["kalman"] is False
    assert health["portfolio_construction"] is False
    assert health["execution"] is False


def test_placeholder_flags_raise():
    registry = FeatureRegistryService()
    e04 = E04Service(registry, flags=E04Flags(e04_p0=True, e04_ml=True))
    g = _golden()
    with pytest.raises(RuntimeError, match="E04_ML"):
        e04.run_universe(as_of=g["as_of"], panels=g["panels"], static_pairs=[("TCS", "INFY")])


def test_sector_peer_discovery():
    registry = FeatureRegistryService()
    e04 = E04Service(registry)
    g = _golden()
    out = e04.run_universe(as_of=g["as_of"], panels=g["panels"])
    # Sector peers should create IT and BANK pairs even without static list
    assert any(pid.endswith("TCS") or pid.startswith("INFY") for pid in out)
    assert "HDFCBANK_SBIN" in out or "INFY_TCS" in out


def test_orch_passive_consumer():
    registry = FeatureRegistryService()
    ledger = OrchLedger()
    l2 = L2FeatureBuildService(registry, orch_ledger=ledger)
    e01 = E01Service(registry, orch_ledger=ledger)
    e14 = E14Service(registry, e01=e01, orch_ledger=ledger)
    e02 = E02Service(registry, e01=e01, e14=e14, orch_ledger=ledger)
    e03 = E03Service(registry, e01=e01, e14=e14, e02=e02, orch_ledger=ledger)
    e04 = E04Service(registry, e01=e01, e14=e14, e02=e02, e03=e03, orch_ledger=ledger)
    g = _golden()
    static = [tuple(p) for p in g["static_pairs"]]
    e04.set_static_pairs(static)
    e04.run_universe(as_of=g["as_of"], panels=g["panels"], static_pairs=static)
    register_e04_with_orch(l2, e04, e01, e14, e02, e03)
    ready = FeatureReadyEvent(
        batch_id="b-e04",
        as_of=g["as_of"],
        symbol="TCS",
        feature_ids=["RVAL_SPREAD"],
        succeeded=["RVAL_SPREAD"],
    )
    for handler in l2._ready_handlers:
        handler(ready)
    assert e04.get_rv_state("INFY_TCS") is not None
    e01.store.put(_mini_e01(g["as_of"]))
    e04.on_e01_ready(_mini_e01(g["as_of"]))
    e04.on_e14_ready(_mini_e14(g["as_of"]))
    state = e04.get_state("INFY_TCS")
    assert state is not None
    assert state.metadata["e04_state"]["e01_ref"]["primary_regime"] == "expansion_risk_on"


def test_history_multi_day():
    registry = FeatureRegistryService()
    e04 = E04Service(registry)
    g = _golden()
    static = [tuple(p) for p in g["static_pairs"]]
    e04.run_universe(as_of="2026-07-23", panels=g["panels"], static_pairs=static)
    e04.run_universe(as_of="2026-07-24", panels=g["panels"], static_pairs=static)
    hist = e04.history("INFY_TCS", limit=10)
    assert len(hist) == 2


def test_no_market_data_imports():
    root = Path(__file__).resolve().parents[1] / "app" / "engines" / "e04"
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
    assert "E04" in result.run.engine_versions
    assert "RV_AGI_PAIR" in result.run.formula_versions
    assert result.days[0].e04_hashes
    assert result.days[0].e04_scores

    cre = CREService(flags=CREFlags(cre=True, promotion=False))
    eval_result = cre.evaluate("golden_p0_v1", generated_at=FIXED)
    engines = {c.engine for c in eval_result.engine_scorecards}
    assert "E04" in engines
    assert eval_result.promotion is not None
    assert eval_result.promotion.ready is False
    card = next(c for c in eval_result.engine_scorecards if c.engine == "E04")
    assert "stat_arb_relative_value" in card.notes


@pytest.mark.asyncio
async def test_e04_api():
    from app.api import routes as api_routes

    registry = FeatureRegistryService()
    api_routes._e04 = E04Service(registry)
    g = _golden()
    static = [tuple(p) for p in g["static_pairs"]]
    api_routes._e04.run_universe(
        as_of=g["as_of"], panels=g["panels"], static_pairs=static, generated_at=FIXED
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/e04/health")
        assert health.status_code == 200
        body = health.json()
        assert body["engine"] == "E04"
        assert body["flags"]["E04_P0"] is True
        assert body["flags"]["E04_ML"] is False

        state = await client.get("/v1/e04/state/INFY_TCS")
        assert state.status_code == 200
        assert state.json()["pair_id"] == "INFY_TCS"
        assert "z_score" in state.json()

        hist = await client.get("/v1/e04/history/INFY_TCS")
        assert hist.status_code == 200
        assert len(hist.json()) >= 1
