"""IRP V1 — Institutional Reasoning Pipeline above KIP/RSP, below Ask AGI."""

from __future__ import annotations

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from app.aws.service import AwsService
from app.cre.service import CREService
from app.ioc.service import IocService
from app.irp.domain import classify_domain
from app.irp.entities import resolve_entities
from app.irp.intent import detect_intent
from app.irp.service import IrpService
from app.kip.models import DocumentType, IngestRequest
from app.kip.service import KipService
from app.main import app
from app.rms.service import RmsService
from app.rsp.service import RspService
from app.ui.service import UiService
from app.validation.service import ValidationService


def _kip_with_india_it() -> KipService:
    kip = KipService()
    kip.ingest_agi(
        IngestRequest(
            title="India IT Sector update",
            content=(
                "India IT Services – Q1FY27 Review & Outlook. "
                "The Indian IT services sector continues to face weak growth visibility, "
                "with earnings reflecting ongoing macro challenges, slower deal conversions, "
                "and increasing pressure from AI-led productivity demands. "
                "Revenue growth remained muted at around 0% QoQ. "
                "Sector: Information Technology\nTheme: ai_adoption\n"
            ),
            tickers=["TCS", "INFY"],
            sectors=["Information Technology"],
            themes=["ai_adoption"],
            date=date(2026, 7, 24),
            article_id="irp_india_it",
            document_type=DocumentType.AGI_RESEARCH,
        )
    )
    return kip


def test_intent_and_entity_resolution_for_india_it():
    intent = detect_intent("how is Indian IT services doing?")
    assert intent == "sector_research"
    ents = resolve_entities("how is Indian IT services doing?")
    assert ents.sector_key == "INDIA_IT"
    assert "TCS" in ents.tickers
    assert "INFY" in ents.tickers
    assert "ai_adoption" in ents.themes or "cloud" in ents.themes or ents.themes
    assert classify_domain(intent, ents) == "sector"


def test_irp_pipeline_thinks_before_answer():
    kip = _kip_with_india_it()
    rsp = RspService(kip=kip)
    irp = IrpService(kip=kip, rsp=rsp)
    pkg = irp.run("how is Indian IT services doing?")
    assert pkg.intent == "sector_research"
    assert pkg.domain == "sector"
    assert pkg.entities.sector_key == "INDIA_IT"
    assert pkg.research_plan and pkg.research_plan.steps
    assert pkg.reasoning.stance in {"Bearish", "Neutral"}
    assert pkg.reasoning.company_leaders
    assert pkg.reasoning.key_drivers or pkg.reasoning.macro_drivers
    assert pkg.institutional_briefing.get("current_outlook")
    assert pkg.sector_intelligence.get("top_companies")
    assert pkg.validation.answered_question is True
    # Must not invent unrelated names in leaders
    leaders = " ".join(pkg.reasoning.company_leaders).upper()
    assert "PAYTM" not in leaders
    assert "TCS" in leaders


def test_ask_agi_uses_irp_briefing():
    kip = _kip_with_india_it()
    rsp = RspService(kip=kip)
    irp = IrpService(kip=kip, rsp=rsp)
    rms = RmsService(kip=kip, rsp=rsp)
    aws = AwsService(kip=kip, rsp=rsp, rms=rms, cre=CREService(), validation=ValidationService())
    ioc = IocService(kip=kip, rsp=rsp, rms=rms, aws=aws, cre=CREService(), validation=ValidationService())
    ui = UiService(aws=aws, ioc=ioc, kip=kip, rsp=rsp, rms=rms, cre=CREService(), validation=ValidationService(), irp=irp)
    pack = ui.search("how is Indian IT services doing?")
    assert pack.workspace.get("programme") == "IRP V1"
    assert pack.irp.get("intent") == "sector_research"
    assert pack.sector_intelligence.get("sector_overview")
    assert pack.company_leaders
    assert pack.current_outlook
    assert pack.house_view_card.get("stance") in {"Bearish", "Neutral"}
    assert "document_id" not in (pack.executive_summary or "")
    titles = " ".join(str(i.get("title") or "") for i in (pack.supporting_evidence or []))
    assert "India IT" in titles or "IT Services" in titles or pack.supporting_evidence


@pytest.mark.asyncio
async def test_irp_api_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/irp/health")
        assert health.status_code == 200
        body = health.json()
        assert body["programme"] == "IRP V1"
        assert body["architecture_status"] == "v1.0.1 LOCKED"

        run = await client.post(
            "/v1/irp/run",
            params={"question": "how is Indian IT services doing?"},
        )
        assert run.status_code == 200
        payload = run.json()
        assert payload["intent"] == "sector_research"
        assert payload["entities"]["sector_key"] == "INDIA_IT"
