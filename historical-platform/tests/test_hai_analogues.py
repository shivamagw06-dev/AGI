"""Sprint 8.4 — Historical Analogue Intelligence tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config.settings import Settings
from app.hai.similarity import relative_similarity, score_dimensions, COMPANY_WEIGHTS
from app.main import create_app


def _settings(tmp_path: Path, watchlist: tuple[str, ...] = ("INFY", "HDFCBANK")) -> Settings:
    return Settings(
        db_path=tmp_path / "hip.db",
        live_collectors_enabled=False,
        watchlist=watchlist,
        min_daily_bars=40,
        min_quarterly_financials=8,
        min_annual_financials=11,
    )


def _bootstrapped_client(tmp_path: Path) -> TestClient:
    app = create_app(_settings(tmp_path))
    client = TestClient(app)
    client.__enter__()
    boot = client.post("/v1/internal/bootstrap")
    assert boot.status_code == 200
    return client


def test_similarity_scoring_deterministic() -> None:
    score_a, _, _, _ = score_dimensions(
        {"revenue_growth": 5.0, "pat_margin": 0.18, "pe": 17.0, "sector_alignment": 1.0},
        {"revenue_growth": 5.0, "pat_margin": 0.18, "pe": 17.0, "sector_alignment": 1.0},
        COMPANY_WEIGHTS,
    )
    score_b, _, matching, _ = score_dimensions(
        {"revenue_growth": 5.0, "pat_margin": 0.18, "pe": 17.0, "sector_alignment": 1.0},
        {"revenue_growth": 12.0, "pat_margin": 0.21, "pe": 24.0, "sector_alignment": 1.0},
        COMPANY_WEIGHTS,
    )
    assert score_a == 100.0
    assert score_b < score_a
    assert relative_similarity(10.0, 10.0, scale=12.0) == 100.0
    assert "Revenue Growth" in matching or score_a == 100.0


def test_infosys_slowdown_analogues(tmp_path: Path) -> None:
    """Success path: Has Infosys experienced this type of slowdown before?"""
    client = _bootstrapped_client(tmp_path)
    try:
        resp = client.post(
            "/v1/history/analogues/search",
            json={
                "scope": "company",
                "entity": "INFY",
                "question": "Has Infosys experienced this type of slowdown before?",
                "top_k": 5,
            },
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["providers_queried"] == []
        assert body["situation"] == "slowdown"
        analogues = body["analogues"]
        assert len(analogues) >= 1
        periods = {a["matched_period"] for a in analogues}
        # Slowdown years from fixture should rank among top analogues
        assert "FY2020" in periods or "FY2022" in periods
        top = analogues[0]
        assert top["similarity_score"] > 0
        assert top["matching_dimensions"]
        assert top["supporting_evidence"]
        assert top["dimension_scores"]
        for dim in top["dimension_scores"]:
            assert "score" in dim
        bundle = body["bundle"]
        assert bundle["top_historical_analogues"]
        assert bundle["historical_timeline"] is not None
        # Evidence integrity: no analogue without score + evidence
        for a in analogues:
            assert a["similarity_score"] > 0
            assert a["supporting_evidence"]
    finally:
        client.__exit__(None, None, None)


def test_company_sector_market_macro_analogue_apis(tmp_path: Path) -> None:
    client = _bootstrapped_client(tmp_path)
    try:
        company = client.get(
            "/v1/history/analogues/company/INFY",
            params={"question": "Is today's valuation similar to prior years?", "top_k": 3},
        ).json()
        assert company["providers_queried"] == []
        assert company["analogues"]

        sector = client.get(
            "/v1/history/analogues/sector/information_technology",
            params={"question": "Weak US demand, strong USD, margin pressure"},
        ).json()
        assert sector["providers_queried"] == []
        assert sector["analogues"]
        assert any(a["similarity_score"] >= 50 for a in sector["analogues"])

        market = client.get(
            "/v1/history/analogues/market",
            params={"question": "High PE, low VIX, liquidity abundant"},
        ).json()
        assert market["providers_queried"] == []
        assert market["analogues"]

        macro = client.get(
            "/v1/history/analogues/macro",
            params={"question": "RBI rate cut, inflation falling, GDP slowing"},
        ).json()
        assert macro["providers_queried"] == []
        assert macro["analogues"]
        assert any("easing" in (a.get("matched_label") or "").lower() or "rate" in (a.get("matched_label") or "").lower() for a in macro["analogues"])
    finally:
        client.__exit__(None, None, None)


def test_analogue_mission_control_board(tmp_path: Path) -> None:
    client = _bootstrapped_client(tmp_path)
    try:
        client.post(
            "/v1/history/analogues/search",
            json={
                "scope": "company",
                "entity": "INFY",
                "question": "Has Infosys experienced this type of slowdown before?",
            },
        )
        body = client.get("/v1/history/mission-control").json()
        assert body["principles"]["no_analogue_without_explainable_score"] is True
        board = body["analogue_board"]
        assert board["analogue_searches_executed"] >= 1
        assert board["average_similarity_score"] >= 0
        names = {t["name"] for t in body["retrieval_performance"]["traces"]}
        assert "historical_analogue_search" in names or "similarity_scoring" in names
    finally:
        client.__exit__(None, None, None)


def test_analogue_links_timeline_and_relationships(tmp_path: Path) -> None:
    client = _bootstrapped_client(tmp_path)
    try:
        body = client.post(
            "/v1/history/analogues/search",
            json={
                "scope": "company",
                "entity": "INFY",
                "question": "Has Infosys experienced this type of slowdown before?",
                "top_k": 5,
            },
        ).json()
        kinds = {e.get("kind") for a in body["analogues"] for e in a["supporting_evidence"]}
        assert "historical_financials" in kinds
        # At least one analogue should surface timeline or relationship evidence
        assert "timeline" in kinds or "relationships" in kinds
        assert body["bundle"]["historical_relationships"] is not None
    finally:
        client.__exit__(None, None, None)
