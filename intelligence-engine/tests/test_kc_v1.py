"""KCV1 — Knowledge Corpus populates/improves KF without redesign."""

from __future__ import annotations

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from app.aws.service import AwsService
from app.cre.service import CREService
from app.ioc.service import IocService
from app.irp.service import IrpService
from app.kc.service import KcService
from app.kc.universes import NIFTY_50, nifty50_tickers
from app.kf.service import KfService
from app.kf.store import KfStore
from app.kip.models import DocumentType, IngestRequest
from app.kip.service import KipService
from app.main import app
from app.rms.service import RmsService
from app.rsp.service import RspService
from app.ui.service import UiService
from app.validation.service import ValidationService


def _stack():
    kip = KipService()
    kip.ingest_agi(
        IngestRequest(
            title="India IT Services – Q1FY27 Review",
            content=(
                "Indian IT services face weak growth visibility. "
                "Bull case: GenAI deals. Bear case: US budget freezes. "
                "Theme: ai_adoption."
            ),
            tickers=["TCS", "INFY"],
            sectors=["Information Technology"],
            themes=["ai_adoption"],
            date=date(2026, 7, 24),
            article_id="kc_india_it",
            document_type=DocumentType.AGI_RESEARCH,
        )
    )
    kip.ingest_agi(
        IngestRequest(
            title="HUL Q1FY27 earnings results",
            content=(
                "Hindustan Unilever earnings: rural volume recovery, margin expansion. "
                "Guidance cautious. Revenue trend improving."
            ),
            tickers=["HINDUNILVR"],
            sectors=["FMCG"],
            date=date(2026, 7, 22),
            article_id="kc_hul_earnings",
            document_type=DocumentType.EARNINGS_TRANSCRIPT,
        )
    )
    kip.ingest_broker(
        IngestRequest(
            title="TCS broker note — Buy, target price Rs 4500",
            content=(
                "We upgrade TCS to Buy with target price Rs 4500. "
                "Investment thesis: large deal pipeline. Risks: pricing pressure."
            ),
            tickers=["TCS"],
            sectors=["Information Technology"],
            date=date(2026, 7, 21),
            article_id="kc_tcs_broker",
            document_type=DocumentType.BROKER_RESEARCH,
            broker="DemoBroker",
        )
    )
    store = KfStore()
    kf = KfService(kip=kip, store=store)
    kc = KcService(kf=kf, kip=kip)
    return kip, kf, kc


def test_universe_and_nifty50_coverage():
    _, kf, kc = _stack()
    uni = kc.ensure_universe()
    assert uni["nifty_50"] == len(NIFTY_50)
    assert uni["companies"] >= len(NIFTY_50)
    for t in nifty50_tickers():
        assert t in kf.store.companies


def test_populate_compounds_research_broker_earnings():
    _, kf, kc = _stack()
    result = kc.populate(rebuild_kip=True)
    assert result["documents"]["documents"] >= 3
    assert result["metrics"]["nifty_50_total"] == len(NIFTY_50)
    assert result["metrics"]["companies_covered"] >= len(NIFTY_50)

    tcs = kf.get_company("TCS")
    assert tcs["ticker"] == "TCS"
    # Broker structured knowledge should land in valuation / research
    blob = f"{tcs.get('valuation') or ''} {' '.join(tcs.get('related_research') or [])}".lower()
    assert "broker" in blob or "4500" in blob or "buy" in (tcs.get("valuation") or "").lower()

    hul = kf.get_company("HINDUNILVR")
    hist = " ".join(hul.get("financial_history") or []).lower()
    assert "earnings" in hist or "hul" in (hul.get("latest_thesis") or "").lower() or hul.get("related_research")


def test_gaps_quality_learning_and_consult():
    _, _, kc = _stack()
    kc.populate(rebuild_kip=True)
    gaps = kc.gaps()
    assert gaps["count"] >= 1
    assert any(t["kind"] for t in gaps["tasks"])

    quality = kc.quality(kind="company", key="TCS")
    assert quality["count"] >= 1
    assert 0 < quality["scores"][0]["overall_quality"] <= 1

    learning = kc.learning()
    assert learning["as_of"]
    assert learning["learned_today"]

    consult = kc.consult("Indian FMCG")
    assert consult["answer_policy"] == "knowledge_corpus_before_documents"
    assert consult["hits"]
    assert any(h["kind"] == "sector" and h["key"] == "fmcg" for h in consult["hits"])


def test_ask_agi_uses_knowledge_corpus_first():
    kip, kf, kc = _stack()
    kc.populate(rebuild_kip=True)
    rsp = RspService(kip=kip)
    irp = IrpService(kip=kip, rsp=rsp)
    rms = RmsService(kip=kip, rsp=rsp)
    aws = AwsService(kip=kip, rsp=rsp, rms=rms, cre=CREService(), validation=ValidationService())
    ioc = IocService(kip=kip, rsp=rsp, rms=rms, aws=aws, cre=CREService(), validation=ValidationService())
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
        kc=kc,
    )
    pack = ui.search("how is Indian IT services doing?")
    assert pack.knowledge_corpus.get("answer_policy") == "knowledge_corpus_before_documents"
    assert pack.knowledge_corpus.get("count", 0) >= 1 or pack.knowledge_foundation.get("count", 0) >= 1
    assert pack.workspace.get("primary_source_of_truth") == "knowledge_objects"


@pytest.mark.asyncio
async def test_kc_api_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/kc/health")
        assert health.status_code == 200
        body = health.json()
        assert body["programme"] == "KCV1"
        assert body["architecture_status"] == "v1.0.1 LOCKED"
        assert "kf" in " ".join(body.get("no_redesign") or []).lower() or "kf" in body.get("depends_on", [])

        uni = await client.post("/v1/kc/universe")
        assert uni.status_code == 200
        assert uni.json()["nifty_50"] == len(NIFTY_50)

        pop = await client.post("/v1/kc/populate", params={"rebuild_kip": False})
        assert pop.status_code == 200

        dash = await client.get("/v1/kc/dashboard")
        assert dash.status_code == 200
        assert "metrics" in dash.json()
        assert "gaps" in dash.json()

        consult = await client.get("/v1/kc/consult", params={"q": "Inflation"})
        assert consult.status_code == 200
        assert consult.json()["hits"]
