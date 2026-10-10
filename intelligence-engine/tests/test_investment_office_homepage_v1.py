"""Investment Office Homepage V1 — live home aggregation fields."""

from __future__ import annotations

from datetime import date

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
from app.ui.service import UiService
from app.validation.service import ValidationService


def _ui() -> UiService:
    kip = KipService()
    kip.ingest_agi(
        IngestRequest(
            title="Office Home ICICI",
            content="ICICIBANK thesis.\nTheme: credit_growth\nSector: Financials\n",
            tickers=["ICICIBANK"],
            themes=["credit_growth"],
            sectors=["Financials"],
            date=date(2026, 1, 15),
            article_id="office_home_1",
            document_type=DocumentType.AGI_RESEARCH,
        )
    )
    rsp = RspService(kip=kip)
    rms = RmsService(kip=kip, rsp=rsp)
    rms.create_request(
        ResearchRequestCreate(
            title="Office home note",
            owner="analyst",
            tickers=["ICICIBANK"],
            sectors=["Financials"],
            themes=["credit_growth"],
            request_brief="Home",
        )
    )
    aws = AwsService(kip=kip, rsp=rsp, rms=rms, cre=CREService(), validation=ValidationService())
    ioc = IocService(kip=kip, rsp=rsp, rms=rms, aws=aws, cre=CREService(), validation=ValidationService())
    return UiService(aws=aws, ioc=ioc, kip=kip, rsp=rsp, rms=rms, cre=CREService(), validation=ValidationService())


def test_home_office_fields():
    home = _ui().home()
    assert home.morning_intelligence.get("cards")
    assert len(home.morning_intelligence["cards"]) >= 6
    labels = {c["label"] for c in home.morning_intelligence["cards"]}
    assert "Today's House View" in labels or "Current House View" in labels
    assert any("Regime" in x for x in labels)
    assert "Platform Health" in labels
    assert home.knowledge_feed
    assert home.featured_research
    assert home.economic_calendar
    assert home.market_themes
    assert home.top_companies
    assert home.feeds.get("latest_predictions")
    assert home.market_dashboard.get("tabs")
    assert home.market_dashboard.get("heatmap")
    assert home.footer_metrics.get("companies_covered")
    assert home.newsletter.get("subscribers")
    assert len(home.popular_questions) >= 8
    blob = str(home.model_dump())
    assert "E01" not in blob
    assert "E14" not in blob
    assert "L4" not in blob
    assert "Unavailable" not in home.morning_intelligence["cards"][0]["value"]


def test_calendar_surface():
    cal = _ui().calendar()
    assert cal["meta"]["surface"] == "calendar"
    assert "events" in cal


@pytest.mark.asyncio
async def test_home_and_calendar_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        home = await client.get("/v1/ui/home")
        assert home.status_code == 200
        body = home.json()
        assert body["morning_intelligence"]["cards"]
        assert body["footer_metrics"]
        assert "E03" not in str(body)

        cal = await client.get("/v1/ui/calendar")
        assert cal.status_code == 200
        assert cal.json()["meta"]["surface"] == "calendar"
