"""L4 P0 Shadow — L4-001–005 Composite Intelligence."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.contracts.engine_state import EngineState, empty_evidence_pack, validate_engine_state
from app.engines.e01.service import E01Service
from app.engines.e02.exposure import E02Exposure
from app.engines.e02.service import E02Service
from app.engines.e03.alpha import E03Alpha
from app.engines.e03.service import E03Service
from app.engines.e14.service import E14Service
from app.engines.l4.conflict import resolve_conflicts
from app.engines.l4.collector import collect_inputs
from app.engines.l4.consumer import register_l4_with_orch
from app.engines.l4.evidence import aggregate_evidence
from app.engines.l4.flags import L4Flags
from app.engines.l4.service import L4Service
from app.features.service import FeatureRegistryService
from app.main import app
from app.orch.ledger import OrchLedger

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "l4"


def _golden() -> dict:
    return json.loads((FIXTURES / "golden_shadow.json").read_text(encoding="utf-8"))


def _e01(as_of: str, meta: dict) -> EngineState:
    return EngineState.model_validate(
        {
            "engine": "E01",
            "version": "1.0.0",
            "model_version": "e01-p0-axes-0.1.0",
            "as_of": as_of,
            "score": {
                "raw": meta["score"],
                "normalized_0_100": meta["score"],
                "normalized_signed": (meta["score"] - 50) / 50,
                "unit": "score",
            },
            "confidence": {
                "value": meta["confidence"],
                "components": {"C_coverage": 0.8, "C_freshness": 0.8, "C_stability": 0.7},
                "method_version": "conf-1.0",
            },
            "metadata": {
                "primary_regime": meta["primary_regime"],
                "risk_level": "low",
                "size_multiplier": 1.0,
            },
            "evidence": empty_evidence_pack(),
            "explanation": {"summary": "fixture"},
            "warnings": [],
            "stale_inputs": [],
            "input_hash": "sha256:" + ("a" * 64),
            "hash": "sha256:" + ("b" * 64),
            "timestamp_generated": datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc).isoformat(),
        }
    )


def _e14(as_of: str, meta: dict) -> EngineState:
    return EngineState.model_validate(
        {
            "engine": "E14",
            "version": "1.0.0",
            "model_version": "e14-p0-rules-0.1.0",
            "as_of": as_of,
            "score": {
                "raw": meta["score"],
                "normalized_0_100": meta["score"],
                "normalized_signed": (meta["score"] - 50) / 50,
                "unit": "score",
            },
            "confidence": {
                "value": meta["confidence"],
                "components": {"C_coverage": 0.7, "C_freshness": 0.8, "C_model": 0.7},
                "method_version": "conf-1.0",
            },
            "metadata": {
                "playbook": meta["playbook"],
                "risk_level": meta["risk_level"],
                "confidence_adjustment": meta["confidence_adjustment"],
                "gate": meta["gate"],
                "size_multiplier": 0.5 if meta["playbook"] == "hard_derisk" else 0.9,
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


def _e02(as_of: str, symbol: str, meta: dict) -> E02Exposure:
    return E02Exposure(
        as_of=as_of,
        universe_id="NIFTY500",
        symbol=symbol,
        sector_id=meta.get("sector_id"),
        scores={"F_QUALITY": meta["composite_score"]},
        loadings={"F_QUALITY": 0.5},
        composite_score=meta["composite_score"],
        dominant_factor=meta["dominant_factor"],
        style_box={"size": "large", "style": "quality"},
        factor_confidence=meta["factor_confidence"],
        hash="sha256:" + ("e" * 64),
    )


def _e03(as_of: str, symbol: str, meta: dict) -> E03Alpha:
    return E03Alpha(
        as_of=as_of,
        universe_id="NIFTY500",
        symbol=symbol,
        agi_tech_score=meta["agi_tech_score"],
        composite_alpha_score=meta["agi_tech_score"],
        label=meta["label"],
        confidence=meta["confidence"],
        confidence_pct=meta["confidence_pct"],
        top_features=["rsi", "macd"],
        hash="sha256:" + ("f" * 64),
    )


def _run_case(case: dict, *, generated_at: datetime | None = None) -> tuple:
    g = _golden()
    as_of = g["as_of"]
    l4 = L4Service(flags=L4Flags())
    opinion = l4.run(
        symbol=case["symbol"],
        as_of=as_of,
        e01_state=_e01(as_of, case["e01"]),
        e14_state=_e14(as_of, case["e14"]),
        e02_exposure=_e02(as_of, case["symbol"], case["e02"]),
        e03_alpha=_e03(as_of, case["symbol"], case["e03"]),
        universe_id=g["universe_id"],
        generated_at=generated_at,
    )
    return l4, opinion


def test_collector_and_evidence():
    g = _golden()
    case = g["cases"][0]
    as_of = g["as_of"]
    inputs = collect_inputs(
        symbol=case["symbol"],
        as_of=as_of,
        e01=_e01(as_of, case["e01"]),
        e14=_e14(as_of, case["e14"]),
        e02=_e02(as_of, case["symbol"], case["e02"]),
        e03=_e03(as_of, case["symbol"], case["e03"]),
    )
    assert inputs.completeness == 1.0
    assert not inputs.missing
    evidence = aggregate_evidence(inputs)
    assert evidence["positive"] or evidence["negative"]
    assert any(i.get("engine") == "E02" for i in evidence["unknowns"])


def test_conflict_hard_derisk_prefers_neutral():
    g = _golden()
    case = next(c for c in g["cases"] if c["symbol"] == "RISKY")
    as_of = g["as_of"]
    inputs = collect_inputs(
        symbol=case["symbol"],
        as_of=as_of,
        e01=_e01(as_of, case["e01"]),
        e14=_e14(as_of, case["e14"]),
        e02=_e02(as_of, case["symbol"], case["e02"]),
        e03=_e03(as_of, case["symbol"], case["e03"]),
    )
    evidence = aggregate_evidence(inputs)
    resolution = resolve_conflicts(inputs, evidence)
    assert resolution.prefer_neutral is True
    assert resolution.confidence_mult <= 0.55
    assert evidence["contradictions"]
    l4, opinion = _run_case(case)
    assert opinion.shadow is True
    assert opinion.primary is False
    assert opinion.confidence < case["e03"]["confidence"]
    # Pulled toward neutral vs raw Strong Bullish E03
    assert opinion.label in {"Neutral", "Bullish", "Bearish", "Strong Bearish"}
    assert opinion.label != "Strong Bullish" or opinion.confidence_mult <= 0.55


def test_shadow_opinion_schema_and_conf():
    g = _golden()
    case = g["cases"][0]
    l4, opinion = _run_case(case)
    assert opinion.engine == "L4"
    assert opinion.shadow is True
    assert opinion.primary is False
    assert opinion.label
    assert opinion.dominant_drivers
    assert opinion.explanation.get("summary")
    assert "Production remains E03" in opinion.explanation["summary"]
    state = l4.get_state(case["symbol"])
    assert state is not None
    payload = state.model_dump(mode="json")
    assert payload["engine"] == "L4"
    assert payload["confidence"]["method_version"] == "conf-1.0"
    assert "shadow_mode" in payload["warnings"]
    assert payload["metadata"]["production_influence"] is False
    assert validate_engine_state(payload) == []


def test_shadow_comparison():
    g = _golden()
    case = g["cases"][0]
    l4, opinion = _run_case(case)
    shadow = l4.get_shadow(case["symbol"])
    assert shadow is not None
    assert shadow.legacy_label == case["e03"]["label"]
    assert shadow.l4_label == opinion.label
    assert shadow.shadow is True
    assert shadow.evidence_summary


def test_determinism_replay():
    g = _golden()
    case = g["cases"][0]
    fixed = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
    l4a, a = _run_case(case, generated_at=fixed)
    l4b, b = _run_case(case, generated_at=fixed)
    assert a.label == b.label
    assert a.composite_score == b.composite_score
    assert a.confidence == b.confidence
    assert a.hash == b.hash
    assert l4a.get_state(case["symbol"]).hash == l4b.get_state(case["symbol"]).hash


def test_warm_cache_under_25ms():
    g = _golden()
    case = g["cases"][0]
    l4, _ = _run_case(case)
    for _ in range(30):
        t0 = time.perf_counter()
        op = l4.get_opinion(case["symbol"])
        assert op is not None
        assert (time.perf_counter() - t0) * 1000 < 25.0
    assert l4.metrics.snapshot()["cache_hits"] >= 30


def test_feature_flags_no_production_influence():
    flags = L4Flags.from_settings()
    assert flags.l4_shadow is True
    assert flags.l4_primary is False
    assert flags.l4_bayes is False
    assert flags.l4_ml is False
    assert flags.l4_probability is False
    l4 = L4Service(flags=flags)
    health = l4.health()
    assert health["production_influence"] is False
    assert health["replaces_e03"] is False
    assert health["market_data_access"] is False
    assert health["feature_snapshot_access"] is False
    assert health["flags"]["L4_PRIMARY"] is False


def test_primary_flag_rejected():
    l4 = L4Service(flags=L4Flags(l4_shadow=True, l4_primary=True))
    g = _golden()
    case = g["cases"][0]
    with pytest.raises(RuntimeError, match="L4_PRIMARY"):
        l4.run(
            symbol=case["symbol"],
            as_of=g["as_of"],
            e03_alpha=_e03(g["as_of"], case["symbol"], case["e03"]),
        )


def test_history():
    g = _golden()
    case = g["cases"][2]
    l4 = L4Service()
    for day in ("2026-07-23", "2026-07-24"):
        l4.run(
            symbol=case["symbol"],
            as_of=day,
            e01_state=_e01(day, case["e01"]),
            e14_state=_e14(day, case["e14"]),
            e02_exposure=_e02(day, case["symbol"], case["e02"]),
            e03_alpha=_e03(day, case["symbol"], case["e03"]),
        )
    assert len(l4.history(case["symbol"])) == 2


def test_orch_integration_e03_ready():
    registry = FeatureRegistryService()
    ledger = OrchLedger()
    e01 = E01Service(registry, orch_ledger=ledger)
    e14 = E14Service(registry, e01=e01, orch_ledger=ledger)
    e02 = E02Service(registry, e01=e01, e14=e14, orch_ledger=ledger)
    e03 = E03Service(registry, e01=e01, e14=e14, e02=e02, orch_ledger=ledger)
    l4 = L4Service(e01=e01, e14=e14, e02=e02, e03=e03, orch_ledger=ledger)
    register_l4_with_orch(l4, e01, e14, e02, e03)

    g = _golden()
    case = g["cases"][0]
    as_of = g["as_of"]
    # Seed E01/E14 stores
    e01.store.put(_e01(as_of, case["e01"]))
    e14.store.put(_e14(as_of, case["e14"]))
    e02.store.put(
        _e02(as_of, case["symbol"], case["e02"]),
        EngineState.model_validate(
            {
                "engine": "E02",
                "version": "1.0.0",
                "model_version": "e02-p0-factors-0.1.0",
                "as_of": as_of,
                "symbol": case["symbol"],
                "score": {"raw": 60.0, "normalized_0_100": 60.0, "normalized_signed": 0.2, "unit": "score"},
                "confidence": {
                    "value": 0.7,
                    "components": {"C_coverage": 0.7, "C_freshness": 0.7, "C_stability": 0.7},
                    "method_version": "conf-1.0",
                },
                "metadata": {},
                "evidence": empty_evidence_pack(),
                "explanation": {"summary": "x"},
                "warnings": [],
                "stale_inputs": [],
                "input_hash": "sha256:" + ("1" * 64),
                "hash": "sha256:" + ("2" * 64),
                "timestamp_generated": datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc).isoformat(),
            }
        ),
    )
    alpha = _e03(as_of, case["symbol"], case["e03"])
    # Trigger via wrapped e03.run_universe path by calling on_e03_ready directly after register
    out = l4.on_e03_ready({case["symbol"]: alpha})
    assert case["symbol"] in out
    assert l4.get_opinion(case["symbol"]) is not None
    assert l4.get_opinion(case["symbol"]).shadow is True
    # Ensure E03 path itself unchanged — alpha object not mutated
    assert alpha.label == case["e03"]["label"]


@pytest.mark.asyncio
async def test_l4_api():
    from app.api import routes as api_routes

    g = _golden()
    case = g["cases"][0]
    as_of = g["as_of"]
    api_routes._l4.run(
        symbol=case["symbol"],
        as_of=as_of,
        e01_state=_e01(as_of, case["e01"]),
        e14_state=_e14(as_of, case["e14"]),
        e02_exposure=_e02(as_of, case["symbol"], case["e02"]),
        e03_alpha=_e03(as_of, case["symbol"], case["e03"]),
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/l4/health")
        assert health.status_code == 200
        body = health.json()
        assert body["engine"] == "L4"
        assert body["flags"]["L4_SHADOW"] is True
        assert body["flags"]["L4_PRIMARY"] is False
        assert body["production_influence"] is False
        assert body["market_data_access"] is False
        op = await client.get(f"/v1/l4/opinion/{case['symbol']}")
        assert op.status_code == 200
        payload = op.json()
        assert payload["engine"] == "L4"
        assert payload["shadow"] is True
        assert payload["primary"] is False
        hist = await client.get(f"/v1/l4/history/{case['symbol']}")
        assert hist.status_code == 200
        assert len(hist.json()) >= 1
        assert validate_engine_state(hist.json()[0]) == []


def test_no_market_data_or_feature_snapshot_imports():
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app" / "engines" / "l4"
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [a.name for a in node.names]
            else:
                continue
            joined = " ".join(names)
            assert "MarketDataClient" not in joined
            assert "market_data" not in joined
            assert "FeatureSnapshot" not in joined
            assert "features.models" not in joined
