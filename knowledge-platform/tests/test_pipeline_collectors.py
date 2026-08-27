"""Collector → validation → KO coverage for Sprint 6.1 sources."""

from __future__ import annotations

from pathlib import Path

from app.collectors.bse.corporate_actions import BSECorporateActionCollector
from app.collectors.company_ir.collector import CompanyIRCollector
from app.collectors.nse.announcements import NSEAnnouncementCollector
from app.collectors.nse.bhavcopy import NSEBhavcopyCollector
from app.config.settings import Settings
from app.contracts.models import KnowledgeObjectType
from app.pipeline.orchestrator import AcquisitionPipeline
from app.storage.db import KaipStore


def _pipeline(tmp_path: Path) -> AcquisitionPipeline:
    settings = Settings(
        db_path=tmp_path / "kaip.db",
        scheduler_enabled=False,
        live_collectors_enabled=False,
        watchlist=("INFY",),
    )
    return AcquisitionPipeline(KaipStore(settings.db_path), settings)


def test_nse_announcement_becomes_corporate_event(tmp_path: Path) -> None:
    pipeline = _pipeline(tmp_path)
    collector = NSEAnnouncementCollector(
        symbols=["INFY"],
        live=False,
        fixture_payloads=[
            {
                "symbol": "INFY",
                "desc": "Board Meeting",
                "attchmntText": "Outcome of Board Meeting",
                "an_dt": "28-Jul-2026",
                "attchmntFile": "https://archives.nseindia.com/corporate/INFY.pdf",
            }
        ],
    )
    result = pipeline.run_collector(collector)
    assert len(result.accepted) == 1
    assert any(ko.object_type == KnowledgeObjectType.CORPORATE_EVENT for ko in result.knowledge_objects)
    assert any(le.field_name == "object_created" for le in result.learning_events)


def test_bhavcopy_becomes_market_snapshot(tmp_path: Path) -> None:
    pipeline = _pipeline(tmp_path)
    collector = NSEBhavcopyCollector(
        symbols=["INFY"],
        live=False,
        fixture_rows=[{"symbol": "INFY", "CLOSE": 1555.5, "TTL_TRD_QNTY": 1000000}],
    )
    result = pipeline.run_collector(collector)
    assert any(ko.object_type == KnowledgeObjectType.MARKET_SNAPSHOT for ko in result.knowledge_objects)
    snap = pipeline.store.get_latest_market("INFY")
    assert snap is not None
    assert snap["payload"]["last_price"] == 1555.5


def test_bse_corporate_action(tmp_path: Path) -> None:
    pipeline = _pipeline(tmp_path)
    collector = BSECorporateActionCollector(
        symbols=["INFY"],
        live=False,
        fixture_rows=[
            {
                "company_symbol": "INFY",
                "action_type": "Dividend",
                "ex_date": "2026-08-01",
                "record_date": "2026-08-02",
                "amount": 20.0,
            }
        ],
    )
    result = pipeline.run_collector(collector)
    assert any(ko.object_type == KnowledgeObjectType.CORPORATE_ACTION for ko in result.knowledge_objects)


def test_company_ir_event(tmp_path: Path) -> None:
    pipeline = _pipeline(tmp_path)
    collector = CompanyIRCollector(
        symbols=["INFY"],
        live=False,
        fixture_payloads={
            "INFY": {
                "company_symbol": "INFY",
                "ir_url": "https://www.infosys.com/investors.html",
                "event_title": "Annual Report FY26",
                "documents": [{"url": "https://www.infosys.com/investors/reports/ar.pdf"}],
            }
        },
    )
    result = pipeline.run_collector(collector)
    assert len(result.accepted) == 1
    events = pipeline.store.list_events("INFY")
    assert events


def test_duplicate_raw_event_not_republished(tmp_path: Path) -> None:
    pipeline = _pipeline(tmp_path)
    collector = NSEAnnouncementCollector(
        symbols=["INFY"],
        live=False,
        fixture_payloads=[
            {
                "symbol": "INFY",
                "desc": "Board Meeting",
                "subject": "Outcome",
                "attchmntFile": "https://archives.nseindia.com/corporate/INFY.pdf",
            }
        ],
    )
    r1 = pipeline.run_collector(collector)
    r2 = pipeline.run_collector(collector)
    assert len(r1.accepted) == 1
    assert len(r2.duplicates) == 1
    assert r2.knowledge_objects == []
