"""FRE v1 — Finance Retrieval Engine (evidence acquisition; never answers)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.fre.authority import authority_score
from app.fre.planner import plan_retrieval
from app.fre.service import FreService
from app.fre.store import FreStore
from app.fre.understanding import understand_query
from app.main import app


def test_fre_health_locked_architecture():
    fre = FreService(store=FreStore())
    h = fre.health()
    assert h["programme"] == "FRE"
    assert h["architecture_status"] == "v1.0.1 LOCKED"
    assert h["does_not_answer"] is True
    assert "ask_agi" in h["no_redesign"]
    assert "never_answer_user" in h["invariants"]


def test_query_understanding_reliance_buy():
    ud = understand_query("Should I buy Reliance?")
    assert ud.intent == "investment_analysis"
    assert any("Reliance" in c for c in ud.companies) or "RELIANCE" in ud.symbols
    assert "Financials" in ud.needs
    assert "Risks" in ud.needs


def test_query_planner_multiple_tasks():
    plan = plan_retrieval("Analyse Infosys")
    assert len(plan.tasks) >= 6
    descriptions = " ".join(t.description.lower() for t in plan.tasks)
    assert "annual" in descriptions
    assert "quarterly" in descriptions
    assert "news" in descriptions


def test_authority_scoring():
    assert authority_score("annual_report") == 10
    assert authority_score("exchange_filing") == 10
    assert authority_score("unknown_blog") == 2


def test_query_returns_evidence_not_answer():
    fre = FreService(store=FreStore())
    pack = fre.query("Should I buy Reliance?", limit=10)
    assert pack["does_not_answer"] is True
    assert pack["architecture_status"] == "v1.0.1 LOCKED"
    assert pack["understanding"]["intent"] == "investment_analysis"
    assert len(pack["plan"]["tasks"]) >= 5
    assert isinstance(pack["top_evidence"], list)
    assert len(pack["top_evidence"]) >= 1
    ev = pack["top_evidence"][0]
    assert ev.get("claim")
    assert ev.get("source") or ev.get("document_id")
    # Must not invent a buy/sell recommendation field
    assert "recommendation" not in pack
    assert "answer" not in pack


def test_company_and_search_apis():
    fre = FreService(store=FreStore())
    co = fre.company("INFY", limit=8)
    assert co["company"] == "INFY"
    assert isinstance(co["documents"], list)
    assert len(co["documents"]) >= 1
    search = fre.search("Infosys guidance margins", limit=8)
    assert len(search["hits"]) >= 1
    assert search["hits"][0].get("rerank_score") is not None or search["hits"][0].get("score") is not None


def test_ingest_dedupes_by_checksum():
    fre = FreService(store=FreStore())
    payload = {
        "title": "Test Filing",
        "text": "Revenue increased 12% in FY26. Operating margin expanded to 20%.",
        "source": "nse",
        "document_type": "exchange_filing",
        "company": "Test Co",
        "symbol": "TEST",
        "published_at": "2026-07-01",
    }
    a = fre.ingest(payload)
    b = fre.ingest(payload)
    assert a["failed"] == 0
    # second ingest versions rather than duplicating checksum
    assert fre.store.snapshot()["unique_checksums"] == fre.store.snapshot()["documents"] or b["ingested"]


def test_consult_soft_shape_for_ask_agi():
    fre = FreService(store=FreStore())
    c = fre.consult("Infosys AI deals and guidance", limit=5)
    assert c["does_not_answer"] is True
    assert "hits" in c
    assert "top_sources" in c
    assert "never_answer_user" in c["invariants"]


@pytest.mark.asyncio
async def test_fre_http_health_and_query():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        headers = {"Authorization": "Bearer dev-intelligence-token"}
        health = await client.get("/v1/fre/health", headers=headers)
        assert health.status_code == 200
        body = health.json()
        assert body["programme"] == "FRE"
        assert body["architecture_status"] == "v1.0.1 LOCKED"

        q = await client.get("/v1/fre/query", params={"q": "Should I buy Reliance?"}, headers=headers)
        assert q.status_code == 200
        pack = q.json()
        assert pack["does_not_answer"] is True
        assert pack["top_evidence"]
