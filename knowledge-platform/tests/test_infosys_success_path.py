"""Sprint 6.1/6.2 success path: Yahoo Infosys → institutional CompanyProfile published."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.collectors.yahoo.collector import YahooCollector
from app.config.settings import Settings
from app.contracts.models import KnowledgeObjectType
from app.main import create_app
from app.pipeline.orchestrator import AcquisitionPipeline
from app.storage.db import KaipStore


INFY_DAY1 = {
    "yahoo_symbol": "INFY.NS",
    "as_of": "2026-07-27T10:00:00+00:00",
    "info": {
        "longName": "Infosys Limited",
        "shortName": "INFY",
        "sector": "Technology",
        "industry": "Information Technology Services",
        "currency": "INR",
        "exchange": "NSI",
        "website": "https://www.infosys.com",
        "marketCap": 6500000000000,
        "trailingPE": 24.1,
        "priceToBook": 7.2,
        "regularMarketPrice": 1550.0,
        "regularMarketVolume": 4200000,
        "revenueGrowth": 0.18,
        "earningsGrowth": 0.12,
    },
}

INFY_DAY2 = {
    "yahoo_symbol": "INFY.NS",
    "as_of": "2026-07-28T10:00:00+00:00",
    "info": {
        "longName": "Infosys Limited",
        "shortName": "INFY",
        "sector": "Technology",
        "industry": "Information Technology Services",
        "currency": "INR",
        "exchange": "NSI",
        "website": "https://www.infosys.com",
        "marketCap": 6550000000000,
        "trailingPE": 24.2,
        "priceToBook": 7.25,
        "regularMarketPrice": 1560.0,
        "regularMarketVolume": 4300000,
        "revenueGrowth": 0.28,
        "earningsGrowth": 0.15,
    },
}


def test_infosys_yahoo_to_published_company_profile(tmp_path: Path) -> None:
    db_path = tmp_path / "kaip.db"
    settings = Settings(
        db_path=db_path,
        scheduler_enabled=False,
        live_collectors_enabled=False,
        watchlist=("INFY",),
        pe_material_abs=1.0,
        revenue_growth_material_pp=5.0,
        price_material_pct=3.0,
        duplicate_window_seconds=0,
    )
    store = KaipStore(db_path)
    pipeline = AcquisitionPipeline(store, settings)

    c1 = YahooCollector(symbols=["INFY"], live=False, fixture_payloads={"INFY": INFY_DAY1})
    r1 = pipeline.run_collector(c1)
    assert len(r1.accepted) == 1
    assert any(ko.object_type == KnowledgeObjectType.COMPANY_PROFILE for ko in r1.knowledge_objects)
    profile = store.get_company_profile("INFY")
    assert profile is not None
    assert profile["knowledge"]["company"] == "Infosys Limited"
    assert profile["knowledge"]["business"]["sector"] == "Technology"
    assert "NIFTY50" in profile["entity_refs"]["indexes"]
    assert "marketCap" not in profile["knowledge"]
    assert "longName" not in profile["knowledge"]
    assert profile["metadata"]["source"] == "yahoo"

    c2 = YahooCollector(symbols=["INFY"], live=False, fixture_payloads={"INFY": INFY_DAY2})
    r2 = pipeline.run_collector(c2)
    assert len(r2.accepted) == 1
    learning_fields = {le.field_name for le in r2.learning_events}
    assert "revenue_growth" in learning_fields
    assert "pe_ratio" not in learning_fields
    assert "pe" not in learning_fields

    app = create_app(
        Settings(
            db_path=db_path,
            scheduler_enabled=False,
            live_collectors_enabled=False,
            watchlist=("INFY",),
        )
    )
    with TestClient(app) as client:
        resp = client.get("/v1/knowledge/company/INFY")
        assert resp.status_code == 200
        body = resp.json()
        assert body["object_type"] == "CompanyProfile"
        assert body["payload"]["company_symbol"] == "INFY"
        assert body["company_knowledge"]["Company"] in {"Infosys Limited", "Infosys Ltd", "Infosys"}

        market = client.get("/v1/knowledge/market/INFY")
        assert market.status_code == 200
        assert market.json()["payload"]["market_cap"] is not None

        learn = client.get("/v1/knowledge/learning/INFY")
        assert learn.status_code == 200
        fields = {item["field_name"] for item in learn.json()["items"]}
        assert "revenue_growth" in fields

    store.close()


def test_scheduler_is_finance_agnostic_registration() -> None:
    from app.scheduler.scheduler import AcquisitionScheduler

    calls: list[str] = []
    scheduler = AcquisitionScheduler()
    collector = YahooCollector(symbols=["INFY"], live=False, fixture_payloads={"INFY": INFY_DAY1})
    scheduler.register(collector, lambda: calls.append(collector.collector_id))
    jobs = scheduler.list_jobs()
    assert jobs[0]["job_id"] == "YahooCollector"
    assert jobs[0]["interval_seconds"] == 30
    scheduler.run_once("YahooCollector")
    assert calls == ["YahooCollector"]


def test_canonical_field_mapping() -> None:
    from app.collectors.base import checksum_payload
    from app.contracts.models import RawEvent, Source
    from app.normalizers.canonical import CanonicalNormalizer

    event = RawEvent(
        source=Source.YAHOO,
        collector_id="YahooCollector",
        endpoint="fixture",
        company_symbol="INFY",
        payload=INFY_DAY1,
        checksum=checksum_payload(INFY_DAY1),
    )
    items = CanonicalNormalizer().normalize(event)
    market = next(i for i in items if i["object_type"] == "MarketSnapshot")
    assert "market_cap" in market
    assert "marketCap" not in market
    assert market["pe_ratio"] == 24.1
