"""Continuous Research Evaluation P0 — CRE-001–005."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from httpx import ASGITransport, AsyncClient

from app.cre.flags import CREFlags
from app.cre.service import CREService
from app.main import app


FIXED = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)


def test_daily_evaluation_runner():
    svc = CREService(flags=CREFlags(cre=True, promotion=False))
    result = svc.evaluate("golden_p0_v1", generated_at=FIXED)
    assert result.production_influence is False
    assert result.flags["CRE"] is True
    assert result.flags["PROMOTION"] is False
    assert result.dataset_id == "golden_p0_v1"
    assert result.replay_run_id
    assert len(result.engine_scorecards) == 12
    assert result.composite is not None
    assert result.composite.promotion_ready is False
    assert result.promotion is not None
    assert result.promotion.ready is False
    assert result.promotion.evidence_only is True
    assert result.dashboard
    assert "engine_rankings" in result.dashboard
    assert "trend_charts" in result.dashboard
    assert "promotion_readiness" in result.dashboard


def test_rolling_windows_adaptive_days_used():
    svc = CREService()
    result = svc.evaluate("golden_p0_v1", generated_at=FIXED)
    card = next(c for c in result.engine_scorecards if c.engine == "L4")
    for w in ("30", "90", "252"):
        assert w in card.rolling
        m = card.rolling[w]
        assert m.window == int(w)
        assert m.days_used == 5  # golden dataset length
        assert m.days_used < m.window


def test_metrics_present_on_scorecards():
    svc = CREService()
    result = svc.evaluate("golden_p0_v1", generated_at=FIXED)
    m = result.engine_scorecards[0].rolling["30"]
    # Fields required by mission (may be None on short series)
    for field in (
        "information_coefficient",
        "calibration_error",
        "brier_score",
        "precision",
        "recall",
        "hit_rate",
        "sharpe",
        "sortino",
        "max_drawdown",
        "turnover",
        "average_confidence",
        "schema_stability",
        "parity_stability",
    ):
        assert hasattr(m, field)


def test_drift_and_regression_alerts_emitted():
    svc = CREService()
    result = svc.evaluate("golden_p0_v1", generated_at=FIXED)
    # Short-window info alert always present for golden_p0_v1 (5 days)
    kinds = {a.kind for a in result.drift_alerts}
    assert "model" in kinds or any(a.alert_id == "drift-info-short-window" for a in result.drift_alerts)
    assert isinstance(result.regression_alerts, list)


def test_promotion_never_ready_when_flag_false():
    svc = CREService(flags=CREFlags(cre=True, promotion=False))
    result = svc.evaluate("golden_p0_v1", generated_at=FIXED)
    assert result.promotion is not None
    assert result.promotion.promotion_flag is False
    assert result.promotion.ready is False
    assert "PROMOTION=false" in " ".join(result.promotion.blocking_reasons)


def test_version_and_formula_aware():
    svc = CREService()
    result = svc.evaluate("golden_p0_v1", generated_at=FIXED)
    engines = {c.engine: c for c in result.engine_scorecards}
    assert engines["E03"].model_version
    assert "SM_AGI_TECH" in engines["E03"].formula_versions
    assert result.promotion is not None
    assert "E10" in result.promotion.engine_versions
    assert "SM_AGI_TECH" in result.promotion.formula_versions


def test_deterministic_evaluation():
    svc = CREService()
    a = svc.evaluate("golden_p0_v1", generated_at=FIXED)
    b = svc.evaluate("golden_p0_v1", generated_at=FIXED)
    assert a.evaluation_id == b.evaluation_id
    assert [c.rank_score for c in a.engine_scorecards] == [c.rank_score for c in b.engine_scorecards]
    assert a.composite.ranking == b.composite.ranking
    assert [x.alert_id for x in a.drift_alerts] == [x.alert_id for x in b.drift_alerts]


def test_cre_disabled():
    svc = CREService(flags=CREFlags(cre=False, promotion=False))
    with pytest.raises(RuntimeError, match="CRE"):
        svc.evaluate("golden_p0_v1")


def test_no_market_data_imports():
    import ast
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "app" / "cre"
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


def test_store_and_facade_reads():
    svc = CREService()
    result = svc.evaluate("golden_p0_v1", generated_at=FIXED)
    assert svc.latest() is not None
    assert svc.get_evaluation(result.evaluation_id) is not None
    assert svc.get_scorecard("L4") is not None
    assert svc.get_composite() is not None
    alerts = svc.get_alerts()
    assert "drift" in alerts and "regression" in alerts
    assert svc.get_promotion() is not None
    dash = svc.get_dashboard()
    assert dash is not None
    assert dash["promotion_readiness"]["ready"] is False
    health = svc.health()
    assert health["ok"] is True
    assert health["production_influence"] is False
    assert health["flags"]["CRE"] is True
    assert health["flags"]["PROMOTION"] is False


@pytest.mark.asyncio
async def test_cre_api():
    from app.api import routes as api_routes

    api_routes._cre = CREService()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/cre/health")
        assert health.status_code == 200
        body = health.json()
        assert body["platform"] == "CRE"
        assert body["flags"]["CRE"] is True
        assert body["flags"]["PROMOTION"] is False

        eval_resp = await client.post("/v1/cre/evaluate", params={"dataset_id": "golden_p0_v1"})
        assert eval_resp.status_code == 200
        payload = eval_resp.json()
        assert payload["production_influence"] is False
        assert len(payload["engine_scorecards"]) == 12

        cards = await client.get("/v1/cre/scorecards")
        assert cards.status_code == 200
        assert cards.json()["composite"] is not None

        l4 = await client.get("/v1/cre/scorecards/L4")
        assert l4.status_code == 200
        assert l4.json()["engine"] == "L4"

        alerts = await client.get("/v1/cre/alerts")
        assert alerts.status_code == 200

        promo = await client.get("/v1/cre/promotion")
        assert promo.status_code == 200
        assert promo.json()["ready"] is False

        dash = await client.get("/v1/cre/dashboard")
        assert dash.status_code == 200
        assert "engine_rankings" in dash.json()
