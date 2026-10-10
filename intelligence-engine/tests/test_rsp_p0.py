"""RSP P0 — Reasoning & Research Synthesis Platform."""

from __future__ import annotations

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from app.kip.models import DocumentType, IngestRequest
from app.kip.service import KipService
from app.main import app
from app.rsp.flags import RspFlags
from app.rsp.models import CommitteeRequest, EngineBundle, ReasonRequest, SynthesizeRequest
from app.rsp.service import RspService


AGI = """
ICICI Bank — AGI Research
2026-01-15
Investment Thesis
ICICIBANK is AGI preferred private bank on deposit franchise.
Target price Rs 1400. Expected return 18%.

Bull Case
- Credit growth above 18%

Bear Case
- Unsecured stress

Risks
- Asset quality deterioration

Catalysts
- Q3 earnings
"""

BROKER_BEAR = """
Broker Research ICICIBANK Downgrade
Broker: Motilal
We downgrade ICICIBANK to Sell / Underweight.
Target price Rs 1100.
Bear Case
- Rich valuations
Bull Case
- Franchise quality
"""


def _seed_kip() -> KipService:
    kip = KipService()
    kip.ingest_agi(
        IngestRequest(
            title="AGI ICICI",
            content=AGI,
            tickers=["ICICIBANK"],
            date=date(2026, 1, 15),
            article_id="rsp_agi_1",
            document_type=DocumentType.AGI_RESEARCH,
        )
    )
    kip.ingest_broker(
        IngestRequest(
            title="Broker bear ICICI",
            content=BROKER_BEAR,
            tickers=["ICICIBANK"],
            date=date(2026, 2, 20),
            broker="Motilal",
        )
    )
    return kip


def _svc(kip: KipService | None = None, **flag_kw) -> RspService:
    flags = RspFlags(
        rsp=flag_kw.get("rsp", True),
        rsp_consensus=flag_kw.get("rsp_consensus", True),
        rsp_contradictions=flag_kw.get("rsp_contradictions", True),
        rsp_reasoning=flag_kw.get("rsp_reasoning", True),
    )
    return RspService(flags=flags, kip=kip or _seed_kip())


def test_reason_pipeline_builds_package():
    svc = _svc()
    pkg = svc.reason(
        ReasonRequest(
            question="What is the institutional view on ICICIBANK?",
            ticker="ICICIBANK",
            engines=EngineBundle(
                e01={"regime": "risk_on", "confidence": 0.7},
                e13={"side": "long", "confidence": 0.65},
                e11={"label": "positive", "side": "bullish", "confidence": 0.6},
                l4={"side": "long", "confidence": 0.62},
                e10={"ICICIBANK": 0.04},
            ),
        )
    )
    assert pkg.reasoning_id
    assert pkg.answer_policy == "rsp_reasons_before_llm"
    assert pkg.reasoning_version == "rsp-v1.0.1"
    assert "retrieve" in pkg.pipeline_stages
    assert "generate_reasoning_package" in pkg.pipeline_stages
    assert pkg.facts or pkg.opinions
    assert pkg.evidence
    assert pkg.consensus.agi_view
    assert pkg.synthesis.investment_thesis
    assert pkg.synthesis.evidence_tree
    assert pkg.validation.evidence_tree
    assert pkg.validation.reasoning_version == "rsp-v1.0.1"
    assert 0 <= pkg.confidence <= 1
    assert 0 <= pkg.validation.freshness <= 1
    # Contract: structured reasoning only — no full raw document dump fields
    dumped = pkg.model_dump(mode="json")
    assert "cleaned_content" not in dumped
    assert "content" not in dumped
    assert all("cleaned_content" not in e for e in dumped["evidence"])


def test_contradictions_and_consensus():
    svc = _svc()
    pkg = svc.committee(
        CommitteeRequest(
            question="ICICIBANK buy or sell?",
            ticker="ICICIBANK",
            engines=EngineBundle(
                e01={"regime": "risk_off"},
                e09={"side": "long", "trend": "up"},
                e05={"side": "negative", "label": "bearish_event"},
                e13={"side": "long"},
                l4={"side": "long", "confidence": 0.55},
            ),
        )
    )
    kinds = {c.kind for c in pkg.contradictions}
    assert kinds  # at least AGI vs broker or macro/technicals etc.
    assert pkg.consensus.broker_consensus
    assert pkg.consensus.contrarian_view
    assert isinstance(pkg.consensus.unknown_areas, list)
    assert pkg.opinion_clusters


def test_change_detection_from_house_view():
    kip = _seed_kip()
    kip.ingest_agi(
        IngestRequest(
            title="AGI update",
            content=AGI.replace("Target price Rs 1400", "Target price Rs 1350").replace(
                "preferred private bank", "still constructive but less compelling"
            ),
            tickers=["ICICIBANK"],
            date=date(2026, 3, 5),
            article_id="rsp_agi_1",
        )
    )
    svc = _svc(kip=kip)
    pkg = svc.reason(ReasonRequest(question="What changed for ICICIBANK?", ticker="ICICIBANK"))
    cont = pkg.research_continuity
    assert cont.what_changed or cont.what_stayed_the_same or cont.strengthens_thesis or cont.weakens_thesis


def test_evidence_model_fields():
    svc = _svc()
    pkg = svc.reason(ReasonRequest(question="ICICIBANK thesis", ticker="ICICIBANK"))
    e = pkg.evidence[0]
    for field in (
        "source",
        "reliability",
        "freshness",
        "confidence",
        "supporting_documents",
        "contradicting_documents",
        "engine_support",
        "house_view_alignment",
    ):
        assert hasattr(e, field)
    stored = svc.get_evidence(e.evidence_id)
    assert stored is not None
    got = svc.get_reasoning(pkg.reasoning_id)
    assert got is not None
    assert got.reasoning_id == pkg.reasoning_id


def test_reason_for_writer_omits_raw_documents():
    svc = _svc()
    payload = svc.reason_for_writer("ICICIBANK institutional view", ticker="ICICIBANK")
    assert payload["raw_documents_included"] is False
    assert "synthesis" in payload
    assert "validation" in payload
    assert "content" not in payload
    assert "cleaned_content" not in payload


def test_synthesize_by_id_and_flags():
    svc = _svc()
    pkg = svc.reason(ReasonRequest(question="ICICIBANK", ticker="ICICIBANK"))
    again = svc.synthesize(SynthesizeRequest(reasoning_id=pkg.reasoning_id, question="ICICIBANK refresh"))
    assert again.synthesis.investment_thesis

    disabled = _svc(rsp=False)
    with pytest.raises(RuntimeError, match="RSP is disabled"):
        disabled.reason(ReasonRequest(question="x"))

    no_reason = _svc(rsp_reasoning=False)
    with pytest.raises(RuntimeError, match="RSP_REASONING"):
        no_reason.reason(ReasonRequest(question="x", ticker="ICICIBANK"))


def test_no_engine_redesign_surface():
    import app.engines as engines
    import app.rsp as rsp

    assert hasattr(rsp, "RspService")
    assert not hasattr(engines, "rsp")


@pytest.mark.asyncio
async def test_rsp_http_apis():
    # Seed shared app kip via ingest API so RSP can resolve context
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/rsp/health")
        assert health.status_code == 200
        body = health.json()
        assert body["platform"] == "RSP"
        assert body["flags"]["RSP"] is True
        assert "KIP retrieves" in body["contract"]

        await client.post(
            "/v1/kip/ingest/agi",
            json={
                "title": "AGI ICICI",
                "content": AGI,
                "tickers": ["ICICIBANK"],
                "date": "2026-01-15",
                "article_id": "http_rsp_1",
            },
        )
        await client.post(
            "/v1/kip/ingest/broker",
            json={
                "title": "Broker bear",
                "content": BROKER_BEAR,
                "tickers": ["ICICIBANK"],
                "date": "2026-02-20",
                "broker": "Motilal",
            },
        )

        reason = await client.post(
            "/v1/rsp/reason",
            json={
                "question": "ICICIBANK house view vs brokers",
                "ticker": "ICICIBANK",
                "engines": {
                    "e01": {"regime": "risk_on"},
                    "e13": {"side": "long"},
                    "l4": {"side": "long", "confidence": 0.6},
                    "e10": {"ICICIBANK": 0.03},
                },
            },
        )
        assert reason.status_code == 200, reason.text
        pkg = reason.json()
        assert pkg["validation"]["evidence_tree"]
        assert pkg["validation"]["supporting_documents"] is not None
        rid = pkg["reasoning_id"]

        got = await client.get(f"/v1/rsp/reasoning/{rid}")
        assert got.status_code == 200

        eid = pkg["evidence"][0]["evidence_id"]
        ev = await client.get(f"/v1/rsp/evidence/{eid}")
        assert ev.status_code == 200

        synth = await client.post("/v1/rsp/synthesize", json={"reasoning_id": rid})
        assert synth.status_code == 200

        committee = await client.post(
            "/v1/rsp/committee",
            json={"question": "Committee on ICICIBANK", "ticker": "ICICIBANK"},
        )
        assert committee.status_code == 200
        assert committee.json()["synthesis"]["research_brief"]
