"""AGI Product V1 — institutional product excellence across UI surfaces."""

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
from app.ui.product import accuracy_summary, discovery_pack, prediction_row, thesis_status
from app.ui.service import UiService
from app.validation.service import ValidationService


def _ui() -> UiService:
    kip = KipService()
    kip.ingest_agi(
        IngestRequest(
            title="AGI Product V1 ICICI",
            content=(
                "ICICIBANK Investment Thesis preferred private bank.\n"
                "Bull Case\n- Franchise growth\nBear Case\n- Credit costs\n"
                "Risks\n- NIMs\nCatalysts\n- Loan growth\n"
                "Theme: credit_growth\nSector: Financials\n"
            ),
            tickers=["ICICIBANK"],
            themes=["credit_growth"],
            sectors=["Financials"],
            date=date(2026, 1, 15),
            article_id="prod_v1_agi_1",
            document_type=DocumentType.AGI_RESEARCH,
        )
    )
    rsp = RspService(kip=kip)
    rms = RmsService(kip=kip, rsp=rsp)
    rms.create_request(
        ResearchRequestCreate(
            title="Product V1 ICICI",
            owner="analyst",
            tickers=["ICICIBANK"],
            sectors=["Financials"],
            themes=["credit_growth"],
            request_brief="Product enrichment",
        )
    )
    aws = AwsService(kip=kip, rsp=rsp, rms=rms, cre=CREService(), validation=ValidationService())
    ioc = IocService(kip=kip, rsp=rsp, rms=rms, aws=aws, cre=CREService(), validation=ValidationService())
    return UiService(aws=aws, ioc=ioc, kip=kip, rsp=rsp, rms=rms, cre=CREService(), validation=ValidationService())


def test_product_helpers():
    pack = discovery_pack(
        companies=["ICICIBANK"],
        themes=["credit_growth"],
        research=[{"title": "Note"}],
        questions=["What changed?"],
    )
    assert pack["related_companies"] == ["ICICIBANK"]
    assert pack["related_questions"]
    row = prediction_row(
        {"predicted_at": "2026-01-01", "horizon": "12m", "thesis": "Up", "confidence": 0.7},
        ticker="ICICIBANK",
    )
    assert row["ticker"] == "ICICIBANK"
    assert row["target_horizon"] == "12m"
    acc = accuracy_summary([row, {**row, "id": "2", "current_status": "hit", "outcome": "hit"}])
    assert acc["n"] == 2
    status = thesis_status(house={"current_view": "Bullish", "thesis_evolution": ["NIM better"]})
    assert status["current_stance"] == "Bullish"
    assert status["whats_changed_since_publication"]


def test_company_product_fields():
    company = _ui().company("ICICIBANK")
    assert company.product_meta.get("freshness_indicator")
    assert company.discovery.get("related_companies")
    assert company.follow_up_questions
    assert "E03" not in str(company.model_dump())


def test_theme_sector_macro_product_fields():
    ui = _ui()
    theme = ui.theme("credit_growth")
    assert theme.discovery
    assert theme.follow_up_questions
    sector = ui.sector("Financials")
    assert sector.current_outlook
    assert sector.discovery
    macro = ui.macro()
    assert macro.intelligence.get("what_happened")
    assert macro.follow_up_questions
    assert "E01" not in str(macro.intelligence)
    assert "E14" not in str(macro.intelligence)


def test_article_living_research():
    art = _ui().article("prod_v1_agi_1", ticker="ICICIBANK")
    assert art.thesis_status
    assert art.discovery
    assert isinstance(art.whats_changed_since_publication, list)


def test_prediction_centre():
    view = _ui().predictions()
    assert view.meta.surface == "predictions"
    assert isinstance(view.predictions, list)
    assert view.accuracy
    assert view.discovery


def test_home_predictions_feed():
    home = _ui().home()
    assert "latest_predictions" in home.feeds
    assert "E01" not in str(home.model_dump())


@pytest.mark.asyncio
async def test_product_v1_api_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path in (
            "/v1/ui/predictions",
            "/v1/ui/theme/credit_growth",
            "/v1/ui/sector/Financials",
            "/v1/ui/macro",
            "/v1/ui/company/ICICIBANK",
        ):
            resp = await client.get(path)
            assert resp.status_code == 200, path
            body = resp.json()
            assert "E03" not in str(body)
            assert "EngineState" not in str(body)
