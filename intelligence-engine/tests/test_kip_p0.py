"""Knowledge Intelligence Platform P0 — institutional memory layer."""

from __future__ import annotations

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from app.kip.flags import KipFlags
from app.kip.models import DocumentType, IngestRequest
from app.kip.service import KipService
from app.main import app


ICICI_V1 = """
ICICI Bank — Institutional Update
2026-01-15

Investment Thesis
ICICIBANK remains a high-quality private bank with durable deposit franchise and improving credit costs.
Target price Rs 1400. PE 18. EPS growth intact.

Bull Case
- Credit growth accelerates above 18%
- Digital banking and UPI share gains
- NIM expands on rate cut lag

Bear Case
- Unsecured stress rises
- Competitive intensity compresses margins

Risks
- Asset quality deterioration in retail
- Regulatory tightening by RBI

Catalysts
- Q3 earnings on 2026-02-02
- Management interview on 2026-02-08

Valuation
Trade at a premium to PSU banks; fair value supported by ROE 16%.

Counter Arguments
- Valuation already prices perfection
"""

ICICI_V2 = """
ICICI Bank — AGI Research Update
2026-03-05

Investment Thesis
Post Q3, ICICIBANK thesis intact but valuation less compelling after rally.
Target price Rs 1350.

Bull Case
- Fee income diversification
- Liability franchise remains best-in-class

Bear Case
- Rate cut cycle may pressure NIM faster than expected
- Downgrade risk if credit costs normalize higher

Risks
- Margin compression
- Slower loan growth

Catalysts
- RBI policy on 2026-03-01 already delivered cut
- AGI update cycle

Sector: banking Financials
Theme: credit growth, rate cut
"""

BROKER_BEAR = """
Broker Research — ICICI Bank Downgrade
2026-02-20
Broker: Motilal

Investment Thesis
We downgrade ICICIBANK to Underweight / Sell on rich valuations.

Bear Case
- Premium multiples unjustified versus HDFCBANK
- Street estimates too optimistic

Bull Case
- Franchise quality still strong

Risks
- Multiple compression

Valuation
Cut target price Rs 1100.
"""


def _svc(**flag_overrides) -> KipService:
    flags = KipFlags(
        kip=flag_overrides.get("kip", True),
        kip_rag=flag_overrides.get("kip_rag", True),
        kip_graph=flag_overrides.get("kip_graph", True),
        kip_versioning=flag_overrides.get("kip_versioning", True),
        kip_ocr=flag_overrides.get("kip_ocr", True),
        kip_llm_summary=flag_overrides.get("kip_llm_summary", True),
    )
    return KipService(flags=flags)


def test_ingest_pipeline_extracts_institutional_fields():
    svc = _svc()
    doc = svc.ingest(
        IngestRequest(
            title="ICICI Bank — Institutional Update",
            content=ICICI_V1,
            source="agi",
            document_type=DocumentType.AGI_RESEARCH,
            author="AGI Desk",
            date=date(2026, 1, 15),
            tickers=["ICICIBANK"],
        )
    )
    assert doc.immutable is True
    assert doc.document.title.startswith("ICICI")
    assert "ICICIBANK" in doc.investment.tickers
    assert doc.research.investment_thesis
    assert doc.research.bull_case
    assert doc.research.bear_case
    assert doc.research.risks
    assert doc.research.catalysts
    assert doc.research.target_prices
    assert doc.knowledge.confidence > 0
    assert doc.knowledge.freshness > 0
    assert doc.knowledge.summary
    assert "chunking" in doc.pipeline_stages
    assert "knowledge_graph" in doc.pipeline_stages
    assert len(svc.store.chunks) >= 1
    assert svc.store.chunks[0].embedding


def test_ocr_and_versioning_lineage():
    svc = _svc()
    v1 = svc.ingest(
        IngestRequest(
            title="ICICI v1",
            content=ICICI_V1,
            source="agi",
            document_type=DocumentType.AGI_RESEARCH,
            date=date(2026, 1, 15),
            tickers=["ICICIBANK"],
            needs_ocr=True,
            ocr_text=ICICI_V1,
        )
    )
    assert v1.ocr_applied is True
    assert v1.document.version == 1
    v2 = svc.ingest(
        IngestRequest(
            title="ICICI v2",
            content=ICICI_V2,
            source="agi",
            document_type=DocumentType.AGI_RESEARCH,
            date=date(2026, 3, 5),
            tickers=["ICICIBANK"],
            supersedes=v1.document_id,
        )
    )
    assert v2.document.version == 2
    assert v2.lineage_id == v1.lineage_id
    assert v2.supersedes == v1.document_id
    refreshed = svc.get_document(v1.document_id)
    assert refreshed is not None
    assert refreshed.superseded_by == v2.document_id
    # immutability: content of v1 unchanged
    assert "Target price Rs 1400" in refreshed.cleaned_content


def test_company_timeline_and_graph():
    svc = _svc()
    svc.ingest(
        IngestRequest(
            title="Broker Upgrade ICICI",
            content="2026-01-15 Broker Upgrade ICICIBANK overweight banking rate cut",
            source="broker",
            document_type=DocumentType.BROKER_RESEARCH,
            broker="Kotak",
            date=date(2026, 1, 15),
            tickers=["ICICIBANK"],
        )
    )
    svc.ingest(
        IngestRequest(
            title="Q3 Earnings",
            content="2026-02-02 Q3 Earnings ICICIBANK beat EPS",
            source="agi",
            document_type=DocumentType.EARNINGS_TRANSCRIPT,
            date=date(2026, 2, 2),
            tickers=["ICICIBANK"],
        )
    )
    svc.ingest(
        IngestRequest(
            title="AGI Research",
            content=ICICI_V1,
            source="agi",
            document_type=DocumentType.AGI_RESEARCH,
            date=date(2026, 2, 5),
            tickers=["ICICIBANK"],
        )
    )
    tl = svc.timeline("ICICIBANK")
    assert tl.ticker == "ICICIBANK"
    assert len(tl.events) >= 3
    dates = [e.event_date for e in tl.events]
    assert dates == sorted(dates)
    company = svc.get_company("ICICIBANK")
    assert company.latest_thesis
    assert company.timeline is not None
    g = svc.graph("ICICIBANK")
    assert g.nodes
    assert any(e.relation == "MENTIONS_COMPANY" for e in g.edges) or any(
        n.kind == "company" for n in g.nodes
    )


def test_hybrid_search_and_similarity():
    svc = _svc()
    a = svc.ingest(
        IngestRequest(
            title="ICICI thesis",
            content=ICICI_V1,
            source="agi",
            document_type=DocumentType.AGI_RESEARCH,
            date=date(2026, 1, 15),
            tickers=["ICICIBANK"],
            themes=["credit_growth"],
        )
    )
    svc.ingest(
        IngestRequest(
            title="HDFC note",
            content="HDFCBANK deposit franchise and credit growth in Financials sector",
            source="agi",
            document_type=DocumentType.AGI_NOTE,
            date=date(2026, 1, 20),
            tickers=["HDFCBANK"],
        )
    )
    hybrid = svc.search("ICICI Bank credit growth NIM", mode="hybrid", limit=5)
    assert hybrid.hits
    assert any(h.document_id == a.document_id for h in hybrid.hits)
    company = svc.search("ICICIBANK", mode="company", ticker="ICICIBANK")
    assert company.hits
    theme = svc.search("credit", mode="theme", theme="credit_growth")
    assert theme.hits
    sim = svc.similar(a.document_id, limit=5)
    assert sim.mode == "similar"


def test_rag_evidence_pack_with_conflicts():
    svc = _svc()
    svc.ingest(
        IngestRequest(
            title="AGI bullish ICICI",
            content=ICICI_V1,
            source="agi",
            document_type=DocumentType.AGI_RESEARCH,
            date=date(2026, 1, 15),
            tickers=["ICICIBANK"],
        )
    )
    svc.ingest(
        IngestRequest(
            title="Broker bearish ICICI",
            content=BROKER_BEAR,
            source="broker",
            document_type=DocumentType.BROKER_RESEARCH,
            broker="Motilal",
            date=date(2026, 2, 20),
            tickers=["ICICIBANK"],
        )
    )
    pack = svc.rag("ICICIBANK investment thesis", ticker="ICICIBANK")
    assert pack.answer_policy == "retrieval_augmented_only"
    assert pack.documents_retrieved
    assert pack.supporting_evidence or pack.conflicting_opinions
    assert pack.source_list
    assert 0 <= pack.freshness_score <= 1
    assert 0 <= pack.confidence_score <= 1
    ctx = svc.research_context("ICICIBANK update", ticker="ICICIBANK")
    for key in (
        "documents_retrieved",
        "knowledge_version",
        "source_list",
        "conflicting_evidence",
        "freshness_score",
        "confidence_score",
    ):
        assert key in ctx


def test_theme_endpoint_and_flags():
    svc = _svc()
    svc.ingest(
        IngestRequest(
            title="Digital banking theme",
            content="ICICIBANK digital banking UPI fintech theme gains",
            source="newsletter",
            document_type=DocumentType.NEWSLETTER,
            date=date(2026, 2, 1),
            tickers=["ICICIBANK"],
            themes=["digital_banking"],
        )
    )
    theme = svc.get_theme("digital_banking")
    assert theme.documents
    assert "ICICIBANK" in theme.tickers

    disabled = _svc(kip=False)
    with pytest.raises(RuntimeError, match="KIP is disabled"):
        disabled.ingest(IngestRequest(title="x", content="y"))

    no_rag = _svc(kip_rag=False)
    no_rag.ingest(
        IngestRequest(
            title="x",
            content="ICICIBANK thesis",
            tickers=["ICICIBANK"],
            document_type=DocumentType.AGI_NOTE,
        )
    )
    with pytest.raises(RuntimeError, match="KIP_RAG"):
        no_rag.rag("ICICIBANK")

    no_graph = _svc(kip_graph=False)
    no_graph.ingest(
        IngestRequest(
            title="x",
            content="ICICIBANK thesis",
            tickers=["ICICIBANK"],
            document_type=DocumentType.AGI_NOTE,
        )
    )
    with pytest.raises(RuntimeError, match="KIP_GRAPH"):
        no_graph.graph("ICICIBANK")


def test_self_learning_from_research_run():
    from app.schemas.models import (
        ConfidenceBreakdown,
        DeskType,
        InstitutionalReport,
        ResearchRun,
        RunStatus,
    )

    svc = _svc()
    run = ResearchRun(
        desk=DeskType.CIO_MORNING,
        status=RunStatus.COMPLETED,
        symbols=["ICICIBANK"],
        cio_thesis="Private banks remain preferred.",
        report=InstitutionalReport(
            desk=DeskType.CIO_MORNING,
            title="CIO Morning — Banks",
            executive_summary="ICICIBANK favored on deposit franchise.",
            risks=["Margin compression"],
            catalysts=["RBI policy"],
            confidence=ConfidenceBreakdown(
                score=70,
                rationale="Supported by deposit franchise evidence.",
            ),
        ),
    )
    doc = svc.ingest_research_run(run)
    assert doc is not None
    assert doc.document.document_type == DocumentType.AGI_CIO_REPORT
    assert "ICICIBANK" in doc.investment.tickers


@pytest.mark.asyncio
async def test_kip_http_apis():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/kip/health")
        assert health.status_code == 200
        body = health.json()
        assert body["platform"] == "KIP"
        assert body["flags"]["KIP"] is True

        ingest = await client.post(
            "/v1/kip/ingest",
            json={
                "title": "ICICI API ingest",
                "content": ICICI_V1,
                "source": "agi",
                "document_type": "agi_research",
                "date": "2026-01-15",
                "tickers": ["ICICIBANK"],
            },
        )
        assert ingest.status_code == 200, ingest.text
        doc_id = ingest.json()["document_id"]

        got = await client.get(f"/v1/kip/document/{doc_id}")
        assert got.status_code == 200
        assert got.json()["document_id"] == doc_id

        company = await client.get("/v1/kip/company/ICICIBANK")
        assert company.status_code == 200
        assert company.json()["ticker"] == "ICICIBANK"

        search = await client.get("/v1/kip/search", params={"q": "ICICI NIM", "mode": "hybrid"})
        assert search.status_code == 200
        assert search.json()["hits"]

        timeline = await client.get("/v1/kip/timeline/ICICIBANK")
        assert timeline.status_code == 200
        assert timeline.json()["events"]

        similar = await client.get(f"/v1/kip/similar/{doc_id}")
        assert similar.status_code == 200

        graph = await client.get("/v1/kip/graph/ICICIBANK")
        assert graph.status_code == 200
        assert graph.json()["nodes"]

        theme = await client.get("/v1/kip/theme/credit_growth")
        assert theme.status_code == 200

        rag = await client.get("/v1/kip/rag", params={"q": "ICICIBANK thesis", "ticker": "ICICIBANK"})
        assert rag.status_code == 200
        assert rag.json()["answer_policy"] == "retrieval_augmented_only"


def test_no_engine_redesign_surface():
    """KIP is a platform package, not an engine under app/engines."""
    import app.kip as kip
    import app.engines as engines

    assert hasattr(kip, "KipService")
    assert not hasattr(engines, "kip")
