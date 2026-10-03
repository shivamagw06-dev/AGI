"""UI Aggregation Layer P0 — client facade over Investment Office platforms."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.aws.service import AwsService
from app.cre.service import CREService
from app.ioc.service import IocService
from app.kip.models import DocumentType, IngestRequest
from app.kip.service import KipService
from app.main import app
from app.rms.models import ResearchRequestCreate
from app.rms.service import RmsService
from app.rsp.service import RspService
from app.ui.flags import UiFlags
from app.ui.sanitize import public_label, scrub_text
from app.ui.service import UiService
from app.validation.service import ValidationService
from datetime import date


def _stack() -> UiService:
    kip = KipService()
    kip.ingest_agi(
        IngestRequest(
            title="AGI ICICI house view",
            content=(
                "ICICIBANK Investment Thesis preferred private bank.\n"
                "Target price Rs 1400.\nBull Case\n- Growth\nBear Case\n- Stress\n"
                "Theme: credit_growth\nSector: Financials\n"
            ),
            tickers=["ICICIBANK"],
            themes=["credit_growth"],
            sectors=["Financials"],
            date=date(2026, 1, 15),
            article_id="ui_agi_1",
            document_type=DocumentType.AGI_RESEARCH,
        )
    )
    rsp = RspService(kip=kip)
    rms = RmsService(kip=kip, rsp=rsp)
    created = rms.create_request(
        ResearchRequestCreate(
            title="UI draft ICICI",
            owner="analyst",
            tickers=["ICICIBANK"],
            sectors=["Financials"],
            themes=["credit_growth"],
            request_brief="Update ICICIBANK",
        )
    )
    aws = AwsService(
        kip=kip,
        rsp=rsp,
        rms=rms,
        cre=CREService(),
        validation=ValidationService(),
    )
    ioc = IocService(kip=kip, rsp=rsp, rms=rms, aws=aws, cre=CREService(), validation=ValidationService())
    return UiService(aws=aws, ioc=ioc, kip=kip, rsp=rsp, rms=rms, cre=CREService(), validation=ValidationService()), created


def test_sanitize_hides_engine_names():
    assert public_label("E03") == "technical"
    assert public_label("L4") == "composite_view"
    assert "E03" not in (scrub_text("Signal from E03 and L4") or "")
    assert "institutional model" in (scrub_text("Signal from E03 and L4") or "")


def test_home_and_company_views():
    ui, _ = _stack()
    home = ui.home()
    assert home.meta.surface == "home"
    assert home.market_brief.get("title")
    assert "E01" not in str(home.model_dump())
    assert "L4" not in str(home.model_dump())

    company = ui.company("ICICIBANK")
    assert company.ticker == "ICICIBANK"
    assert "overview" in company.model_dump()
    assert "market_intelligence" in company.model_dump()
    assert "research" in company.model_dump()
    assert "evidence" in company.model_dump()
    assert "portfolio" in company.model_dump()
    blob = str(company.model_dump())
    assert "E03" not in blob
    assert "E14" not in blob


def test_search_evidence_pack():
    ui, _ = _stack()
    pack = ui.search("What is changing at ICICIBANK?")
    assert pack.question
    assert pack.answer_policy == "institutional_evidence_pack"
    assert pack.answer.get("policy")
    assert isinstance(pack.follow_up_questions, list)
    assert "E10" not in str(pack.model_dump())


def test_theme_sector_macro_portfolio_workflow():
    ui, created = _stack()
    theme = ui.theme("credit_growth")
    assert theme.theme_id == "credit_growth"
    sector = ui.sector("Financials")
    assert sector.sector_id == "Financials"
    macro = ui.macro()
    assert macro.meta.surface == "macro"
    port = ui.portfolio()
    assert port.meta.surface == "portfolio"
    dash = ui.dashboard()
    assert dash.meta.surface == "dashboard"
    wf = ui.workflow()
    assert len(wf.stages) >= 7
    research = ui.research(created.research_id)
    assert research.research_id == created.research_id
    copilot = ui.copilot(page="company", question="Summarise ICICIBANK", ticker="ICICIBANK")
    assert copilot.context
    assert copilot.answer_policy == "context_aware_never_empty"


def test_ui_disabled():
    ui, _ = _stack()
    ui.flags = UiFlags(ui=False)
    with pytest.raises(RuntimeError, match="UI"):
        ui.home()


@pytest.mark.asyncio
async def test_ui_api_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        h = await client.get("/v1/ui/health")
        assert h.status_code == 200
        assert h.json()["exposes_engine_names"] is False

        home = await client.get("/v1/ui/home")
        assert home.status_code == 200
        assert "market_brief" in home.json()

        search = await client.post(
            "/v1/ui/search",
            params={"question": "What is changing at ICICIBANK?"},
        )
        assert search.status_code == 200
        assert search.json()["answer_policy"] in {
            "institutional_evidence_pack",
            "think_then_answer_institutional",
        }

        company = await client.get("/v1/ui/company/ICICIBANK")
        assert company.status_code == 200
        assert company.json()["ticker"] == "ICICIBANK"

        dash = await client.get("/v1/ui/dashboard")
        assert dash.status_code == 200
        macro = await client.get("/v1/ui/macro")
        assert macro.status_code == 200
        port = await client.get("/v1/ui/portfolio")
        assert port.status_code == 200
        wf = await client.get("/v1/ui/workflow")
        assert wf.status_code == 200
