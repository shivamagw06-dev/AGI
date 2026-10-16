"""Alpha Improvement Programme P0 — research programme (not a platform)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.aip.flags import AipFlags
from app.aip.models import ExperimentHypothesis, ExperimentRequest
from app.aip.service import AipService
from app.engines.l4.mapping import VOTER_WEIGHTS, WEIGHT_SET_ID
from app.main import app

FIXED = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)


def _svc(**kwargs) -> AipService:
    return AipService(flags=AipFlags(aip=True, aip_experiments=True, aip_promotion=False), **kwargs)


def test_roadmap_workstreams():
    road = _svc().roadmap()
    assert road["architecture_status"] == "v1.0.1 LOCKED"
    assert road["production_influence"] is False
    ids = [w["id"] for w in road["workstreams"]]
    assert ids == [f"AIP-{i:02d}" for i in range(1, 11)]
    assert "sharpe_delta" in road["validation_metrics"]
    assert "replay_superiority" in road["promotion_gates"]


def test_dynamic_weight_registry_shadow_only():
    svc = _svc()
    weights = svc.list_weights()
    ids = {w.weight_set_id for w in weights}
    assert WEIGHT_SET_ID in ids
    base = svc.get_weight(WEIGHT_SET_ID)
    assert base is not None
    assert base.baseline is True
    assert base.production is False
    assert base.shadow_only is True
    assert base.weights["E03"] == VOTER_WEIGHTS["E03"]

    with pytest.raises(ValueError, match="Cannot overwrite"):
        svc.register_weight(
            weight_set_id=WEIGHT_SET_ID,
            name="evil",
            weights={"E03": 1.0},
        )

    ws = svc.register_weight(
        weight_set_id="aip_test_candidate_v1",
        name="Test candidate",
        weights={"E03": 0.75, "E01": 0.15, "E14": 0.08, "E11": 0.02, "E02": 0.0},
        regime="RiskOn",
    )
    assert ws.production is False
    assert ws.shadow_only is True
    # Production L4 mapping unchanged
    assert VOTER_WEIGHTS["E03"] == 0.70


def test_experiment_framework_and_deltas():
    svc = _svc()
    result = svc.run_experiment(
        ExperimentRequest(
            hypothesis=ExperimentHypothesis(
                statement="Heavier E03 improves IC vs current L4",
                workstream="AIP-02",
                expected_effect="IC up, risk non-inferior",
            ),
            candidate_weight_set_id="aip_e03_heavier_v1",
            dataset_id="golden_p0_v1",
            name="unit-aip-experiment",
        ),
        generated_at=FIXED,
    )
    assert result.production_influence is False
    assert result.l4_remains_shadow is True
    assert result.promotion_ready is False
    assert result.replay_run_id
    assert result.cre_evaluation_id
    assert result.baseline_weight_set_id == WEIGHT_SET_ID
    assert result.hypothesis.statement
    assert result.significance.method == "paired_bootstrap_ic"
    assert result.rollback.rollback_to_weight_set_id == WEIGHT_SET_ID
    assert result.rollback.production_touched is False

    baselines = {c.baseline for c in result.comparisons}
    assert baselines == {
        "current_l4",
        "current_e03",
        "historical_replay",
        "golden_dataset",
        "paper_portfolio",
    }
    for cmp_ in result.comparisons:
        d = cmp_.deltas
        for field in (
            "sharpe_delta",
            "sortino_delta",
            "ic_delta",
            "hit_rate_delta",
            "calibration_delta",
            "max_drawdown_delta",
            "turnover_delta",
            "prediction_accuracy_delta",
        ):
            assert hasattr(d, field)

    assert result.contribution is not None
    engines = {e.engine for e in result.contribution.engines}
    assert "E03" in engines and "E01" in engines
    assert result.calibration is not None
    assert result.calibration.applied_to_production is False
    assert result.attribution is not None
    assert len(result.attribution.rows) > 0


def test_contribution_recommends_weight_direction():
    svc = _svc()
    out = svc.contribution("golden_p0_v1", generated_at=FIXED)
    assert "report" in out and "summary" in out
    assert out["report"]["production_influence"] is False
    engines = out["report"]["engines"]
    assert any(e["engine"] == "E03" for e in engines)
    assert "larger_weight" in out["summary"]


def test_house_view_evolution_and_quality():
    svc = _svc()
    evo = svc.house_view_evolution("TCS", generated_at=FIXED)
    assert evo["ticker"] == "TCS"
    assert evo["source"] == "replay_l4_shadow"
    assert isinstance(evo["points"], list)

    rq = svc.score_quality(
        {
            "domain": "research",
            "evidence_count": 5,
            "has_reasoning_package": True,
            "has_house_view": True,
            "contradiction_resolved": True,
        }
    )
    assert rq.domain == "research"
    assert rq.score > 0.5

    cq = svc.score_quality(
        {
            "domain": "client_answer",
            "grounded": True,
            "cites_evidence": True,
            "confidence_stated": True,
            "unknowns_stated": True,
            "answer_chars": 200,
        }
    )
    assert cq.domain == "client_answer"
    assert cq.score >= 0.8


def test_promotion_never_ready_when_flag_false():
    svc = _svc()
    svc.run_experiment(generated_at=FIXED)
    promo = svc.promotion()
    assert promo["promotion_flag"] is False
    assert promo["evidence_only"] is True
    assert promo["ready"] is False
    assert any("AIP_PROMOTION=false" in r for r in promo["blocking_reasons"])
    gates = {c["gate"] for c in promo["checklist"]}
    for required in (
        "replay_superiority",
        "cre_superiority",
        "statistical_significance",
        "risk_approval",
        "architecture_approval",
        "l4_remains_shadow",
    ):
        assert required in gates


def test_aip_disabled():
    svc = AipService(flags=AipFlags(aip=False, aip_experiments=True, aip_promotion=False))
    with pytest.raises(RuntimeError, match="AIP"):
        svc.run_experiment(generated_at=FIXED)


def test_experiments_disabled():
    svc = AipService(flags=AipFlags(aip=True, aip_experiments=False, aip_promotion=False))
    with pytest.raises(RuntimeError, match="AIP_EXPERIMENTS"):
        svc.run_experiment(generated_at=FIXED)


def test_deterministic_experiment_id():
    svc = _svc()
    req = ExperimentRequest(
        hypothesis=ExperimentHypothesis(
            statement="Determinism check",
            workstream="AIP-03",
            expected_effect="stable id",
        ),
        candidate_weight_set_id="aip_e03_heavier_v1",
        dataset_id="golden_p0_v1",
    )
    a = svc.run_experiment(req, generated_at=FIXED)
    b = svc.run_experiment(req, generated_at=FIXED)
    assert a.experiment_id == b.experiment_id


def test_no_l4_mapping_mutation_and_no_market_data_imports():
    import ast

    # Mapping constants unchanged after AIP operations
    before = dict(VOTER_WEIGHTS)
    svc = _svc()
    svc.run_experiment(generated_at=FIXED)
    assert dict(VOTER_WEIGHTS) == before
    assert WEIGHT_SET_ID == "l4_p0_shadow_voters_v1"

    root = Path(__file__).resolve().parents[1] / "app" / "aip"
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


@pytest.mark.asyncio
async def test_aip_api_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        h = await client.get("/v1/aip/health")
        assert h.status_code == 200
        body = h.json()
        assert body["l4_shadow"] is True
        assert body["production_influence"] is False
        assert body["flags"]["AIP_PROMOTION"] is False

        road = await client.get("/v1/aip/roadmap")
        assert road.status_code == 200
        assert len(road.json()["workstreams"]) == 10

        weights = await client.get("/v1/aip/weights")
        assert weights.status_code == 200
        assert weights.json()["l4_remains_shadow"] is True

        exp = await client.post(
            "/v1/aip/experiment",
            params={
                "candidate_weight_set_id": "aip_regime_risk_on_v1",
                "workstream": "AIP-04",
            },
        )
        assert exp.status_code == 200
        payload = exp.json()
        assert payload["l4_remains_shadow"] is True
        assert payload["promotion_ready"] is False
        eid = payload["experiment_id"]

        got = await client.get(f"/v1/aip/experiments/{eid}")
        assert got.status_code == 200

        contrib = await client.get("/v1/aip/contribution")
        assert contrib.status_code == 200

        promo = await client.get("/v1/aip/promotion")
        assert promo.status_code == 200
        assert promo.json()["ready"] is False

        dash = await client.get("/v1/aip/dashboard")
        assert dash.status_code == 200
        assert dash.json()["architecture_status"] == "v1.0.1 LOCKED"
        assert dash.json()["l4_shadow"] is True

        evo = await client.get("/v1/aip/house-view-evolution/INFY")
        assert evo.status_code == 200

        q = await client.post(
            "/v1/aip/quality",
            params={"domain": "research", "evidence_count": 3, "has_reasoning_package": True},
        )
        assert q.status_code == 200
        assert "score" in q.json()
