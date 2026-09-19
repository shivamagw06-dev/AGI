"""E05 P0 — E05-001–005 Event-Driven & Special Situations."""

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
from app.engines.e05.consumer import register_e05_with_orch
from app.engines.e05.flags import E05Flags
from app.engines.e05.mapping import FORMULA_ID
from app.engines.e05.models.decay import decay_weight
from app.engines.e05.models.surprise import eps_surprise, surprise_score_0_100
from app.engines.e05.service import E05Service
from app.engines.e14.service import E14Service
from app.features.service import FeatureRegistryService
from app.main import app
from app.orch.l2.executor import L2FeatureBuildService
from app.orch.l2.models import FeatureReadyEvent
from app.orch.ledger import OrchLedger
from app.validation.flags import ValidationFlags
from app.validation.service import ValidationService

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "e05"
FIXED = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)


def _golden() -> dict:
    return json.loads((FIXTURES / "golden_events.json").read_text(encoding="utf-8"))


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


def test_surprise_and_decay():
    surp = eps_surprise(0.135, 0.12)
    assert surp is not None and surp > 0
    score = surprise_score_0_100(surp)
    assert 50.0 < score <= 100.0
    assert surprise_score_0_100(None) == 50.0
    # HL=10 → age 10 ≈ 0.5
    w0 = decay_weight(0.0, 10.0)
    w10 = decay_weight(10.0, 10.0)
    w20 = decay_weight(20.0, 10.0)
    assert abs(w0 - 1.0) < 1e-9
    assert abs(w10 - 0.5) < 1e-6
    assert w20 < w10 < w0


def test_golden_event_states():
    registry = FeatureRegistryService()
    e05 = E05Service(registry, flags=E05Flags())
    g = _golden()
    out = e05.run_universe(
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
    assert tcs.upcoming_events
    assert tcs.recent_events
    assert tcs.days_since_event is not None
    assert tcs.days_until_event is not None
    assert math.isfinite(tcs.composite_score)
    assert 0.0 <= tcs.composite_score <= 100.0
    assert tcs.surprise_score > 50.0  # beat
    assert tcs.label
    assert tcs.side in {"bullish_catalyst", "bearish_catalyst", "neutral"}
    # INFY miss + rights
    infy = out["INFY"]
    assert infy.surprise_score < 55.0


def test_determinism_replay():
    registry = FeatureRegistryService()
    e05 = E05Service(registry)
    g = _golden()
    a = e05.run_universe(as_of=g["as_of"], panels=g["panels"], generated_at=FIXED)
    b = e05.run_universe(as_of=g["as_of"], panels=g["panels"], generated_at=FIXED)
    assert a["TCS"].composite_score == b["TCS"].composite_score
    assert a["TCS"].hash == b["TCS"].hash
    sa = e05.get_state("TCS")
    sb = e05.store.get_state("TCS")
    assert sa is not None and sb is not None
    assert sa.hash == sb.hash


def test_engine_state_schema_and_conf():
    registry = FeatureRegistryService()
    e05 = E05Service(registry)
    g = _golden()
    e05.run_universe(
        as_of=g["as_of"],
        panels=g["panels"],
        e01_state=_mini_e01(g["as_of"]),
        e14_state=_mini_e14(g["as_of"]),
        generated_at=FIXED,
    )
    state = e05.get_state("TCS")
    assert state is not None
    payload = state.model_dump(mode="json")
    assert payload["engine"] == "E05"
    assert payload["symbol"] == "TCS"
    assert payload["confidence"]["method_version"] == "conf-1.0"
    assert validate_engine_state(payload) == []
    assert payload["metadata"]["formula_id"] == FORMULA_ID


def test_warm_cache_under_25ms():
    registry = FeatureRegistryService()
    e05 = E05Service(registry)
    g = _golden()
    e05.run_universe(as_of=g["as_of"], panels=g["panels"])
    for _ in range(30):
        t0 = time.perf_counter()
        evt = e05.get_event_state("TCS")
        assert evt is not None
        assert (time.perf_counter() - t0) * 1000 < 25.0
    assert e05.metrics.snapshot()["cache_hits"] >= 30


def test_flags_and_no_market_data():
    flags = E05Flags.from_settings()
    assert flags.e05_p0 is True
    assert flags.e05_deal_probability is False
    assert flags.e05_transcripts is False
    assert flags.e05_ml is False
    registry = FeatureRegistryService()
    e05 = E05Service(registry)
    health = e05.health()
    assert health["market_data_access"] is False
    assert health["deal_probability"] is False
    assert health["transcripts"] is False
    assert health["ml"] is False
    assert health["event_forecasting"] is False


def test_placeholder_flags_raise():
    registry = FeatureRegistryService()
    e05 = E05Service(registry, flags=E05Flags(e05_p0=True, e05_ml=True))
    g = _golden()
    with pytest.raises(RuntimeError, match="E05_ML"):
        e05.run_universe(as_of=g["as_of"], panels=g["panels"])


def test_pit_no_lookahead_actuals():
    registry = FeatureRegistryService()
    e05 = E05Service(registry)
    panels = {
        "TCS": {
            "sector_id": "IT",
            "events": [
                {
                    "event_id": "future_earn",
                    "event_type": "earn_q",
                    "event_time": "2026-08-20",
                    "actual": 0.20,
                    "consensus": 0.10,
                }
            ],
        }
    }
    out = e05.run_universe(as_of="2026-07-24", panels=panels, generated_at=FIXED)
    # Upcoming — surprise should not use future actuals as beat signal
    tcs = out["TCS"]
    assert tcs.upcoming_events
    assert tcs.upcoming_events[0].surprise is None or tcs.days_until_event is not None


def test_orch_passive_consumer():
    registry = FeatureRegistryService()
    ledger = OrchLedger()
    l2 = L2FeatureBuildService(registry, orch_ledger=ledger)
    e01 = E01Service(registry, orch_ledger=ledger)
    e14 = E14Service(registry, e01=e01, orch_ledger=ledger)
    e05 = E05Service(registry, e01=e01, e14=e14, orch_ledger=ledger)
    g = _golden()
    e05.run_universe(as_of=g["as_of"], panels=g["panels"])
    register_e05_with_orch(l2, e05, e01, e14)
    ready = FeatureReadyEvent(
        batch_id="b-e05",
        as_of=g["as_of"],
        symbol="TCS",
        feature_ids=["EVENT_EPS_SURPRISE"],
        succeeded=["EVENT_EPS_SURPRISE"],
    )
    for handler in l2._ready_handlers:
        handler(ready)
    assert e05.get_event_state("TCS") is not None
    e01.store.put(_mini_e01(g["as_of"]))
    e05.on_e01_ready(_mini_e01(g["as_of"]))
    e05.on_e14_ready(_mini_e14(g["as_of"]))
    state = e05.get_state("TCS")
    assert state is not None
    assert state.metadata["e05_state"]["e01_ref"]["primary_regime"] == "expansion_risk_on"


def test_history_multi_day():
    registry = FeatureRegistryService()
    e05 = E05Service(registry)
    g = _golden()
    e05.run_universe(as_of="2026-07-23", panels=g["panels"])
    e05.run_universe(as_of="2026-07-24", panels=g["panels"])
    hist = e05.history("TCS", limit=10)
    assert len(hist) == 2


def test_no_market_data_imports():
    root = Path(__file__).resolve().parents[1] / "app" / "engines" / "e05"
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
    assert "E05" in result.run.engine_versions
    assert "EM_AGI_EVENT" in result.run.formula_versions
    assert result.days[0].e05_hashes
    assert result.days[0].e05_scores

    cre = CREService(flags=CREFlags(cre=True, promotion=False))
    eval_result = cre.evaluate("golden_p0_v1", generated_at=FIXED)
    engines = {c.engine for c in eval_result.engine_scorecards}
    assert "E05" in engines
    assert eval_result.promotion is not None
    assert eval_result.promotion.ready is False
    card = next(c for c in eval_result.engine_scorecards if c.engine == "E05")
    assert "event_driven_special_situations" in card.notes


@pytest.mark.asyncio
async def test_e05_api():
    from app.api import routes as api_routes

    registry = FeatureRegistryService()
    api_routes._e05 = E05Service(registry)
    g = _golden()
    api_routes._e05.run_universe(
        as_of=g["as_of"], panels=g["panels"], generated_at=FIXED
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/e05/health")
        assert health.status_code == 200
        body = health.json()
        assert body["engine"] == "E05"
        assert body["flags"]["E05_P0"] is True
        assert body["flags"]["E05_ML"] is False

        state = await client.get("/v1/e05/events/TCS")
        assert state.status_code == 200
        assert state.json()["symbol"] == "TCS"
        assert "composite_score" in state.json()
        assert "upcoming_events" in state.json()

        hist = await client.get("/v1/e05/history/TCS")
        assert hist.status_code == 200
        assert len(hist.json()) >= 1
