"""E03 P0/M0 — E03-001–005 SM_AGI_TECH production parity."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.contracts.engine_state import EngineState, empty_evidence_pack, validate_engine_state
from app.engines.e01.service import E01Service
from app.engines.e02.service import E02Service
from app.engines.e03.consumer import register_e03_with_orch
from app.engines.e03.flags import E03Flags
from app.engines.e03.legacy import category_legacy, confidence_legacy, score_research_legacy
from app.engines.e03.parity.audit import run_parity_audit
from app.engines.e03.service import E03Service
from app.engines.e03.submodels.agi_tech import confidence, run_sm_agi_tech, score_research
from app.engines.e03.submodels.label_bands import category as category_bands
from app.engines.e14.service import E14Service
from app.features.service import FeatureRegistryService
from app.main import app
from app.orch.l2.executor import L2FeatureBuildService
from app.orch.l2.models import FeatureReadyEvent
from app.orch.ledger import OrchLedger

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "e03"


def _golden() -> dict:
    return json.loads((FIXTURES / "golden_indicators.json").read_text(encoding="utf-8"))


def _panels() -> dict[str, dict]:
    g = _golden()
    return {row["symbol"]: row["indicators"] for row in g["symbols"]}


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


def test_score_research_exact_golden():
    g = _golden()
    for row in g["symbols"]:
        score = score_research(row["indicators"])
        assert score == row["legacy_score"]
        assert category_bands(score) == row["legacy_label"]
        assert confidence(score, row["indicators"]) == row["legacy_confidence_pct"]


def test_legacy_vs_sm_agi_tech_bit_parity():
    panels = _panels()
    for sym, ind in panels.items():
        legacy = score_research_legacy(ind)
        result = run_sm_agi_tech(ind)
        assert result.agi_tech_score == legacy
        assert result.label == category_legacy(legacy)
        assert result.confidence_pct == confidence_legacy(legacy, ind)


def test_label_band_boundaries():
    assert category_bands(72) == "Strong Bullish"
    assert category_bands(71.9) == "Bullish"
    assert category_bands(58) == "Bullish"
    assert category_bands(57.9) == "Neutral"
    assert category_bands(43) == "Neutral"
    assert category_bands(42.9) == "Bearish"
    assert category_bands(28) == "Bearish"
    assert category_bands(27.9) == "Strong Bearish"


def test_parity_report_passes_99pct():
    panels = _panels()
    report = run_parity_audit(panels, as_of="2026-07-24")
    assert report.n_symbols == 20
    assert report.within_0_1_rate >= 0.99
    assert report.bucket_agreement_rate >= 0.99
    assert report.confidence_agreement_rate >= 0.99
    assert report.max_drift <= 0.1
    assert report.passed is True
    assert all(r.agreement for r in report.rows)


def test_engine_state_schema_and_conf():
    registry = FeatureRegistryService()
    e03 = E03Service(registry)
    g = _golden()
    e03.run_universe(
        as_of=g["as_of"],
        panels=_panels(),
        e01_state=_mini_e01(g["as_of"]),
        e14_state=_mini_e14(g["as_of"]),
    )
    state = e03.get_state("TCS")
    assert state is not None
    payload = state.model_dump(mode="json")
    assert payload["engine"] == "E03"
    assert payload["confidence"]["method_version"] == "conf-1.0"
    assert validate_engine_state(payload) == []
    assert "positive" in payload["evidence"] or "negative" in payload["evidence"]
    assert payload["metadata"]["label"] in {
        "Strong Bullish",
        "Bullish",
        "Neutral",
        "Bearish",
        "Strong Bearish",
    }


def test_determinism_replay():
    registry = FeatureRegistryService()
    e03 = E03Service(registry)
    g = _golden()
    fixed = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
    a = e03.run_universe(as_of=g["as_of"], panels=_panels(), generated_at=fixed)
    b = e03.run_universe(as_of=g["as_of"], panels=_panels(), generated_at=fixed)
    assert a["TCS"].agi_tech_score == b["TCS"].agi_tech_score
    assert a["TCS"].label == b["TCS"].label
    assert a["TCS"].hash == b["TCS"].hash
    sa = e03.get_state("TCS")
    assert sa is not None
    assert sa.hash == e03.store.get_state("TCS").hash


def test_warm_cache_under_25ms():
    registry = FeatureRegistryService()
    e03 = E03Service(registry)
    g = _golden()
    e03.run_universe(as_of=g["as_of"], panels=_panels())
    for _ in range(30):
        t0 = time.perf_counter()
        alpha = e03.get_alpha("TCS")
        assert alpha is not None
        assert (time.perf_counter() - t0) * 1000 < 25.0
    assert e03.metrics.snapshot()["cache_hits"] >= 30


def test_feature_flags():
    flags = E03Flags.from_settings()
    assert flags.e03_p0 is True
    assert flags.e03_parity is True
    assert flags.e03_composite is False
    assert flags.e03_xs_mode is False
    assert flags.e03_ml is False
    registry = FeatureRegistryService()
    e03 = E03Service(registry)
    health = e03.health()
    assert health["market_data_access"] is False
    assert health["polling"] is False
    assert health["flags"]["E03_COMPOSITE"] is False


def test_history():
    registry = FeatureRegistryService()
    e03 = E03Service(registry)
    panels = _panels()
    e03.run_universe(as_of="2026-07-23", panels=panels)
    e03.run_universe(as_of="2026-07-24", panels=panels)
    hist = e03.history("TCS")
    assert len(hist) == 2


def test_orch_integration():
    registry = FeatureRegistryService()
    ledger = OrchLedger()
    l2 = L2FeatureBuildService(registry, orch_ledger=ledger)
    e01 = E01Service(registry, orch_ledger=ledger)
    e14 = E14Service(registry, e01=e01, orch_ledger=ledger)
    e02 = E02Service(registry, e01=e01, e14=e14, orch_ledger=ledger)
    e03 = E03Service(registry, e01=e01, e14=e14, e02=e02, orch_ledger=ledger)
    g = _golden()
    panels = _panels()
    e03.run_universe(as_of=g["as_of"], panels=panels)
    register_e03_with_orch(l2, e03, e01, e14, e02)
    ready = FeatureReadyEvent(
        batch_id="b1",
        as_of=g["as_of"],
        symbol="TCS",
        feature_ids=["TECH_RSI_14"],
        succeeded=["TECH_RSI_14"],
    )
    for handler in l2._ready_handlers:
        handler(ready)
    assert e03.get_alpha("TCS") is not None
    e03.on_e01_ready(_mini_e01(g["as_of"]))
    e03.on_e14_ready(_mini_e14(g["as_of"]))
    state = e03.get_state("TCS")
    assert state is not None
    assert state.metadata["e03_alpha"]["e01_ref"]["primary_regime"] == "expansion_risk_on"
    parity = e03.get_parity()
    assert parity is not None and parity.passed


@pytest.mark.asyncio
async def test_e03_api():
    from app.api import routes as api_routes

    g = _golden()
    api_routes._e03.run_universe(as_of=g["as_of"], panels=_panels())
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/e03/health")
        assert health.status_code == 200
        body = health.json()
        assert body["engine"] == "E03"
        assert body["flags"]["E03_P0"] is True
        assert body["flags"]["E03_ML"] is False
        assert body["market_data_access"] is False
        alpha = await client.get("/v1/e03/alpha/TCS")
        assert alpha.status_code == 200
        payload = alpha.json()
        assert payload["engine"] == "E03"
        assert payload["submodel_id"] == "SM_AGI_TECH"
        assert payload["label"] in {
            "Strong Bullish",
            "Bullish",
            "Neutral",
            "Bearish",
            "Strong Bearish",
        }
        hist = await client.get("/v1/e03/history/TCS")
        assert hist.status_code == 200
        assert len(hist.json()) >= 1
        assert validate_engine_state(hist.json()[0]) == []
        parity = await client.get("/v1/e03/parity")
        assert parity.status_code == 200
        assert parity.json()["passed"] is True
        assert parity.json()["within_0_1_rate"] >= 0.99


def test_indicator_contributions_present():
    result = run_sm_agi_tech(_panels()["TCS"])
    assert set(result.contributions) >= {
        "rsi",
        "macd",
        "price_vs_sma",
        "sma_alignment",
        "change_20d",
        "change_60d",
        "volume_confirmation",
        "range_position",
        "roc",
    }
    assert abs(50.0 + sum(result.contributions.values()) - result.agi_tech_score) < 0.11
