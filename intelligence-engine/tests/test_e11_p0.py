"""E11 P0 — EPIC-015 / E11-001–005 Sentiment soft voter."""

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
from app.engines.e11.consumer import register_e11_with_orch
from app.engines.e11.entity_map import EntityMap
from app.engines.e11.flags import E11Flags
from app.engines.e11.mapping import FORMULA_ID, SOCIAL_WEIGHT_CAP
from app.engines.e11.models.decay import decay_weight
from app.engines.e11.models.scoring import news_document_score, tone_from_text, tone_to_score
from app.engines.e11.service import E11Service
from app.engines.e11.soft_voter import soft_voter_contribution
from app.engines.e14.service import E14Service
from app.engines.l4.service import L4Service
from app.features.service import FeatureRegistryService
from app.main import app
from app.orch.l2.executor import L2FeatureBuildService
from app.orch.l2.models import FeatureReadyEvent
from app.orch.ledger import OrchLedger
from app.validation.flags import ValidationFlags
from app.validation.service import ValidationService

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "e11"
FIXED = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)


def _golden() -> dict:
    return json.loads((FIXTURES / "golden_sentiment.json").read_text(encoding="utf-8"))


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


def test_entity_map_resolution():
    em = EntityMap()
    rec = em.upsert(symbol="TCS", name="Tata Consultancy", aliases=["TATA CONSULTANCY"], sector_id="IT")
    assert rec.entity_id == "ENT:TCS"
    assert em.resolve("tcs") is not None
    assert em.resolve("TATA CONSULTANCY").symbol == "TCS"


def test_news_scoring_and_decay():
    assert tone_from_text("company beat estimates on strong growth") > 0
    assert tone_from_text("miss guidance cut weak demand") < 0
    assert tone_to_score(1.0) == 100.0
    assert tone_to_score(-1.0) == 0.0
    w0 = decay_weight(age_hours=0.0)
    w72 = decay_weight(age_hours=72.0)  # HL=3d → age 3d → ~0.5
    assert abs(w0 - 1.0) < 1e-9
    assert abs(w72 - 0.5) < 1e-3
    fresh = news_document_score(
        tone=0.5, volume=10, age_hours=1, decay_w=1.0, reliability=0.85, entity_link=0.95
    )
    stale = news_document_score(
        tone=0.5, volume=10, age_hours=200, decay_w=0.05, reliability=0.85, entity_link=0.95
    )
    assert fresh > 50.0
    assert abs(stale - 50.0) < abs(fresh - 50.0)


def test_golden_sentiment_states():
    registry = FeatureRegistryService()
    e11 = E11Service(registry, flags=E11Flags())
    g = _golden()
    out = e11.run_universe(
        as_of=g["as_of"],
        panels=g["panels"],
        e01_state=_mini_e01(g["as_of"]),
        e14_state=_mini_e14(g["as_of"]),
        universe_id=g["universe_id"],
        generated_at=FIXED,
    )
    assert "TCS" in out
    tcs = out["TCS"]
    assert tcs.formula_id == FORMULA_ID
    assert tcs.entity_id == "ENT:TCS"
    assert tcs.news_score > 50.0
    assert 0.0 <= tcs.composite_score <= 100.0
    assert tcs.social_enabled is False
    assert tcs.social_weight_cap == SOCIAL_WEIGHT_CAP
    assert tcs.soft_voter_weight <= SOCIAL_WEIGHT_CAP
    assert out["INFY"].news_score < 50.0


def test_determinism_replay():
    registry = FeatureRegistryService()
    e11 = E11Service(registry)
    g = _golden()
    a = e11.run_universe(as_of=g["as_of"], panels=g["panels"], generated_at=FIXED)
    b = e11.run_universe(as_of=g["as_of"], panels=g["panels"], generated_at=FIXED)
    assert a["TCS"].hash == b["TCS"].hash
    assert a["TCS"].composite_score == b["TCS"].composite_score


def test_engine_state_schema_and_conf():
    registry = FeatureRegistryService()
    e11 = E11Service(registry)
    g = _golden()
    e11.run_universe(
        as_of=g["as_of"],
        panels=g["panels"],
        e01_state=_mini_e01(g["as_of"]),
        e14_state=_mini_e14(g["as_of"]),
        generated_at=FIXED,
    )
    state = e11.get_state("TCS")
    assert state is not None
    payload = state.model_dump(mode="json")
    assert payload["engine"] == "E11"
    assert payload["confidence"]["method_version"] == "conf-1.0"
    assert validate_engine_state(payload) == []
    assert payload["metadata"]["social_weight_cap"] == SOCIAL_WEIGHT_CAP


def test_warm_cache_under_25ms():
    registry = FeatureRegistryService()
    e11 = E11Service(registry)
    g = _golden()
    e11.run_universe(as_of=g["as_of"], panels=g["panels"])
    for _ in range(30):
        t0 = time.perf_counter()
        sent = e11.get_sentiment_state("TCS")
        assert sent is not None
        assert (time.perf_counter() - t0) * 1000 < 25.0


def test_flags_and_placeholders():
    flags = E11Flags.from_settings()
    assert flags.e11_p0 is True
    assert flags.e11_social is False
    assert flags.e11_llm is False
    registry = FeatureRegistryService()
    e11 = E11Service(registry, flags=E11Flags(e11_p0=True, e11_ml=True))
    g = _golden()
    with pytest.raises(RuntimeError, match="E11_ML"):
        e11.run_universe(as_of=g["as_of"], panels=g["panels"])
    health = E11Service(registry).health()
    assert health["market_data_access"] is False
    assert health["social"] is False


def test_soft_voter_absent_weight_zero_chaos():
    """E11-005: absent soft voter ⇒ L4 weight 0; L4 still runs."""
    absent = soft_voter_contribution(None)
    assert absent["present"] is False
    assert absent["weight"] == 0.0

    registry = FeatureRegistryService()
    ledger = OrchLedger()
    e01 = E01Service(registry, orch_ledger=ledger)
    e14 = E14Service(registry, e01=e01, orch_ledger=ledger)
    e02 = E02Service(registry, e01=e01, e14=e14, orch_ledger=ledger)
    e03 = E03Service(registry, e01=e01, e14=e14, e02=e02, orch_ledger=ledger)
    # L4 without e11 wired — chaos kill path
    l4 = L4Service(e01=e01, e14=e14, e02=e02, e03=e03, e11=None, orch_ledger=ledger)
    e01.store.put(_mini_e01("2026-07-24"))
    e14.store.put(_mini_e14("2026-07-24"))
    # Minimal e03 via run_universe empty panels may fail — use collect path with None e03 but e01/e14
    op = l4.run(
        symbol="TCS",
        as_of="2026-07-24",
        e01_state=_mini_e01("2026-07-24"),
        e14_state=_mini_e14("2026-07-24"),
        e03_alpha=None,
        e11_state=None,
        generated_at=FIXED,
    )
    assert op is not None
    engines = {c["engine"] for c in op.engine_contributions}
    assert "E11" not in engines


def test_orch_passive_consumer():
    registry = FeatureRegistryService()
    ledger = OrchLedger()
    l2 = L2FeatureBuildService(registry, orch_ledger=ledger)
    e01 = E01Service(registry, orch_ledger=ledger)
    e14 = E14Service(registry, e01=e01, orch_ledger=ledger)
    e11 = E11Service(registry, e01=e01, e14=e14, orch_ledger=ledger)
    g = _golden()
    e11.run_universe(as_of=g["as_of"], panels=g["panels"])
    register_e11_with_orch(l2, e11, e01, e14)
    ready = FeatureReadyEvent(
        batch_id="b-e11",
        as_of=g["as_of"],
        symbol="TCS",
        feature_ids=["SENT_NEWS"],
        succeeded=["SENT_NEWS"],
    )
    for handler in l2._ready_handlers:
        handler(ready)
    e01.store.put(_mini_e01(g["as_of"]))
    e11.on_e01_ready(_mini_e01(g["as_of"]))
    e11.on_e14_ready(_mini_e14(g["as_of"]))
    state = e11.get_state("TCS")
    assert state is not None
    assert state.metadata["e11_state"]["e01_ref"]["primary_regime"] == "expansion_risk_on"


def test_no_market_data_imports():
    root = Path(__file__).resolve().parents[1] / "app" / "engines" / "e11"
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
    assert "E11" in result.run.engine_versions
    assert "SM_AGI_SENT" in result.run.formula_versions
    assert result.days[0].e11_hashes
    assert result.days[0].e11_scores

    cre = CREService(flags=CREFlags(cre=True, promotion=False))
    eval_result = cre.evaluate("golden_p0_v1", generated_at=FIXED)
    engines = {c.engine for c in eval_result.engine_scorecards}
    assert "E11" in engines
    assert eval_result.promotion.ready is False
    card = next(c for c in eval_result.engine_scorecards if c.engine == "E11")
    assert "sentiment_soft_voter" in card.notes


@pytest.mark.asyncio
async def test_e11_api():
    from app.api import routes as api_routes

    registry = FeatureRegistryService()
    api_routes._e11 = E11Service(registry)
    g = _golden()
    api_routes._e11.run_universe(as_of=g["as_of"], panels=g["panels"], generated_at=FIXED)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/e11/health")
        assert health.status_code == 200
        assert health.json()["flags"]["E11_P0"] is True
        assert health.json()["social_weight_cap"] == SOCIAL_WEIGHT_CAP

        sent = await client.get("/v1/e11/sentiment/TCS")
        assert sent.status_code == 200
        assert sent.json()["symbol"] == "TCS"
        assert "news_score" in sent.json()

        state = await client.get("/v1/e11/state/TCS")
        assert state.status_code == 200

        hist = await client.get("/v1/e11/history/TCS")
        assert hist.status_code == 200
        assert len(hist.json()) >= 1
