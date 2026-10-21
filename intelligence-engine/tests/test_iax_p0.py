"""IAX P0 — Institutional Answer Experience workspace fields."""

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
from app.ui.iax import (
    evidence_items,
    house_view_card,
    market_intelligence_summary,
    normalize_stance,
    whats_changed,
)
from app.ui.service import UiService
from app.validation.service import ValidationService


def _ui() -> UiService:
    kip = KipService()
    kip.ingest_agi(
        IngestRequest(
            title="AGI ICICI IAX Brief",
            content=(
                "ICICIBANK Investment Thesis preferred private bank.\n"
                "Bull Case\n- Franchise growth\nBear Case\n- Credit costs\n"
                "Risks\n- NIMs compression\nCatalysts\n- Loan growth rebound\n"
                "Theme: credit_growth\nSector: Financials\n"
            ),
            tickers=["ICICIBANK"],
            themes=["credit_growth"],
            sectors=["Financials"],
            date=date(2026, 1, 15),
            article_id="iax_agi_1",
            document_type=DocumentType.AGI_RESEARCH,
        )
    )
    rsp = RspService(kip=kip)
    rms = RmsService(kip=kip, rsp=rsp)
    rms.create_request(
        ResearchRequestCreate(
            title="IAX ICICI note",
            owner="analyst",
            tickers=["ICICIBANK"],
            sectors=["Financials"],
            themes=["credit_growth"],
            request_brief="Update house view",
        )
    )
    aws = AwsService(kip=kip, rsp=rsp, rms=rms, cre=CREService(), validation=ValidationService())
    ioc = IocService(kip=kip, rsp=rsp, rms=rms, aws=aws, cre=CREService(), validation=ValidationService())
    return UiService(aws=aws, ioc=ioc, kip=kip, rsp=rsp, rms=rms, cre=CREService(), validation=ValidationService())


def test_normalize_stance_and_house_card():
    assert normalize_stance("Strongly Bullish") == "Bullish"
    assert normalize_stance("bearish") == "Bearish"
    # Critical: stringified HistoricalView contains "bull_case" and must NOT become Bullish.
    dumped = (
        "{'document_id': 'doc_x', 'thesis': 'weak growth visibility and macro challenges', "
        "'bull_case': [], 'bear_case': []}"
    )
    assert normalize_stance(dumped) == "Bearish"
    card = house_view_card({"current_view": "Bullish", "horizon": "12m", "conviction": "high"}, 0.72)
    assert card["stance"] == "Bullish"
    assert card["bullish"] is True
    assert card["confidence"] == 0.72
    # HouseView dumps nest thesis under current_view — must not collapse to Neutral noise.
    nested = house_view_card(
        {
            "ticker": "INDIA_IT",
            "research_confidence": 0.7,
            "current_view": {
                "document_id": "doc_x",
                "thesis": "Indian IT services face weak growth visibility and AI productivity pressure.",
                "bull_case": [],
                "bear_case": [],
            },
        },
        None,
    )
    assert nested["stance"] == "Bearish"
    assert nested["confidence"] == 0.7
    assert nested["label"] == "Bearish"


def test_whats_changed_highlights_deltas():
    changed = whats_changed(
        house={
            "current_view": "Bullish",
            "thesis_evolution": ["Loan growth improving"],
            "failed_assumptions": ["NIM pressure rising"],
            "catalysts_occurred": ["Deposit franchise held"],
        },
        prior_house={"current_view": "Neutral", "confidence": 0.4, "thesis": "Old thesis"},
        conf=0.7,
        prior_conf=0.4,
        thesis="New franchise thesis",
    )
    kinds = {i["kind"] for i in changed["items"]}
    assert "stance" in kinds
    assert "confidence" in kinds
    assert changed["buckets"]["new_risks"]
    assert changed["buckets"]["new_catalysts"]


def test_evidence_and_market_intelligence_scrub_engines():
    items = evidence_items(
        [{"title": "Broker note E03 overlay", "source": "broker_desk", "document_type": "broker", "snippet": "Supportive"}],
        default_type="broker",
    )
    blob = str(items)
    assert "E03" not in blob
    mi = market_intelligence_summary({"macro": {"regime": "RiskOn", "confidence": 0.8}})
    dims = {row["dimension"] for row in mi}
    assert {"Market", "Business", "Risk", "Momentum", "Events", "Sentiment", "Volatility"} <= dims
    assert "E01" not in str(mi)


def test_search_returns_iax_workspace_fields():
    pack = _ui().search("What is changing at ICICIBANK?")
    assert pack.executive_summary
    assert pack.house_view_card.get("stance")
    assert pack.whats_changed.get("items")
    assert pack.current_thesis
    assert isinstance(pack.supporting_evidence, list)
    assert isinstance(pack.conflicting_evidence, list)
    assert pack.research_panel
    assert pack.knowledge_graph.get("buckets") is not None
    assert pack.market_intelligence
    assert isinstance(pack.charts, list)
    assert pack.related_ideas
    assert pack.workspace.get("mode") == "institutional_answer"
    assert 4 <= len(pack.follow_up_questions) <= 8
    import re

    dumped = str(pack.model_dump())
    # Avoid false positives from hex ids (e.g. ...E03EE84)
    assert not re.search(r"(?<![A-Za-z0-9])E01(?![A-Za-z0-9])", dumped)
    assert not re.search(r"(?<![A-Za-z0-9])E03(?![A-Za-z0-9])", dumped)
    assert "EngineState" not in dumped


def test_sector_search_uses_titles_and_synthesizes_house_view():
    ui = _ui()
    ui.kip.ingest_agi(
        IngestRequest(
            title="hello world",
            content="tiny test note that should be ignored by Ask AGI quality filters",
            tickers=["SERVICES", "GLOBAL", "TCS"],
            date=date(2026, 7, 1),
            article_id="junk_hello",
            document_type=DocumentType.AGI_NOTE,
        )
    )
    ui.kip.ingest_agi(
        IngestRequest(
            title="India IT Sector update",
            content=(
                "India IT Services – Q1FY27 Review &amp; Outlook. "
                "The Indian IT services sector continues to face weak growth visibility, "
                "with earnings reflecting ongoing macro challenges, slower deal conversions, "
                "and increasing pressure from AI-led productivity demands. "
                "Key Sector Takeaways (Q1FY27) Revenue growth remained muted at around 0% QoQ "
                "(constant currency, organic), indicating continued demand weakness. "
                "On a YoY basis, growth improved slightly to 3.1%, driven mainly by better "
                "performance from select large-cap names.\n"
                "Sector: Information Technology\nTheme: ai_adoption\n"
            ),
            tickers=["SERVICES", "CONTINUES", "TCS", "INFY"],
            sectors=["Information Technology"],
            themes=["ai_adoption"],
            date=date(2026, 7, 24),
            article_id="india_it_q1fy27",
            document_type=DocumentType.AGI_RESEARCH,
        )
    )
    pack = ui.search("how is Indian IT services doing?")
    titles = " ".join(str(i.get("title") or "") for i in (pack.supporting_evidence or []))
    assert "India IT" in titles or "IT Services" in titles or "IT Sector" in titles
    assert "hello world" not in titles.lower()
    assert not any(str(i.get("title") or "").startswith("doc_") for i in (pack.supporting_evidence or []))
    assert pack.house_view_card.get("stance") == "Bearish"
    assert pack.house_view_card.get("label") == "Bearish"
    assert "document_id" not in (pack.executive_summary or "")
    assert "bull_case" not in (pack.executive_summary or "")
    assert "Current AGI house view is Bearish" in " ".join(pack.why or [])
    thesis_text = pack.investment_thesis or (pack.current_thesis or {}).get("summary") or ""
    assert "weak growth" in thesis_text.lower() or "IT services" in thesis_text
    assert "&amp;" not in thesis_text
    assert (pack.current_thesis or {}).get("bear_case")
    assert "House view not yet established" not in (pack.executive_summary or "")
    related_blob = " ".join(pack.related_companies or [])
    assert "SERVICES" not in related_blob
    assert "CONTINUES" not in related_blob
    assert "GLOBAL" not in related_blob
    for item in pack.supporting_evidence or []:
        assert not str(item.get("title") or "").startswith("doc_")


def test_timeline_surface():
    view = _ui().timeline("ICICIBANK")
    assert view.meta.surface == "timeline"
    assert view.entity == "ICICIBANK"
    assert isinstance(view.events, list)


@pytest.mark.asyncio
async def test_iax_api_routes():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        search = await client.post("/v1/ui/search", params={"question": "What is changing at ICICIBANK?"})
        assert search.status_code == 200
        body = search.json()
        assert body["house_view_card"]
        assert body["whats_changed"]
        assert body["supporting_evidence"] is not None
        assert body["market_intelligence"]
        assert "E14" not in str(body)

        tl = await client.get("/v1/ui/timeline/ICICIBANK")
        assert tl.status_code == 200
        assert tl.json()["entity"] == "ICICIBANK"
