"""Sprint 8.3 — Historical Relationship Intelligence tests."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.config.settings import Settings
from app.contracts.models import (
    HistoricalRelationship,
    RelationshipConfidence,
    RelationshipDomain,
    RelationshipEvidence,
    RelationshipType,
)
from app.hri.engine import HistoricalRelationshipEngine
from app.hri.validation import validate_relationship
from app.main import create_app
from app.storage.db import HipStore
from app.timeline.builder import TimelineBuilder


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
    body = boot.json()
    assert body["relationship_count"] > 0
    assert body.get("relationships") is not None
    return client


def test_rejects_relationship_without_evidence() -> None:
    rel = HistoricalRelationship(
        domain=RelationshipDomain.MACRO,
        source_key="rbi_rate_cut",
        source_label="RBI Rate Cut",
        target_key="HDFCBANK",
        target_label="HDFC Bank",
        relationship_type=RelationshipType.POSITIVE_HISTORICAL_IMPACT,
        evidence=[],
    )
    errors = validate_relationship(rel)
    assert "evidence_required" in errors


def test_company_relationship_graph_infosys(tmp_path: Path) -> None:
    client = _bootstrapped_client(tmp_path)
    try:
        resp = client.get("/v1/history/relationships/company/INFY")
        assert resp.status_code == 200
        body = resp.json()
        assert body["providers_queried"] == []
        assert body["count"] > 0
        types = {r["relationship_type"] for r in body["relationships"]}
        assert "Competitor" in types or "Global Peer" in types or "Demand Driver" in types
        # Every published edge must carry evidence
        for r in body["relationships"]:
            assert r.get("evidence"), f"missing evidence on {r.get('relationship_id')}"
        assert body["graph"]["edges"]
    finally:
        client.__exit__(None, None, None)


def test_rbi_rate_cut_affects_hdfc_bank(tmp_path: Path) -> None:
    """Success path: How have RBI rate cuts historically affected HDFC Bank?"""
    client = _bootstrapped_client(tmp_path)
    try:
        resp = client.post(
            "/v1/history/relationships/explain",
            json={"source": "RBI Rate Cut", "target": "HDFCBANK"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["providers_queried"] == []
        assert body["relationships"]
        hit = body["relationships"][0]
        assert hit["relationship_type"] == "Positive Historical Impact"
        assert hit["confidence"] == "High"
        assert hit["occurrences"] >= 8
        assert hit["average_delay"] == "3 Trading Days"
        assert hit["evidence"]
        chains = body["transmission_chains"]
        assert chains
        path = chains[0]["path"]
        assert "RBI Rate Cut" in path
        assert "HDFC Bank" in path or "HDFCBANK" in path
        assert any("borrowing" in str(p).lower() or "lending" in str(p).lower() for p in path)
        bundle = body["bundle"]
        assert bundle["relationship_evidence"]
        assert bundle["historical_macro_cycles"]
    finally:
        client.__exit__(None, None, None)


def test_macro_and_market_relationship_apis(tmp_path: Path) -> None:
    client = _bootstrapped_client(tmp_path)
    try:
        macro = client.get("/v1/history/relationships/macro/rbi_rate_cut").json()
        assert macro["providers_queried"] == []
        assert macro["count"] > 0
        assert macro["transmission_chains"]

        crude = client.get("/v1/history/relationships/macro/higher_crude_oil").json()
        targets = {r["target_key"] for r in crude["relationships"]}
        assert "paints" in targets or "airlines" in targets or "omcs" in targets

        market = client.get("/v1/history/relationships/market").json()
        assert market["providers_queried"] == []
        assert market["count"] > 0

        sector = client.get("/v1/history/relationships/sector/information_technology").json()
        assert sector["providers_queried"] == []
        assert sector["count"] > 0
    finally:
        client.__exit__(None, None, None)


def test_relationships_versioned_and_immutable_hko(tmp_path: Path) -> None:
    settings = _settings(tmp_path, watchlist=("INFY",))
    store = HipStore(settings.db_path)
    TimelineBuilder(store).rebuild_all(["INFY"])
    engine = HistoricalRelationshipEngine(store)
    first = engine.rebuild_all(["INFY"])
    assert first["published"] > 0
    # Versions table grows; HKO object count unchanged by relationship rebuild
    before_objects = store.count_objects()
    second = engine.rebuild_all(["INFY"])
    assert second["published"] > 0
    assert store.count_objects() == before_objects
    versions = store._conn.execute("SELECT COUNT(*) AS c FROM relationship_versions").fetchone()["c"]
    assert versions > 0


def test_mission_control_relationship_board(tmp_path: Path) -> None:
    client = _bootstrapped_client(tmp_path)
    try:
        body = client.get("/v1/history/mission-control").json()
        assert body["principles"]["no_relationship_without_evidence"] is True
        board = body["relationship_board"]
        assert board["relationship_count"] > 0
        assert board["evidence_strength"] > 0
        assert board["confidence_distribution"]
        names = {t["name"] for t in body["retrieval_performance"]["traces"]}
        assert "historical_relationship_builder" in names or "relationship_publication" in names
    finally:
        client.__exit__(None, None, None)
