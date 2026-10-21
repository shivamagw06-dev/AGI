"""E10 P0 — E10-001–005 Portfolio Construction (model portfolio only)."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.contracts.engine_state import EngineState, empty_evidence_pack, validate_engine_state
from app.engines.e02.exposure import E02Exposure
from app.engines.e02.service import E02Service
from app.engines.e10.consumer import register_e10_with_orch
from app.engines.e10.flags import E10Flags
from app.engines.e10.mapping import NAME_CAP, SECTOR_CAP
from app.engines.e10.service import E10Service
from app.engines.e14.service import E14Service
from app.engines.l4.opinion import L4Opinion
from app.engines.l4.service import L4Service
from app.features.service import FeatureRegistryService
from app.main import app
from app.orch.ledger import OrchLedger

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "e10"


def _golden() -> dict:
    return json.loads((FIXTURES / "golden_book.json").read_text(encoding="utf-8"))


def _e14(as_of: str, *, playbook: str = "normal", risk_level: str = "moderate", size_mult: float = 1.0, adj: float = 1.0, gate: str = "allow", vol_target: float | None = 0.12) -> EngineState:
    meta = {
        "playbook": playbook,
        "risk_level": risk_level,
        "size_multiplier": size_mult,
        "confidence_adjustment": adj,
        "gate": gate,
    }
    if vol_target is not None:
        meta["vol_target_suggested"] = vol_target
    return EngineState.model_validate(
        {
            "engine": "E14",
            "version": "1.0.0",
            "model_version": "e14-p0-rules-0.1.0",
            "as_of": as_of,
            "score": {"raw": 40.0, "normalized_0_100": 40.0, "normalized_signed": -0.2, "unit": "score"},
            "confidence": {
                "value": 0.7,
                "components": {"C_coverage": 0.7, "C_freshness": 0.8, "C_model": 0.7},
                "method_version": "conf-1.0",
            },
            "metadata": meta,
            "evidence": empty_evidence_pack(),
            "explanation": {"summary": "fixture"},
            "warnings": [],
            "stale_inputs": [],
            "input_hash": "sha256:" + ("c" * 64),
            "hash": "sha256:" + ("d" * 64),
            "timestamp_generated": datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc).isoformat(),
        }
    )


def _opinions(g: dict) -> dict[str, L4Opinion]:
    out: dict[str, L4Opinion] = {}
    for row in g["symbols"]:
        out[row["symbol"]] = L4Opinion(
            as_of=g["as_of"],
            universe_id=g["universe_id"],
            symbol=row["symbol"],
            label=row["l4_label"],
            composite_score=row["l4_score"],
            confidence=row["l4_confidence"],
            explanation={"summary": "fixture"},
            hash="sha256:" + (row["symbol"].lower().ljust(64, "0")[:64]),
        )
    return out


def _exposures(g: dict) -> dict[str, E02Exposure]:
    out: dict[str, E02Exposure] = {}
    for row in g["symbols"]:
        out[row["symbol"]] = E02Exposure(
            as_of=g["as_of"],
            universe_id=g["universe_id"],
            symbol=row["symbol"],
            sector_id=row["sector_id"],
            scores={"F_LOWVOL": row["lowvol_score"], "F_QUALITY": 55.0},
            loadings={"F_LOWVOL": 0.5},
            composite_score=55.0,
            dominant_factor="F_QUALITY",
            factor_confidence=0.7,
            hash="sha256:" + (("e02" + row["symbol"].lower()).ljust(64, "0")[:64]),
        )
    return out


def test_top_n_invvol_weights_and_caps():
    g = _golden()
    e10 = E10Service(flags=E10Flags())
    port = e10.run(
        as_of=g["as_of"],
        opinions=_opinions(g),
        exposures=_exposures(g),
        e14_state=_e14(g["as_of"]),
        top_n=8,
        sigma_overrides={r["symbol"]: r["sigma"] for r in g["symbols"]},
    )
    assert port.execution is False
    assert port.research_only is True
    assert "BEARCO" not in port.weights
    assert "LOWCO" not in port.weights
    assert len(port.weights) <= 8
    assert abs(sum(port.weights.values()) + port.cash_allocation - 1.0) < 1e-4
    assert all(w <= NAME_CAP + 1e-6 for w in port.weights.values())
    # Sector cap
    by_sec: dict[str, float] = {}
    for pos in port.target_positions:
        sec = pos.get("sector_id") or "?"
        by_sec[sec] = by_sec.get(sec, 0.0) + pos["weight"]
    assert all(v <= SECTOR_CAP + 1e-6 for v in by_sec.values())
    assert port.validation["ok"] is True
    assert port.validation["sum_to_one"] is True


def test_hard_derisk_cash_floor():
    g = _golden()
    e10 = E10Service()
    port = e10.run(
        as_of=g["as_of"],
        opinions=_opinions(g),
        exposures=_exposures(g),
        e14_state=_e14(g["as_of"], playbook="hard_derisk", risk_level="severe", size_mult=0.4, adj=0.5),
        sigma_overrides={r["symbol"]: r["sigma"] for r in g["symbols"]},
    )
    assert port.cash_allocation >= 0.30 - 1e-6
    assert port.gross <= 0.70 + 1e-3
    assert port.validation["ok"] is True


def test_name_cap_eight_percent():
    g = _golden()
    # Force tiny universe with identical low sigma → equal invvol would want large weights
    tiny = {
        "AAA": L4Opinion(
            as_of=g["as_of"],
            universe_id=g["universe_id"],
            symbol="AAA",
            label="Strong Bullish",
            composite_score=90,
            confidence=0.8,
            explanation={"summary": "x"},
            hash="sha256:" + ("1" * 64),
        ),
        "BBB": L4Opinion(
            as_of=g["as_of"],
            universe_id=g["universe_id"],
            symbol="BBB",
            label="Strong Bullish",
            composite_score=88,
            confidence=0.8,
            explanation={"summary": "x"},
            hash="sha256:" + ("2" * 64),
        ),
    }
    exps = {
        "AAA": E02Exposure(
            as_of=g["as_of"],
            universe_id=g["universe_id"],
            symbol="AAA",
            sector_id="IT",
            scores={"F_LOWVOL": 90},
            loadings={},
            composite_score=60,
            dominant_factor="F_LOWVOL",
            factor_confidence=0.7,
            hash="sha256:" + ("3" * 64),
        ),
        "BBB": E02Exposure(
            as_of=g["as_of"],
            universe_id=g["universe_id"],
            symbol="BBB",
            sector_id="ENERGY",
            scores={"F_LOWVOL": 90},
            loadings={},
            composite_score=60,
            dominant_factor="F_LOWVOL",
            factor_confidence=0.7,
            hash="sha256:" + ("4" * 64),
        ),
    }
    e10 = E10Service()
    port = e10.run(
        as_of=g["as_of"],
        opinions=tiny,
        exposures=exps,
        e14_state=_e14(g["as_of"], playbook="normal"),
        sigma_overrides={"AAA": 0.10, "BBB": 0.10},
    )
    assert all(w <= NAME_CAP + 1e-6 for w in port.weights.values())
    assert port.cash_allocation >= 1.0 - 2 * NAME_CAP - 1e-4


def test_engine_state_schema():
    g = _golden()
    e10 = E10Service()
    e10.run(
        as_of=g["as_of"],
        opinions=_opinions(g),
        exposures=_exposures(g),
        e14_state=_e14(g["as_of"]),
        sigma_overrides={r["symbol"]: r["sigma"] for r in g["symbols"]},
    )
    state = e10.get_state()
    assert state is not None
    payload = state.model_dump(mode="json")
    assert payload["engine"] == "E10"
    assert payload["confidence"]["method_version"] == "conf-1.0"
    assert "no_execution" in payload["warnings"]
    assert payload["metadata"]["execution"] is False
    assert validate_engine_state(payload) == []


def test_determinism():
    g = _golden()
    fixed = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
    kwargs = dict(
        as_of=g["as_of"],
        opinions=_opinions(g),
        exposures=_exposures(g),
        e14_state=_e14(g["as_of"]),
        sigma_overrides={r["symbol"]: r["sigma"] for r in g["symbols"]},
        generated_at=fixed,
    )
    a = E10Service().run(**kwargs)
    b = E10Service().run(**kwargs)
    assert a.weights == b.weights
    assert a.cash_allocation == b.cash_allocation
    assert a.hash == b.hash


def test_warm_cache_under_25ms():
    g = _golden()
    e10 = E10Service()
    e10.run(
        as_of=g["as_of"],
        opinions=_opinions(g),
        exposures=_exposures(g),
        e14_state=_e14(g["as_of"]),
        sigma_overrides={r["symbol"]: r["sigma"] for r in g["symbols"]},
    )
    for _ in range(30):
        t0 = time.perf_counter()
        port = e10.get_portfolio()
        assert port is not None
        assert (time.perf_counter() - t0) * 1000 < 25.0
    assert e10.metrics.snapshot()["cache_hits"] >= 30


def test_flags_and_no_execution():
    flags = E10Flags.from_settings()
    assert flags.e10_p0 is True
    assert flags.e10_optimizer is False
    assert flags.e10_hrp is False
    assert flags.e10_mvo is False
    health = E10Service().health()
    assert health["execution"] is False
    assert health["broker_integration"] is False
    assert health["order_routing"] is False
    assert health["market_data_access"] is False
    assert health["feature_snapshot_access"] is False


def test_history():
    g = _golden()
    e10 = E10Service()
    for day in ("2026-07-23", "2026-07-24"):
        e10.run(
            as_of=day,
            opinions=_opinions({**g, "as_of": day}),
            exposures=_exposures({**g, "as_of": day}),
            e14_state=_e14(day),
            sigma_overrides={r["symbol"]: r["sigma"] for r in g["symbols"]},
        )
    assert len(e10.history()) == 2


def test_orch_l4_ready():
    registry = FeatureRegistryService()
    ledger = OrchLedger()
    e14 = E14Service(registry, orch_ledger=ledger)
    e02 = E02Service(registry, orch_ledger=ledger)
    l4 = L4Service(e14=e14, e02=e02, orch_ledger=ledger)
    e10 = E10Service(l4=l4, e14=e14, e02=e02, orch_ledger=ledger)
    register_e10_with_orch(e10, l4)

    g = _golden()
    as_of = g["as_of"]
    e14.store.put(_e14(as_of))
    opinions = _opinions(g)
    exposures = _exposures(g)
    for sym, exp in exposures.items():
        # minimal state for e02 store
        e02.store.put(
            exp,
            EngineState.model_validate(
                {
                    "engine": "E02",
                    "version": "1.0.0",
                    "model_version": "e02-p0-factors-0.1.0",
                    "as_of": as_of,
                    "symbol": sym,
                    "score": {"raw": 55.0, "normalized_0_100": 55.0, "normalized_signed": 0.1, "unit": "score"},
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
        l4.store.put(
            opinions[sym],
            EngineState.model_validate(
                {
                    "engine": "L4",
                    "version": "1.0.0",
                    "model_version": "l4-shadow-vote-0.1.0",
                    "as_of": as_of,
                    "symbol": sym,
                    "score": {
                        "raw": opinions[sym].composite_score,
                        "normalized_0_100": opinions[sym].composite_score,
                        "normalized_signed": 0.2,
                        "unit": "score",
                    },
                    "confidence": {
                        "value": opinions[sym].confidence,
                        "components": {"C_coverage": 0.7, "C_freshness": 0.7, "C_model": 0.7},
                        "method_version": "conf-1.0",
                    },
                    "metadata": {"shadow": True, "label": opinions[sym].label},
                    "evidence": empty_evidence_pack(),
                    "explanation": {"summary": "x"},
                    "warnings": ["shadow_mode"],
                    "stale_inputs": [],
                    "input_hash": "sha256:" + ("3" * 64),
                    "hash": "sha256:" + ("4" * 64),
                    "timestamp_generated": datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc).isoformat(),
                }
            ),
        )

    out = e10.on_l4_ready(opinions)
    assert out is not None
    assert e10.get_portfolio() is not None
    assert e10.get_portfolio().execution is False
    assert abs(sum(out.weights.values()) + out.cash_allocation - 1.0) < 1e-4


@pytest.mark.asyncio
async def test_e10_api():
    from app.api import routes as api_routes

    g = _golden()
    api_routes._e10.run(
        as_of=g["as_of"],
        opinions=_opinions(g),
        exposures=_exposures(g),
        e14_state=_e14(g["as_of"]),
        sigma_overrides={r["symbol"]: r["sigma"] for r in g["symbols"]},
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/e10/health")
        assert health.status_code == 200
        body = health.json()
        assert body["engine"] == "E10"
        assert body["flags"]["E10_P0"] is True
        assert body["flags"]["E10_MVO"] is False
        assert body["execution"] is False
        port = await client.get("/v1/e10/portfolio")
        assert port.status_code == 200
        payload = port.json()
        assert payload["engine"] == "E10"
        assert payload["execution"] is False
        assert payload["validation"]["ok"] is True
        hist = await client.get("/v1/e10/history")
        assert hist.status_code == 200
        assert len(hist.json()) >= 1
        assert validate_engine_state(hist.json()[0]) == []
