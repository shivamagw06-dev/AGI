"""RMS P0 — Research Management System."""

from __future__ import annotations

from datetime import date

import pytest
from httpx import ASGITransport, AsyncClient

from app.kip.models import DocumentType, IngestRequest
from app.kip.service import KipService
from app.main import app
from app.rms.flags import RmsFlags
from app.rms.models import (
    ApproveRequest,
    DraftRequest,
    PublishRequest,
    ResearchRequestCreate,
    ResearchStatus,
    ReviewDecision,
    ReviewRequest,
    ReviewType,
)
from app.rms.service import RmsService
from app.rms.workflow import WorkflowError
from app.rsp.service import RspService


def _stack() -> tuple[KipService, RspService, RmsService]:
    kip = KipService()
    kip.ingest_agi(
        IngestRequest(
            title="Prior AGI ICICI",
            content=(
                "ICICIBANK AGI research\nInvestment Thesis\nPreferred private bank.\n"
                "Target price Rs 1400.\nBull Case\n- Credit growth\nBear Case\n- Stress\n"
                "Risks\n- Asset quality\nCatalysts\n- Earnings"
            ),
            tickers=["ICICIBANK"],
            date=date(2026, 1, 15),
            article_id="rms_prior_1",
            document_type=DocumentType.AGI_RESEARCH,
        )
    )
    kip.ingest_broker(
        IngestRequest(
            title="Broker note",
            content="ICICIBANK broker upgrade Buy Target price Rs 1500",
            tickers=["ICICIBANK"],
            date=date(2026, 2, 1),
            broker="Kotak",
        )
    )
    rsp = RspService(kip=kip)
    rms = RmsService(kip=kip, rsp=rsp)
    return kip, rsp, rms


def test_full_lifecycle_idea_to_publish():
    kip, _, rms = _stack()
    obj = rms.create_request(
        ResearchRequestCreate(
            title="ICICI Bank Update",
            owner="analyst_a",
            reviewer="reviewer_b",
            tickers=["ICICIBANK"],
            sectors=["Financials"],
            themes=["credit_growth"],
            request_brief="Update house view on ICICIBANK after Q3",
            prediction_horizon="180d",
            engine_snapshot={
                "e01": {"regime": "risk_on"},
                "e13": {"side": "long", "confidence": 0.6},
                "l4": {"side": "long", "confidence": 0.62},
                "e10": {"ICICIBANK": 0.04},
            },
        )
    )
    assert obj.status == ResearchStatus.DRAFT
    assert obj.version == 1
    assert obj.owner == "analyst_a"
    assert obj.evidence_package.get("documents_retrieved") is not None or obj.evidence_package.get("status")
    assert obj.reasoning_package
    assert obj.reasoning_id or obj.reasoning_package.get("reasoning_id") or obj.reasoning_package.get("synthesis")
    assert obj.house_view is not None
    assert "l4" in obj.engine_snapshot

    obj = rms.create_or_update_draft(
        DraftRequest(
            research_id=obj.research_id,
            draft_body="Draft body with institutional thesis on ICICIBANK.",
            submit_for_review=True,
        )
    )
    assert obj.status == ResearchStatus.INTERNAL_REVIEW
    assert "Draft body" in obj.draft_body

    obj = rms.review(
        ReviewRequest(
            research_id=obj.research_id,
            author="reviewer_b",
            body="Looks good — advance to compliance",
            decision=ReviewDecision.APPROVE,
            review_type=ReviewType.INTERNAL,
        )
    )
    assert obj.status == ResearchStatus.COMPLIANCE_REVIEW
    assert obj.compliance.review_history

    obj = rms.approve(
        ApproveRequest(research_id=obj.research_id, approver="compliance_c", notes="Cleared")
    )
    assert obj.status == ResearchStatus.APPROVED
    assert any(a.decision == "approved" for a in obj.compliance.approvals)

    published = rms.publish(
        PublishRequest(research_id=obj.research_id, actor="publisher_d")
    )
    assert published.status == ResearchStatus.PUBLISHED
    assert published.published_at is not None
    assert published.compliance.publication_timestamp is not None
    channels = {a.channel for a in published.publication_artifacts}
    assert {"website", "newsletter", "linkedin", "internal_archive"} <= channels
    assert published.kip_document_ids
    # KIP received the published article
    doc = kip.get_document(published.kip_document_ids[0])
    assert doc is not None
    assert doc.article_id == published.research_id
    assert published.prediction_ids or kip.predictions("ICICIBANK")


def test_revision_and_reject_paths():
    _, _, rms = _stack()
    obj = rms.create_request(
        ResearchRequestCreate(
            title="Revision case",
            owner="a",
            tickers=["ICICIBANK"],
            request_brief="ICICIBANK note",
        )
    )
    obj = rms.create_or_update_draft(
        DraftRequest(research_id=obj.research_id, draft_body="v1 draft", submit_for_review=True)
    )
    obj = rms.review(
        ReviewRequest(
            research_id=obj.research_id,
            author="rev",
            body="Needs more risks",
            decision=ReviewDecision.REQUEST_REVISION,
            review_type=ReviewType.INTERNAL,
        )
    )
    assert obj.status == ResearchStatus.REVISION_REQUESTED
    obj = rms.create_or_update_draft(
        DraftRequest(research_id=obj.research_id, draft_body="v2 draft with risks", owner="a")
    )
    assert obj.status == ResearchStatus.DRAFT
    assert obj.version == 2

    obj = rms.create_or_update_draft(
        DraftRequest(research_id=obj.research_id, submit_for_review=True)
    )
    obj = rms.review(
        ReviewRequest(
            research_id=obj.research_id,
            author="rev",
            body="Reject — insufficient evidence",
            decision=ReviewDecision.REJECT,
            review_type=ReviewType.INTERNAL,
        )
    )
    assert obj.status == ResearchStatus.REJECTED


def test_publish_requires_approval():
    _, _, rms = _stack()
    obj = rms.create_request(
        ResearchRequestCreate(title="No approve", owner="a", tickers=["ICICIBANK"])
    )
    with pytest.raises(WorkflowError, match="approved"):
        rms.publish(PublishRequest(research_id=obj.research_id))


def test_dashboard_coverage():
    _, _, rms = _stack()
    rms.create_request(
        ResearchRequestCreate(
            title="A",
            owner="a",
            tickers=["ICICIBANK"],
            sectors=["Financials"],
        )
    )
    obj = rms.create_request(
        ResearchRequestCreate(
            title="B",
            owner="b",
            tickers=["HDFCBANK", "ICICIBANK"],
            sectors=["Financials"],
        )
    )
    obj = rms.create_or_update_draft(
        DraftRequest(research_id=obj.research_id, submit_for_review=True)
    )
    dash = rms.dashboard()
    assert dash.totals["research_objects"] >= 2
    assert dash.research_pipeline.draft + dash.research_pipeline.internal_review >= 1
    assert "ICICIBANK" in dash.company_coverage
    assert "Financials" in dash.sector_coverage
    assert isinstance(dash.draft_queue, list)
    assert isinstance(dash.review_queue, list)


def test_flags():
    kip, rsp, _ = _stack()
    disabled = RmsService(flags=RmsFlags(rms=False), kip=kip, rsp=rsp)
    with pytest.raises(RuntimeError, match="RMS is disabled"):
        disabled.create_request(ResearchRequestCreate(title="x", owner="a"))

    no_pub = RmsService(
        flags=RmsFlags(rms=True, rms_review=True, rms_approval=True, rms_publish=False),
        kip=kip,
        rsp=rsp,
    )
    obj = no_pub.create_request(
        ResearchRequestCreate(title="x", owner="a", tickers=["ICICIBANK"])
    )
    obj = no_pub.create_or_update_draft(
        DraftRequest(research_id=obj.research_id, submit_for_review=True)
    )
    obj = no_pub.approve(ApproveRequest(research_id=obj.research_id, approver="c"))
    with pytest.raises(RuntimeError, match="RMS_PUBLISH"):
        no_pub.publish(PublishRequest(research_id=obj.research_id))


def test_no_engine_redesign_surface():
    import app.engines as engines
    import app.rms as rms

    assert hasattr(rms, "RmsService")
    assert not hasattr(engines, "rms")


@pytest.mark.asyncio
async def test_rms_http_apis():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/rms/health")
        assert health.status_code == 200
        assert health.json()["platform"] == "RMS"
        assert health.json()["flags"]["RMS"] is True

        # Seed KIP via API for knowledge collection
        await client.post(
            "/v1/kip/ingest/agi",
            json={
                "title": "Prior",
                "content": "ICICIBANK investment thesis preferred bank target Rs 1400",
                "tickers": ["ICICIBANK"],
                "date": "2026-01-15",
                "article_id": "http_rms_prior",
            },
        )

        req = await client.post(
            "/v1/rms/request",
            json={
                "title": "HTTP ICICI research",
                "owner": "analyst",
                "tickers": ["ICICIBANK"],
                "sectors": ["Financials"],
                "request_brief": "Institutional update on ICICIBANK",
                "engine_snapshot": {"l4": {"side": "long"}, "e10": {"ICICIBANK": 0.02}},
            },
        )
        assert req.status_code == 200, req.text
        rid = req.json()["research_id"]
        assert req.json()["status"] == "draft"

        draft = await client.post(
            "/v1/rms/draft",
            json={"research_id": rid, "draft_body": "Polished draft", "submit_for_review": True},
        )
        assert draft.status_code == 200
        assert draft.json()["status"] == "internal_review"

        review = await client.post(
            "/v1/rms/review",
            json={
                "research_id": rid,
                "author": "rev",
                "body": "OK",
                "decision": "approve",
                "review_type": "internal",
            },
        )
        assert review.status_code == 200

        approve = await client.post(
            "/v1/rms/approve",
            json={"research_id": rid, "approver": "comp", "notes": "Approved"},
        )
        assert approve.status_code == 200
        assert approve.json()["status"] == "approved"

        publish = await client.post(
            "/v1/rms/publish",
            json={"research_id": rid, "actor": "pub"},
        )
        assert publish.status_code == 200, publish.text
        body = publish.json()
        assert body["status"] == "published"
        assert body["kip_document_ids"]
        assert body["publication_artifacts"]

        got = await client.get(f"/v1/rms/research/{rid}")
        assert got.status_code == 200
        assert got.json()["compliance"]["publication_timestamp"]

        dash = await client.get("/v1/rms/dashboard")
        assert dash.status_code == 200
        assert dash.json()["research_pipeline"]["published"] >= 1
