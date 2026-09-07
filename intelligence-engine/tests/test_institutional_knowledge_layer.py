"""IKL — Institutional Knowledge Intelligence Layer."""

from __future__ import annotations

import os
from pathlib import Path

import pytest


@pytest.fixture()
def ikl_tmpdir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AGIB_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("IKL_ENABLED", "1")
    monkeypatch.setenv("IKL_WRITEBACK_ENABLED", "1")
    monkeypatch.setenv("IKL_ASK_CONSULT_ENABLED", "1")
    monkeypatch.setenv("IKL_DELTA_ENABLED", "1")
    return tmp_path


def test_health(ikl_tmpdir):
    from institutional_knowledge_layer.production import health

    h = health()
    assert h["status"] == "ok"
    assert h["engine"] == "IKL"
    assert "company_memory" in h["ask_retrieval_order"]
    assert h["ask_retrieval_order"][0] == "company_memory"
    assert h["ask_retrieval_order"][-1] == "live_search"
    assert h["not_a_second_knowledge_system"] is True
    assert h["issues_recommendations"] is False


def test_extract_and_writeback_updates_company_memory(ikl_tmpdir):
    from institutional_knowledge_layer.memory.company import read_company_memory
    from institutional_knowledge_layer.production import ask_consult, on_document

    doc = {
        "document_id": "doc-rel-1",
        "title": "Reliance Industries Q2 earnings",
        "ticker": "RELIANCE",
        "source_channel": "research_note",
        "text": (
            "RELIANCE reported strong revenue growth in retail and Jio segments. "
            "Management guided for higher capex in FY26. "
            "Key risks include oil volatility and regulatory headwinds. "
            "Opportunities remain in digital and new energy expansion. "
            "EBITDA margin improved year on year."
        ),
        "themes": ["digital", "energy"],
        "industry": "Conglomerate",
        "sectors": ["Energy", "Telecom"],
        "competitors": ["ONGC", "AIRTEl"],
    }
    result = on_document(doc)
    assert result.get("ok") is True
    assert "RELIANCE" in (result.get("companies_updated") or [])

    mem = read_company_memory("RELIANCE")
    assert mem is not None
    assert mem["update_count"] >= 1
    slots = mem["slots"]
    assert slots["document_timeline"]
    assert slots.get("key_risks") or slots.get("latest_guidance") or slots.get("historical_kpis")
    assert any("risk" in str(r).lower() or "oil" in str(r).lower() for r in (slots.get("key_risks") or [])) or slots.get(
        "latest_guidance"
    ) or slots.get("historical_kpis")

    # Incremental — second doc must not wipe prior timeline
    doc2 = {
        **doc,
        "document_id": "doc-rel-2",
        "title": "Reliance strategy update",
        "text": (
            "RELIANCE revised guidance upward for retail. "
            "CEO outlined capital allocation toward new energy. "
            "Margin expansion remains a valuation driver."
        ),
    }
    r2 = on_document(doc2)
    assert r2.get("ok") is True
    mem2 = read_company_memory("RELIANCE")
    assert mem2["update_count"] >= 2
    assert len(mem2["slots"]["document_timeline"]) >= 2

    pack = ask_consult("What is the outlook for Reliance?", ticker="RELIANCE")
    assert pack.get("enabled") is True
    assert "company_memory" in (pack.get("layers_hit") or [])
    assert "RELIANCE" in (pack.get("company_memory") or {})
    expl = pack.get("explainability") or {}
    assert "RELIANCE" in (expl.get("company_memory_used") or [])
    assert "confidence" in expl
    assert "reasoning_path" in expl
    assert pack.get("primary_before_raw_documents") is True
    assert pack.get("recommendation_policy") == "memory_evidence_only_no_buy_sell"


def test_industry_and_macro_memory(ikl_tmpdir):
    from institutional_knowledge_layer.memory.industry import read_industry_memory
    from institutional_knowledge_layer.memory.macro import read_macro_memory
    from institutional_knowledge_layer.production import on_document

    doc = {
        "document_id": "macro-1",
        "title": "RBI monetary policy and steel sector",
        "text": (
            "The RBI kept the repo rate unchanged amid sticky inflation. "
            "Steel producers face higher power costs. "
            "PLI scheme continues to benefit manufacturing. "
            "GDP growth outlook remains resilient."
        ),
        "industry": "Steel",
        "tickers": ["JSWSTEEL"],
        "commodities": ["steel", "power"],
    }
    out = on_document(doc)
    assert out.get("ok") is True
    ind = read_industry_memory("Steel")
    assert ind is not None
    assert ind["update_count"] >= 1
    # at least one macro topic should land
    topics_hit = out.get("macro_updated") or []
    assert topics_hit
    for t in topics_hit:
        m = read_macro_memory(t)
        assert m is not None


def test_graph_edges(ikl_tmpdir):
    from institutional_knowledge_layer.graph import neighbors, package_for_ask
    from institutional_knowledge_layer.production import on_document

    on_document(
        {
            "document_id": "g1",
            "title": "TCS competes with Infosys",
            "ticker": "TCS",
            "industry": "IT Services",
            "competitors": ["INFY"],
            "text": "TCS competes with INFY in IT services. Revenue and EBITDA trends remain healthy.",
            "themes": ["digital transformation"],
        }
    )
    edges = neighbors(entity_type="company", entity_id="TCS")
    assert edges
    pack = package_for_ask(company_ids=["TCS"], industries=["IT Services"])
    assert pack["edge_count"] >= 1


def test_ask_pipeline_knowledge_includes_ikl(ikl_tmpdir, monkeypatch):
    from institutional_knowledge_layer.production import on_document

    on_document(
        {
            "document_id": "ask-1",
            "ticker": "HDFCBANK",
            "title": "HDFC Bank earnings",
            "text": "HDFCBANK NIM expanded. Guidance for loan growth raised. Key risks include NPA cycles.",
            "industry": "Banks",
        }
    )
    from ask_pipeline.knowledge import retrieve_knowledge

    bag = retrieve_knowledge(
        intent="CompanyAnalysis",
        entities=[{"type": "company", "id": "HDFCBANK"}],
        question="How is HDFC Bank performing?",
    )
    assert "institutional_knowledge" in bag
    ikl = bag["institutional_knowledge"]
    assert ikl.get("enabled") is True
    assert "ikl" in str(bag.get("primary_engine") or "")


def test_writeback_disabled_soft(ikl_tmpdir, monkeypatch):
    monkeypatch.setenv("IKL_WRITEBACK_ENABLED", "0")
    from institutional_knowledge_layer.production import on_document

    out = on_document({"document_id": "x", "text": "hello", "ticker": "TCS"})
    assert out.get("skipped") is True
