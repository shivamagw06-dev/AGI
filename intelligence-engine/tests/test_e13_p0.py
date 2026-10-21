"""E13 P0 — E13-001–005 Equity Fundamental L/S Engine."""

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
from app.engines.e13.consumer import register_e13_with_orch
from app.engines.e13.flags import E13Flags
from app.engines.e13.mapping import FORMULA_ID, P0_PILLARS
from app.engines.e13.service import E13Service
from app.engines.e14.service import E14Service
from app.features.service import FeatureRegistryService
from app.main import app
from app.orch.l2.executor import L2FeatureBuildService
from app.orch.l2.models import FeatureReadyEvent
from app.orch.ledger import OrchLedger
from app.validation.flags import ValidationFlags
from app.validation.service import ValidationService

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "e13"
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


def test_golden_fundamental_scores():
    registry = FeatureRegistryService()
    e13 = E13Service(registry, flags=E13Flags())
    g = _golden()
    out = e13.run_universe(
        as_of=g["as_of"],
        panels=g["panels"],
        e01_state=_mini_e01(g["as_of"]),
        e14_state=_mini_e14(g["as_of"]),
        universe_id=g["universe_id"],
    )
    assert set(out) == {"TCS", "RELIANCE", "QUALITYCO", "VALUECO"}
    tcs = out["TCS"]
    for p in P0_PILLARS:
        assert p in tcs.pillar_scores
        assert 0.0 <= tcs.pillar_scores[p] <= 100.0
    assert out["QUALITYCO"].quality_score > out["VALUECO"].quality_score
    assert out["VALUECO"].value_score > out["QUALITYCO"].value_score
    assert tcs.formula_id == FORMULA_ID
    assert "roe" in tcs.metrics
    assert "revenue_growth" in tcs.metrics
    assert tcs.side in {"long", "short", "flat"}


def test_determinism_replay():
    registry = FeatureRegistryService()
    e13 = E13Service(registry)
    g = _golden()
    a = e13.run_universe(as_of=g["as_of"], panels=g["panels"], generated_at=FIXED)
    b = e13.run_universe(as_of=g["as_of"], panels=g["panels"], generated_at=FIXED)
    assert a["TCS"].composite_score == b["TCS"].composite_score
    assert a["TCS"].hash == b["TCS"].hash
    sa = e13.get_state("TCS")
    sb = e13.store.get_state("TCS")
    assert sa is not None and sb is not None
    assert sa.hash == sb.hash
    assert sa.input_hash == sb.input_hash


def test_engine_state_schema_and_conf():
    registry = FeatureRegistryService()
    e13 = E13Service(registry)
    g = _golden()
    e13.run_universe(
        as_of=g["as_of"],
        panels=g["panels"],
        e01_state=_mini_e01(g["as_of"]),
        e14_state=_mini_e14(g["as_of"]),
        generated_at=FIXED,
    )
    state = e13.get_state("TCS")
    assert state is not None
    payload = state.model_dump(mode="json")
    assert payload["engine"] == "E13"
    assert payload["confidence"]["method_version"] == "conf-1.0"
    assert validate_engine_state(payload) == []
    assert "positive" in payload["evidence"]
    assert payload["symbol"] == "TCS"
    assert payload["metadata"]["formula_id"] == FORMULA_ID


def test_warm_cache_under_25ms():
    registry = FeatureRegistryService()
    e13 = E13Service(registry)
    g = _golden()
    e13.run_universe(as_of=g["as_of"], panels=g["panels"])
    for _ in range(30):
        t0 = time.perf_counter()
        fund = e13.get_fundamental("TCS")
        assert fund is not None
        assert (time.perf_counter() - t0) * 1000 < 25.0
    assert e13.metrics.snapshot()["cache_hits"] >= 30


def test_flags_and_no_market_data():
    flags = E13Flags.from_settings()
    assert flags.e13_p0 is True
    assert flags.e13_revisions is False
    assert flags.e13_moat is False
    assert flags.e13_ml is False
    registry = FeatureRegistryService()
    e13 = E13Service(registry)
    health = e13.health()
    assert health["market_data_access"] is False
    assert health["polling"] is False
    assert health["ml"] is False
    assert health["analyst_nlp"] is False
    assert health["moat_classifier"] is False


def test_placeholder_flags_raise():
    registry = FeatureRegistryService()
    e13 = E13Service(registry, flags=E13Flags(e13_p0=True, e13_ml=True))
    g = _golden()
    with pytest.raises(RuntimeError, match="E13_ML"):
        e13.run_universe(as_of=g["as_of"], panels=g["panels"])


def test_feature_registry_fund_mapping():
    registry = FeatureRegistryService()
    ctx = {
        "fundamentals": {
            "roe": 0.42,
            "roic": 0.3,
            "roce": 0.28,
            "revenueGrowth": 0.12,
            "epsGrowth": 0.14,
            "debtEquity": 0.2,
            "interestCoverage": 10.0,
            "fcfYield": 0.04,
            "fcfConversion": 1.0,
            "earningsYield": 0.05,
            "bookYield": 0.2,
        }
    }
    for fid in ("FUND_ROE", "FUND_ROCE", "FUND_REVENUE_GROWTH", "FUND_FCF_YIELD"):
        fv = registry.compute(fid, symbol="TCS", as_of="2026-07-24", ctx=ctx)
        assert fv is not None
        assert fv.value is not None
        cached = registry.get(fid, symbol="TCS", as_of="2026-07-24", pit_mode=True)
        assert cached is not None
        assert cached.value == fv.value

    e13 = E13Service(registry)
    panels = {
        "TCS": {"sector_id": "IT", "gross_margin": 0.4, "oper_margin": 0.2, "leverage": 0.2, "earn_stability": 0.7},
        "PEER": {
            "sector_id": "IT",
            "roe": 0.10,
            "roic": 0.08,
            "gross_margin": 0.2,
            "oper_margin": 0.1,
            "revenue_growth": 0.03,
            "eps_growth": 0.02,
            "leverage": 0.5,
            "earn_stability": 0.4,
            "ep_ttm": 0.03,
            "bp": 0.3,
            "ev_ebitda_inv": 0.05,
            "fcf_yield": 0.02,
            "sp": 0.4,
        },
    }
    out = e13.run_universe(as_of="2026-07-24", panels=panels)
    assert out["TCS"].quality_score >= 0.0
    assert "roe" in out["TCS"].metrics


def test_orch_passive_consumer():
    registry = FeatureRegistryService()
    ledger = OrchLedger()
    l2 = L2FeatureBuildService(registry, orch_ledger=ledger)
    e01 = E01Service(registry, orch_ledger=ledger)
    e14 = E14Service(registry, e01=e01, orch_ledger=ledger)
    e13 = E13Service(registry, e01=e01, e14=e14, orch_ledger=ledger)
    g = _golden()
    e13.run_universe(as_of=g["as_of"], panels=g["panels"])
    register_e13_with_orch(l2, e13, e01, e14)
    ready = FeatureReadyEvent(
        batch_id="b-e13",
        as_of=g["as_of"],
        symbol="TCS",
        feature_ids=["FUND_ROE", "FUND_ROIC"],
        succeeded=["FUND_ROE"],
    )
    for handler in l2._ready_handlers:
        handler(ready)
    assert e13.get_fundamental("TCS") is not None
    e01.store.put(_mini_e01(g["as_of"]))
    e13.on_e01_ready(_mini_e01(g["as_of"]))
    e13.on_e14_ready(_mini_e14(g["as_of"]))
    state = e13.get_state("TCS")
    assert state is not None
    assert state.metadata["e13_fundamental"]["e01_ref"]["primary_regime"] == "expansion_risk_on"


def test_history_multi_day():
    registry = FeatureRegistryService()
    e13 = E13Service(registry)
    g = _golden()
    e13.run_universe(as_of="2026-07-23", panels=g["panels"])
    e13.run_universe(as_of="2026-07-24", panels=g["panels"])
    hist = e13.history("TCS", limit=10)
    assert len(hist) == 2
    assert hist[0].as_of >= hist[1].as_of


def test_no_market_data_imports():
    root = Path(__file__).resolve().parents[1] / "app" / "engines" / "e13"
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
    assert "E13" in result.run.engine_versions
    assert "FM_AGI_FUND" in result.run.formula_versions
    assert result.days[0].e13_hashes
    assert result.days[0].e13_scores

    cre = CREService(flags=CREFlags(cre=True, promotion=False))
    eval_result = cre.evaluate("golden_p0_v1", generated_at=FIXED)
    engines = {c.engine for c in eval_result.engine_scorecards}
    assert "E13" in engines
    assert eval_result.promotion is not None
    assert eval_result.promotion.ready is False
    card = next(c for c in eval_result.engine_scorecards if c.engine == "E13")
    assert card.model_version
    assert "fundamental_ls" in card.notes


@pytest.mark.asyncio
async def test_e13_api():
    from app.api import routes as api_routes

    registry = FeatureRegistryService()
    api_routes._e13 = E13Service(registry)
    g = _golden()
    api_routes._e13.run_universe(as_of=g["as_of"], panels=g["panels"], generated_at=FIXED)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/e13/health")
        assert health.status_code == 200
        body = health.json()
        assert body["engine"] == "E13"
        assert body["flags"]["E13_P0"] is True
        assert body["flags"]["E13_ML"] is False

        fund = await client.get("/v1/e13/fundamental/TCS")
        assert fund.status_code == 200
        assert fund.json()["symbol"] == "TCS"
        assert "composite_score" in fund.json()

        hist = await client.get("/v1/e13/history/TCS")
        assert hist.status_code == 200
        assert len(hist.json()) >= 1
