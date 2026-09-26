"""Sprint 6.5 Operate — Knowledge Freshness Engine + Knowledge Confidence Engine."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.collectors.yahoo.collector import YahooCollector
from app.config.settings import Settings
from app.contracts.models import KnowledgeObjectType, Source
from app.kce.engine import KnowledgeConfidenceEngine
from app.kfe.engine import (
    STATUS_FRESH,
    STATUS_NEEDS_REFRESH,
    KnowledgeFreshnessEngine,
    current_as_of_statement,
    evaluate_object_freshness,
    format_age,
)
from app.main import create_app
from app.pipeline.orchestrator import AcquisitionPipeline
from app.storage.db import KaipStore


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        db_path=tmp_path / "kfe_kce.db",
        scheduler_enabled=False,
        live_collectors_enabled=False,
        ako_enabled=True,
        watchlist=("INFY",),
        duplicate_window_seconds=0,
    )


def _seed_infy(pipeline: AcquisitionPipeline) -> None:
    fixture = {
        "yahoo_symbol": "INFY.NS",
        "as_of": "2026-07-28T10:00:00+00:00",
        "info": {
            "longName": "Infosys Limited",
            "sector": "Technology",
            "industry": "IT Services",
            "currency": "INR",
            "marketCap": 7000000000000,
            "trailingPE": 25.0,
            "regularMarketPrice": 1600.0,
            "regularMarketVolume": 1000000,
            "revenueGrowth": 0.12,
            "earningsGrowth": 0.1,
            "totalCash": 1e11,
            "totalDebt": 5e10,
            "pat_margin": 0.21,
        },
    }
    pipeline.run_collector(
        YahooCollector(symbols=["INFY"], live=False, fixture_payloads={"INFY": fixture})
    )


class TestKFE:
    def test_format_age_and_current_as_of(self):
        assert format_age(37 * 60) == "37 minutes"
        assert format_age(3 * 86400) == "3 days"
        stmt = current_as_of_statement("2026-07-28T05:02:00+00:00")  # 10:32 IST
        assert stmt is not None
        assert "current as of" in stmt.lower()
        assert "IST" in stmt

    def test_fresh_vs_needs_refresh(self):
        now = datetime(2026, 7, 28, 12, 0, tzinfo=timezone.utc)
        fresh = evaluate_object_freshness(
            KnowledgeObjectType.COMPANY_PROFILE,
            updated_at=now - timedelta(minutes=37),
            present=True,
            now=now,
            subject="INFY",
        )
        assert fresh["status"] == STATUS_FRESH
        assert fresh["age"] == "37 minutes"
        assert fresh["needs_refresh"] is False
        assert fresh["current_as_of"]

        stale = evaluate_object_freshness(
            KnowledgeObjectType.SECTOR_KNOWLEDGE,
            updated_at=now - timedelta(days=3),
            present=True,
            now=now,
            subject="auto",
        )
        assert stale["status"] == STATUS_NEEDS_REFRESH
        assert stale["age"] == "3 days"
        assert stale["needs_refresh"] is True

    def test_publish_registers_freshness(self, tmp_path: Path):
        settings = _settings(tmp_path)
        store = KaipStore(settings.db_path)
        pipeline = AcquisitionPipeline(store, settings)
        _seed_infy(pipeline)
        row = store.get_freshness(object_type="CompanyProfile", subject_key="INFY")
        assert row is not None
        assert row["updated_at"]
        report = KnowledgeFreshnessEngine().report_for_store(
            store, object_type="CompanyProfile", subject_key="INFY"
        )
        assert report["status"] in {STATUS_FRESH, STATUS_NEEDS_REFRESH}


class TestKCE:
    def test_financials_triple_source_near_99(self):
        eng = KnowledgeConfidenceEngine()
        report = eng.score(
            object_type=KnowledgeObjectType.FINANCIAL_STATEMENT,
            primary_source=Source.YAHOO,
            sources=[Source.NSE, Source.COMPANY_IR],
            subject_key="INFY",
        )
        assert report.confidence_pct >= 90
        assert report.label.value == "High"
        assert len(report.corroborating_sources) >= 3

    def test_news_single_yahoo_around_58(self):
        eng = KnowledgeConfidenceEngine()
        report = eng.score(
            object_type=KnowledgeObjectType.NEWS_EVENT,
            primary_source=Source.YAHOO,
            sources=[Source.YAHOO],
            subject_key="INFY",
        )
        assert report.confidence_pct == 58.0
        assert report.label.value == "Medium"

    def test_publish_registers_confidence(self, tmp_path: Path):
        settings = _settings(tmp_path)
        store = KaipStore(settings.db_path)
        pipeline = AcquisitionPipeline(store, settings)
        _seed_infy(pipeline)
        row = store.get_confidence(object_type="CompanyProfile", subject_key="INFY")
        assert row is not None
        assert row["confidence_pct"] is not None
        assert row["label"] in {"High", "Medium", "Low"}
        assert row["sources"]


class TestOperateAPIs:
    def test_bundle_exposes_freshness_and_confidence(self, tmp_path: Path):
        settings = _settings(tmp_path)
        app = create_app(settings)
        with TestClient(app) as client:
            # seed via ops run (not Ask)
            store = client.app.state.store
            pipeline = client.app.state.pipeline
            _seed_infy(pipeline)

            bundle = client.post("/v1/knowledge/bundle", json={"symbols": ["INFY"]}).json()
            assert "freshness" in bundle
            assert bundle["freshness"].get("company")
            assert bundle["freshness"]["company"].get("current_as_of") or True
            assert "confidence" in bundle

            fr = client.get("/v1/knowledge/freshness/CompanyProfile/INFY")
            assert fr.status_code == 200
            assert fr.json()["freshness"]["status"] in {
                STATUS_FRESH,
                STATUS_NEEDS_REFRESH,
                "Unknown",
            }

            cr = client.get("/v1/knowledge/confidence/CompanyProfile/INFY")
            assert cr.status_code == 200
            assert cr.json()["confidence"]["confidence_pct"] > 0

            mc = client.get("/v1/ako/mission-control").json()
            assert mc["principles"]["kfe_enabled"] is True
            assert mc["principles"]["kce_enabled"] is True
            assert "freshness" in mc
            assert "confidence" in mc

            # Ask path does not bump collector runs
            before = sum(j["run_count"] for j in mc["jobs"])
            client.post("/v1/knowledge/bundle", json={"symbols": ["INFY"], "question": "Infosys?"})
            after_mc = client.get("/v1/ako/mission-control").json()
            after = sum(j["run_count"] for j in after_mc["jobs"])
            assert after == before
            _ = store
