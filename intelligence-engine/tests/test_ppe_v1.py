"""Public Product Experience V1 — Ask AGI, popular questions, rich answers."""

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
from app.ui.questions import build_popular_questions, follow_up_questions
from app.ui.service import UiService
from app.validation.service import ValidationService


def _ui() -> UiService:
    kip = KipService()
    kip.ingest_agi(
        IngestRequest(
            title="AGI ICICI PPE",
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
            article_id="ppe_agi_1",
            document_type=DocumentType.AGI_RESEARCH,
        )
    )
    rsp = RspService(kip=kip)
    rms = RmsService(kip=kip, rsp=rsp)
    rms.create_request(
        ResearchRequestCreate(
            title="PPE ICICI note",
            owner="analyst",
            tickers=["ICICIBANK"],
            sectors=["Financials"],
            themes=["credit_growth"],
            request_brief="Update",
        )
    )
    aws = AwsService(kip=kip, rsp=rsp, rms=rms, cre=CREService(), validation=ValidationService())
    ioc = IocService(kip=kip, rsp=rsp, rms=rms, aws=aws, cre=CREService(), validation=ValidationService())
    return UiService(aws=aws, ioc=ioc, kip=kip, rsp=rsp, rms=rms, cre=CREService(), validation=ValidationService())


def test_popular_questions_regime_aware():
    rows = build_popular_questions(
        regime_label="RiskOn",
        risk_label="Elevated",
        themes=[{"id": "defence", "name": "Defence"}],
        research=[{"title": "ICICI note", "tickers": ["ICICIBANK"]}],
        calendar=[{"title": "RBI MPC Decision"}],
    )
    texts = " ".join(r["question"] for r in rows).lower()
    assert "rbi" in texts or "interest rates" in texts
    assert any("icici" in r["question"].lower() for r in rows)
    assert len(rows) >= 6


def test_follow_ups_count():
    qs = follow_up_questions(
        question="Should I buy ICICI Bank?",
        intent="recommendation_request",
        related_companies=["ICICIBANK", "HDFCBANK"],
        related_themes=["credit_growth"],
        house_label="Bullish",
    )
    assert 4 <= len(qs) <= 8


def test_home_ppe_fields():
    home = _ui().home()
    assert home.hero.get("headline")
    assert home.popular_questions
    assert home.feeds.get("latest_research") is not None
    assert home.ask_placeholder
    assert "E01" not in str(home.model_dump())


def test_rich_search_answer():
    import re

    pack = _ui().search("What is changing at ICICIBANK?")
    assert pack.executive_summary
    assert pack.answer.get("summary")
    assert len(pack.follow_up_questions) >= 4
    assert pack.recommendations
    dumped = str(pack.model_dump())
    # Avoid false positives from hex ids (e.g. ...E03F)
    assert not re.search(r"(?<![A-Za-z0-9])E03(?![A-Za-z0-9])", dumped)
    assert pack.answer_policy in {
        "institutional_evidence_pack",
        "think_then_answer_institutional",
    }


def test_autocomplete_and_article():
    ui = _ui()
    ac = ui.autocomplete("ICICI")
    assert ac.meta.surface == "autocomplete"
    art = ui.article("ppe_agi_1", ticker="ICICIBANK")
    assert art.article_id == "ppe_agi_1"


@pytest.mark.asyncio
async def test_ppe_api_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        home = await client.get("/v1/ui/home")
        assert home.status_code == 200
        body = home.json()
        assert body["popular_questions"]
        assert body["hero"]

        search = await client.post("/v1/ui/search", params={"question": "Summarise today's market."})
        assert search.status_code == 200
        assert search.json()["executive_summary"]
        assert len(search.json()["follow_up_questions"]) >= 4

        ac = await client.get("/v1/ui/autocomplete", params={"q": "bank"})
        assert ac.status_code == 200

        art = await client.get("/v1/ui/article/demo", params={"ticker": "ICICIBANK"})
        assert art.status_code == 200
