"""KIP P1 — Continuous Knowledge Acquisition & House Intelligence."""

from __future__ import annotations

import base64
import io
import zipfile
from datetime import date, timedelta

import pytest
from httpx import ASGITransport, AsyncClient

from app.kip.flags import KipFlags
from app.kip.models import (
    BulkIngestItem,
    BulkIngestRequest,
    ClientSearchRequest,
    DocumentType,
    IngestRequest,
    PredictionEvalRequest,
)
from app.kip.service import KipService
from app.main import app


AGI_V1 = """
ICICI Bank — AGI Published Research
2026-01-15
Author: AGI Desk
Time horizon: 12 months
Expected return 18%

Investment Thesis
ICICIBANK is AGI's preferred private bank on deposit franchise strength.
Target price Rs 1400.

Bull Case
- Credit growth above 18%
- Digital banking share gains

Bear Case
- Unsecured stress

Risks
- Asset quality deterioration

Catalysts
- Q3 earnings

Assumptions
- Credit costs stay below 1%
- NIM stable near 4%

Valuation
ROE 16% supports premium multiples.
Chart: Deposit Mix
Supporting Evidence
- Prior AGI sector note
"""

AGI_V2 = """
ICICI Bank — AGI Update
2026-03-05
Time horizon: 12 months
Expected return 12%

Investment Thesis
ICICIBANK thesis intact but valuation less compelling after rally.
Target price Rs 1350.

Bull Case
- Fee income diversification

Bear Case
- Rate cut cycle may pressure NIM faster

Risks
- Margin compression

Catalysts
- RBI policy delivered

Assumptions
- NIM compresses modestly
"""

BROKER = """
Broker Research ICICIBANK
Broker: Kotak
We upgrade ICICIBANK to Buy. Target price Rs 1500.
Bull Case
- Loan growth
Bear Case
- Valuation
"""


def _svc(**overrides) -> KipService:
    flags = KipFlags(
        kip=overrides.get("kip", True),
        kip_rag=overrides.get("kip_rag", True),
        kip_graph=overrides.get("kip_graph", True),
        kip_versioning=overrides.get("kip_versioning", True),
        kip_ocr=overrides.get("kip_ocr", True),
        kip_llm_summary=overrides.get("kip_llm_summary", True),
        kip_auto_ingest=overrides.get("kip_auto_ingest", True),
        kip_house_view=overrides.get("kip_house_view", True),
        kip_prediction_tracking=overrides.get("kip_prediction_tracking", True),
        kip_timeline=overrides.get("kip_timeline", True),
    )
    return KipService(flags=flags)


def test_agi_auto_ingest_and_article_versioning():
    svc = _svc()
    d1 = svc.ingest_agi(
        IngestRequest(
            title="ICICI AGI v1",
            content=AGI_V1,
            document_type=DocumentType.AGI_RESEARCH,
            date=date(2026, 1, 15),
            tickers=["ICICIBANK"],
            article_id="art_icici_001",
            research_type="agi_research",
        )
    )
    assert d1.document.source == "agi"
    assert d1.article_id == "art_icici_001"
    assert d1.research.expected_return
    assert d1.research.time_horizon
    assert "house_view_update" in d1.pipeline_stages
    d2 = svc.ingest_agi(
        IngestRequest(
            title="ICICI AGI v2",
            content=AGI_V2,
            document_type=DocumentType.AGI_RESEARCH,
            date=date(2026, 3, 5),
            tickers=["ICICIBANK"],
            article_id="art_icici_001",
        )
    )
    assert d2.document.version == 2
    assert d2.lineage_id == d1.lineage_id
    assert d2.supersedes == d1.document_id


def test_house_view_evolution():
    svc = _svc()
    svc.ingest_agi(
        IngestRequest(
            title="v1",
            content=AGI_V1,
            date=date(2026, 1, 15),
            tickers=["ICICIBANK"],
            article_id="a1",
        )
    )
    svc.ingest_agi(
        IngestRequest(
            title="v2",
            content=AGI_V2,
            date=date(2026, 3, 5),
            tickers=["ICICIBANK"],
            article_id="a1",
        )
    )
    hv = svc.house_view("ICICIBANK")
    assert hv.current_view is not None
    assert len(hv.historical_views) >= 2
    assert hv.thesis_evolution
    assert hv.what_changed
    assert hv.research_confidence > 0


def test_broker_bulk_zip_and_newsletter():
    svc = _svc()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("kotak_icici.md", BROKER)
        zf.writestr("note.txt", "HDFCBANK strategy note on deposit franchise")
    result = svc.ingest_broker(
        BulkIngestRequest(
            zip_base64=base64.b64encode(buf.getvalue()).decode("ascii"),
            default_broker="Kotak",
            source_channel="broker",
        )
    )
    assert result.count >= 2
    assert result.ingested

    nl = svc.ingest_newsletter(
        IngestRequest(
            title="Fintech weekly",
            content="Newsletter on ICICIBANK digital banking UPI",
            tickers=["ICICIBANK"],
            date=date(2026, 2, 1),
        )
    )
    assert nl.document.document_type == DocumentType.NEWSLETTER

    internal = svc.ingest_internal(
        IngestRequest(
            title="Internal note",
            content="Internal AGI note on ICICIBANK risks",
            tickers=["ICICIBANK"],
        )
    )
    assert internal.document.document_type in {
        DocumentType.AGI_NOTE,
        DocumentType.AGI_INVESTMENT_OFFICE,
        DocumentType.STRATEGY_NOTE,
    }


def test_priority_rag_agi_first():
    svc = _svc()
    svc.ingest_broker(
        IngestRequest(
            title="Broker ICICI",
            content=BROKER,
            tickers=["ICICIBANK"],
            date=date(2026, 2, 1),
            broker="Kotak",
        )
    )
    svc.ingest_agi(
        IngestRequest(
            title="AGI ICICI",
            content=AGI_V1,
            tickers=["ICICIBANK"],
            date=date(2026, 1, 15),
            article_id="agi1",
        )
    )
    svc.ingest(
        IngestRequest(
            title="News blurb",
            content="Market news ICICIBANK stock moves on rates",
            document_type=DocumentType.MARKET_NEWS,
            source="news",
            tickers=["ICICIBANK"],
            date=date(2026, 3, 1),
        )
    )
    pack = svc.rag("ICICIBANK house view", ticker="ICICIBANK", limit=5)
    assert pack.agi_research_used
    assert pack.retrieval_order[0] == "agi_research"
    # First retrieved document should be AGI priority when present
    first = svc.get_document(pack.documents_retrieved[0])
    assert first is not None
    assert first.document.document_type.value.startswith("agi_")


def test_prediction_tracking_and_eval():
    svc = _svc()
    doc = svc.ingest_agi(
        IngestRequest(
            title="pred",
            content=AGI_V1,
            tickers=["ICICIBANK"],
            date=date.today() - timedelta(days=100),
            article_id="pred1",
            expected_return="18%",
            time_horizon="12 months",
        )
    )
    preds = svc.predictions("ICICIBANK")
    assert preds
    assert preds[0].document_id == doc.document_id
    updated = svc.evaluate_prediction(
        PredictionEvalRequest(
            prediction_id=preds[0].prediction_id,
            outcome_return=10.0,
            catalyst_hit=True,
            as_of=date.today(),
        )
    )
    assert updated.hit is True
    assert updated.status in {"evaluated_3m", "evaluated_6m", "evaluated_12m"}
    stats = svc.prediction_stats("ICICIBANK")
    assert stats.evaluated >= 1
    assert stats.hit_rate == 1.0


def test_client_search_never_answers_directly():
    svc = _svc()
    svc.ingest_agi(
        IngestRequest(
            title="AGI",
            content=AGI_V1,
            tickers=["ICICIBANK"],
            date=date(2026, 1, 15),
            article_id="c1",
        )
    )
    resp = svc.client_search(
        ClientSearchRequest(
            question="What is AGI house view on ICICIBANK valuation?",
            ticker="ICICIBANK",
            engine_states=[{"engine": "E01", "regime": "risk_on"}],
            l4_opinion={"side": "long", "confidence": 0.62},
            portfolio_exposure={"ICICIBANK": 0.04},
        )
    )
    assert resp.answer_policy == "never_answer_directly"
    assert resp.intent
    assert resp.evidence.agi_research_used
    assert resp.evidence.engine_evidence
    assert resp.evidence.l4_opinion is not None
    assert resp.validation["knowledge_version"]
    assert resp.validation["confidence"] >= 0
    assert "retrieved_agi_articles" in resp.validation


def test_company_dossier_and_research_continuity():
    svc = _svc()
    svc.ingest_agi(
        IngestRequest(
            title="AGI",
            content=AGI_V1,
            tickers=["ICICIBANK"],
            date=date(2026, 1, 15),
            article_id="d1",
        )
    )
    svc.ingest_broker(
        IngestRequest(
            title="Broker",
            content=BROKER,
            tickers=["ICICIBANK"],
            date=date(2026, 2, 1),
        )
    )
    dossier = svc.company_dossier("ICICIBANK")
    assert dossier.house_view is not None
    assert dossier.research_history is not None
    assert dossier.research_history.agi_reports
    assert dossier.timeline is not None
    ctx = svc.research_context(
        "Update ICICIBANK research",
        ticker="ICICIBANK",
        engine_states=[{"engine": "E13", "signal": 0.2}],
        l4_opinion={"side": "long"},
        portfolio_exposure={"ICICIBANK": 0.03},
    )
    assert ctx["agi_research_used"]
    assert ctx["broker_reports_used"]
    assert ctx["engine_evidence"]
    assert ctx["answer_policy"] == "house_view_first_then_external"


def test_p1_flags():
    disabled = _svc(kip_auto_ingest=False)
    with pytest.raises(RuntimeError, match="KIP_AUTO_INGEST"):
        disabled.ingest_agi(IngestRequest(title="x", content="ICICIBANK"))

    no_hv = _svc(kip_house_view=False)
    no_hv.ingest(IngestRequest(title="x", content="ICICIBANK thesis", tickers=["ICICIBANK"]))
    with pytest.raises(RuntimeError, match="KIP_HOUSE_VIEW"):
        no_hv.house_view("ICICIBANK")


@pytest.mark.asyncio
async def test_kip_p1_http_apis():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/kip/health")
        assert health.status_code == 200
        flags = health.json()["flags"]
        assert flags["KIP_AUTO_INGEST"] is True
        assert flags["KIP_HOUSE_VIEW"] is True
        assert flags["KIP_PREDICTION_TRACKING"] is True
        assert flags["KIP_TIMELINE"] is True

        agi = await client.post(
            "/v1/kip/ingest/agi",
            json={
                "title": "Published ICICI",
                "content": AGI_V1,
                "tickers": ["ICICIBANK"],
                "date": "2026-01-15",
                "article_id": "web_001",
                "document_type": "agi_research",
            },
        )
        assert agi.status_code == 200, agi.text

        broker = await client.post(
            "/v1/kip/ingest/broker",
            json={
                "items": [
                    {
                        "filename": "kotak.md",
                        "content": BROKER,
                        "tickers": ["ICICIBANK"],
                        "broker": "Kotak",
                        "date": "2026-02-01",
                    }
                ]
            },
        )
        assert broker.status_code == 200, broker.text
        assert broker.json()["count"] >= 1

        hv = await client.get("/v1/kip/house-view/ICICIBANK")
        assert hv.status_code == 200
        assert hv.json()["current_view"]

        hist = await client.get("/v1/kip/research-history/ICICIBANK")
        assert hist.status_code == 200

        preds = await client.get("/v1/kip/predictions/ICICIBANK")
        assert preds.status_code == 200
        assert preds.json()["predictions"]

        dossier = await client.get("/v1/kip/company-dossier/ICICIBANK")
        assert dossier.status_code == 200

        rag = await client.get("/v1/kip/rag", params={"q": "ICICIBANK", "ticker": "ICICIBANK"})
        assert rag.status_code == 200
        assert rag.json()["agi_research_used"]

        client_search = await client.post(
            "/v1/kip/client-search",
            json={"question": "Should I buy ICICIBANK?", "ticker": "ICICIBANK"},
        )
        assert client_search.status_code == 200
        assert client_search.json()["answer_policy"] == "never_answer_directly"


def test_bulk_markdown_item_helper():
    svc = _svc()
    result = svc.ingest_bulk(
        BulkIngestRequest(
            items=[
                BulkIngestItem(
                    filename="note.md",
                    content="Markdown broker note on RELIANCE energy capex",
                    tickers=["RELIANCE"],
                )
            ],
            source_channel="broker",
            default_broker="Internal Desk",
        )
    )
    assert result.count == 1
