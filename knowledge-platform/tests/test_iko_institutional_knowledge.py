"""Sprint 6.2 — Institutional Knowledge Objects: what AGI learns."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.collectors.yahoo.collector import YahooCollector
from app.config.settings import Settings
from app.contracts.iko import company_knowledge_view
from app.contracts.models import KnowledgeObjectType, Source
from app.main import create_app
from app.pipeline.orchestrator import AcquisitionPipeline
from app.storage.db import KaipStore

INFY_YAHOO = {
    "yahoo_symbol": "INFY.NS",
    "as_of": "2026-07-28T09:30:00+00:00",
    "info": {
        "longName": "Infosys",
        "sector": "Technology",
        "industry": "Information Technology Services",
        "currency": "INR",
        "marketCap": 8100000000000,
        "trailingPE": 25.3,
        "priceToBook": 7.1,
        "regularMarketPrice": 1600.0,
        "regularMarketVolume": 5000000,
        "revenueGrowth": 0.19,
        "earningsGrowth": 0.11,
        "fiftyTwoWeekLow": 1200.0,
        "fiftyTwoWeekHigh": 1900.0,
    },
}

INFY_YAHOO_V2 = {
    **INFY_YAHOO,
    "as_of": "2026-07-28T15:30:00+00:00",
    "info": {
        **INFY_YAHOO["info"],
        "trailingPE": 25.4,  # immaterial
        "revenueGrowth": 0.28,  # material → LearningEvent
        "regularMarketPrice": 1605.0,
    },
}


def _pipeline(tmp_path: Path) -> AcquisitionPipeline:
    settings = Settings(
        db_path=tmp_path / "kaip.db",
        scheduler_enabled=False,
        live_collectors_enabled=False,
        watchlist=("INFY",),
        pe_material_abs=1.0,
        revenue_growth_material_pp=5.0,
        duplicate_window_seconds=0,
    )
    return AcquisitionPipeline(KaipStore(settings.db_path), settings)


def test_yahoo_becomes_institutional_company_knowledge_not_json(tmp_path: Path) -> None:
    pipeline = _pipeline(tmp_path)
    result = pipeline.run_collector(
        YahooCollector(symbols=["INFY"], live=False, fixture_payloads={"INFY": INFY_YAHOO})
    )
    profiles = [ko for ko in result.knowledge_objects if ko.object_type == KnowledgeObjectType.COMPANY_PROFILE]
    assert len(profiles) == 1
    ko = profiles[0]
    knowledge = ko.knowledge

    # Institutional sections — not provider JSON
    assert knowledge["company"] == "Infosys"
    assert knowledge["business"]["sector"] == "Technology"
    assert knowledge["valuation"]["pe"] == 25.3
    assert knowledge["growth"]["revenue_growth_pct"] == 19.0
    assert "marketCap" not in knowledge
    assert "trailingPE" not in knowledge
    assert "revenueGrowth" not in knowledge

    # Metadata required
    assert ko.metadata.source == Source.YAHOO
    assert ko.metadata.confidence.value == "High"
    assert ko.metadata.verified is True
    assert ko.version == 1

    view = company_knowledge_view(knowledge, source=Source.YAHOO, version=1)
    ck = view["CompanyKnowledge"]
    assert ck["Company"] == "Infosys"
    assert ck["Valuation"]["PE"] == 25.3
    assert ck["Business"]["Sector"] == "Technology"
    assert ck["Growth"]["Revenue Growth"] == "19.0%"
    assert ck["Source"] == "Yahoo"


def test_versions_never_overwrite(tmp_path: Path) -> None:
    pipeline = _pipeline(tmp_path)
    pipeline.run_collector(
        YahooCollector(symbols=["INFY"], live=False, fixture_payloads={"INFY": INFY_YAHOO})
    )
    pipeline.run_collector(
        YahooCollector(symbols=["INFY"], live=False, fixture_payloads={"INFY": INFY_YAHOO_V2})
    )
    versions = pipeline.store.list_versions(KnowledgeObjectType.COMPANY_PROFILE, "INFY")
    assert [v["version"] for v in versions] == [1, 2]
    assert versions[1]["previous_object_id"] == versions[0]["object_id"]
    assert versions[1]["changed_fields"]


def test_learning_event_is_institutional(tmp_path: Path) -> None:
    pipeline = _pipeline(tmp_path)
    pipeline.run_collector(
        YahooCollector(symbols=["INFY"], live=False, fixture_payloads={"INFY": INFY_YAHOO})
    )
    r2 = pipeline.run_collector(
        YahooCollector(symbols=["INFY"], live=False, fixture_payloads={"INFY": INFY_YAHOO_V2})
    )
    financial = [le for le in r2.learning_events if le.field_name == "revenue_growth"]
    assert financial
    le = financial[0]
    assert le.category.value == "Financial"
    assert le.importance.value == "High"
    assert "Revenue acceleration" in le.reason or "accelerat" in le.reason.lower()
    assert set(le.affected) >= {"Company", "Sector", "Valuation"}
    assert not any(le.field_name == "pe_ratio" for le in r2.learning_events)
    assert not any(le.field_name == "pe" for le in r2.learning_events)


def test_relationships_auto_connect(tmp_path: Path) -> None:
    pipeline = _pipeline(tmp_path)
    pipeline.run_collector(
        YahooCollector(symbols=["INFY"], live=False, fixture_payloads={"INFY": INFY_YAHOO})
    )
    edges = pipeline.store.list_relationships("Company", "INFY")
    edge_types = {(e["edge_type"], e["to_type"], e["to_key"]) for e in edges}
    assert ("IN_SECTOR", "Sector", "Technology") in edge_types
    assert ("IN_INDUSTRY", "Industry", "Information Technology Services") in edge_types or any(
        e["edge_type"] == "IN_INDUSTRY" for e in edges
    )
    assert any(e["edge_type"] == "IN_INDEX" and e["to_key"] == "NIFTY50" for e in edges)
    assert any(e["edge_type"] == "PEER_OF" for e in edges)

    sector = pipeline.store.get_sector_knowledge("technology")
    assert sector is not None
    assert "INFY" in sector["knowledge"]["leaders"]


def test_publication_envelope_layers(tmp_path: Path) -> None:
    pipeline = _pipeline(tmp_path)
    result = pipeline.run_collector(
        YahooCollector(symbols=["INFY"], live=False, fixture_payloads={"INFY": INFY_YAHOO})
    )
    assert result.published is not None
    assert result.published.envelope is not None
    env = result.published.envelope
    assert env.company_knowledge
    assert env.sector_knowledge
    assert env.evidence_graph_ready is True
    assert env.institutional_memory_ready is True


def test_api_returns_company_knowledge(tmp_path: Path) -> None:
    db_path = tmp_path / "kaip.db"
    pipeline = AcquisitionPipeline(
        KaipStore(db_path),
        Settings(
            db_path=db_path,
            scheduler_enabled=False,
            live_collectors_enabled=False,
            watchlist=("INFY",),
            duplicate_window_seconds=0,
        ),
    )
    pipeline.run_collector(
        YahooCollector(symbols=["INFY"], live=False, fixture_payloads={"INFY": INFY_YAHOO})
    )
    pipeline.store.close()

    app = create_app(
        Settings(db_path=db_path, scheduler_enabled=False, live_collectors_enabled=False, watchlist=("INFY",))
    )
    with TestClient(app) as client:
        resp = client.get("/v1/knowledge/company/INFY")
        assert resp.status_code == 200
        body = resp.json()
        assert body["company_knowledge"]["Company"] == "Infosys"
        assert body["company_knowledge"]["Valuation"]["PE"] == 25.3
        assert body["metadata"]["source"] == "yahoo"
        assert body["knowledge"]["growth"]["revenue_growth_pct"] == 19.0

        rel = client.get("/v1/knowledge/relationships/INFY")
        assert rel.status_code == 200
        assert rel.json()["edges"]

        sector = client.get("/v1/knowledge/sector/technology")
        assert sector.status_code == 200
