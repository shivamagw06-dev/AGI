"""KF1 — Knowledge Foundation V1 over KIP (no engine/KIP/IRP/RSP redesign)."""

from __future__ import annotations

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from app.aws.service import AwsService
from app.cre.service import CREService
from app.ioc.service import IocService
from app.irp.service import IrpService
from app.kf.catalogs import COMPANIES, MACROS, SECTORS, THEMES
from app.kf.merge import merge_list
from app.kf.scoring import confidence_score, freshness_score
from app.kf.service import KfService
from app.kf.store import KfStore
from app.kip.models import DocumentType, IngestRequest
from app.kip.service import KipService
from app.main import app
from app.rms.service import RmsService
from app.rsp.service import RspService
from app.ui.service import UiService
from app.validation.service import ValidationService


def _kip_with_research() -> KipService:
    kip = KipService()
    kip.ingest_agi(
        IngestRequest(
            title="India IT Services – Q1FY27 Review",
            content=(
                "The Indian IT services sector continues to face weak growth visibility. "
                "Revenue growth remained muted. Theme: ai_adoption. "
                "Bull case: GenAI large deals. Bear case: US budget freezes."
            ),
            tickers=["TCS", "INFY"],
            sectors=["Information Technology"],
            themes=["ai_adoption"],
            date=date(2026, 7, 24),
            article_id="kf_india_it",
            document_type=DocumentType.AGI_RESEARCH,
        )
    )
    kip.ingest_agi(
        IngestRequest(
            title="Indian FMCG rural recovery note",
            content=(
                "Rural demand is stabilising for Indian FMCG leaders. "
                "Volume growth improving for HUL and ITC. Theme: manufacturing."
            ),
            tickers=["HINDUNILVR", "ITC"],
            sectors=["FMCG"],
            themes=["manufacturing"],
            date=date(2026, 7, 20),
            article_id="kf_india_fmcg",
            document_type=DocumentType.AGI_RESEARCH,
        )
    )
    return kip


def test_seed_and_coverage_metrics():
    kf = KfService(kip=None, store=KfStore())
    seeded = kf.seed()
    assert seeded["seeded"]["companies"] == len(COMPANIES)
    assert seeded["seeded"]["sectors"] == len(SECTORS)
    cov = kf.coverage()
    assert cov["companies_covered"] >= len(COMPANIES)
    assert cov["sector_coverage"] == len(SECTORS)
    assert cov["theme_coverage"] == len(THEMES)
    assert cov["macro_coverage"] == len(MACROS)
    assert cov["avg_confidence"] > 0
    assert cov["avg_freshness"] > 0
    assert cov["relationship_count"] >= 0


def test_knowledge_search_prefers_objects_for_india_it_and_fmcg():
    kf = KfService(kip=None, store=KfStore())
    kf.seed()
    it = kf.search("how is Indian IT services doing?")
    assert it["answer_policy"] == "knowledge_objects_before_documents"
    assert it["hits"]
    assert any(h["kind"] == "sector" and h["key"] == "it_services" for h in it["hits"])

    fmcg = kf.search("Indian FMCG")
    assert fmcg["hits"]
    assert any(h["kind"] == "sector" and h["key"] == "fmcg" for h in fmcg["hits"])


def test_ingest_extracts_and_merges_without_duplicates():
    kip = _kip_with_research()
    store = KfStore()
    kf = KfService(kip=kip, store=store)
    kf.seed()
    docs = list(kip.store.documents.values())
    assert docs
    for doc in docs:
        assert kf.on_document(doc)["accepted"] is True

    # Re-ingest same docs should reduce duplicates, not create parallel objects
    before_companies = len(store.companies)
    before_extracts = len(store.extracts)
    for doc in docs:
        kf.on_document(doc)
    assert len(store.companies) == before_companies
    assert len(store.extracts) == before_extracts
    assert store.duplicate_reductions >= 1

    tcs = kf.get_company("TCS")
    assert tcs["ticker"] == "TCS"
    assert tcs["meta"]["version"] >= 1
    assert tcs["related_research"] or tcs["latest_thesis"]

    sector = kf.get_sector("it_services")
    assert sector["sector_id"] == "it_services"
    assert sector["major_companies"]


def test_confidence_and_freshness_scoring():
    conf = confidence_score(
        has_thesis=True,
        n_sources=3,
        source_reliability=0.95,
        n_structured_fields=4,
        has_house_view=True,
        has_predictions=True,
    )
    assert 0.5 <= conf <= 0.98
    fresh = freshness_score(None)
    assert 0 < fresh <= 1
    assert merge_list(["a", "b"], ["b", "c"]) == ["a", "b", "c"]


def test_ask_agi_attaches_knowledge_foundation():
    kip = _kip_with_research()
    rsp = RspService(kip=kip)
    irp = IrpService(kip=kip, rsp=rsp)
    rms = RmsService(kip=kip, rsp=rsp)
    aws = AwsService(kip=kip, rsp=rsp, rms=rms, cre=CREService(), validation=ValidationService())
    ioc = IocService(kip=kip, rsp=rsp, rms=rms, aws=aws, cre=CREService(), validation=ValidationService())
    kf = KfService(kip=kip)
    for doc in kip.store.documents.values():
        kf.on_document(doc)
    ui = UiService(
        aws=aws,
        ioc=ioc,
        kip=kip,
        rsp=rsp,
        rms=rms,
        cre=CREService(),
        validation=ValidationService(),
        irp=irp,
        kf=kf,
    )
    pack = ui.search("Indian FMCG")
    assert pack.knowledge_foundation.get("answer_policy") == "knowledge_objects_before_documents"
    assert pack.knowledge_foundation.get("count", 0) >= 1
    kinds = {h.get("kind") for h in pack.knowledge_foundation.get("hits") or []}
    assert "sector" in kinds or "company" in kinds


@pytest.mark.asyncio
async def test_kf_api_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/kf/health")
        assert health.status_code == 200
        body = health.json()
        assert body["programme"] == "KF1"
        assert body["architecture_status"] == "v1.0.1 LOCKED"
        assert body["flags"]["KF"] is True

        cov = await client.get("/v1/kf/coverage")
        assert cov.status_code == 200
        assert cov.json()["companies_covered"] > 0

        search = await client.get("/v1/kf/search", params={"q": "Indian FMCG"})
        assert search.status_code == 200
        assert search.json()["hits"]

        sectors = await client.get("/v1/kf/sectors")
        assert sectors.status_code == 200
        assert any(s["sector_id"] == "fmcg" for s in sectors.json()["sectors"])

        company = await client.get("/v1/kf/company/TCS")
        assert company.status_code == 200
        assert company.json()["ticker"] == "TCS"
