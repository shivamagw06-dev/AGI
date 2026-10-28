"""IERE Track 5 — Institutional Evidence Retrieval Engine acceptance tests."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from evidence_retrieval import store
from evidence_retrieval.assembly import assemble_packs
from evidence_retrieval.citations import attach_citations, citation_coverage
from evidence_retrieval.discovery import discover
from evidence_retrieval.graph import build_evidence_graph
from evidence_retrieval.pipeline import retrieve_evidence
from evidence_retrieval.production import company, dashboard, document, health, replay, search
from evidence_retrieval.quality import evaluate_retrieval_gates
from evidence_retrieval.ranking import rank_evidence
from evidence_retrieval.schema import FREEZE_LOCKS, IERE_VERSION, PACK_KINDS

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("IERE_STORE_ROOT", str(tmp_path / "iere"))
    store.reset()
    yield
    store.reset()


def _synth_items() -> list[dict]:
    return [
        {
            "evidence_id": "fin_infy",
            "evidence_type": "FINANCIAL_METRICS",
            "knowledge_object": "CompanyIntelligenceObject",
            "source": "knowledge_factory",
            "collector": "company_intelligence",
            "company": "INFY",
            "title": "INFY revenue and margins",
            "payload": {"revenue": "known"},
            "confidence": 0.9,
            "available_from": "2024-06-01",
            "checksum": "abc",
            "version": "1",
        },
        {
            "evidence_id": "evt_infy",
            "evidence_type": "CORPORATE_EVENTS",
            "knowledge_object": "CorporateEventObject",
            "source": "NSE",
            "collector": "corporate_events",
            "company": "INFY",
            "title": "INFY dividend announcement",
            "payload": {"event_type": "DIVIDEND"},
            "confidence": 0.85,
            "available_from": "2024-07-01",
            "version": "1",
        },
        {
            "evidence_id": "gov_1",
            "evidence_type": "GOVERNMENT_POLICIES",
            "knowledge_object": "GovernmentIntelligenceObject",
            "source": "SEBI",
            "collector": "government_intelligence",
            "title": "SEBI listing policy",
            "payload": {"topic": "listing"},
            "confidence": 0.8,
            "available_from": "2024-01-01",
            "version": "1",
        },
        {
            "evidence_id": "macro_1",
            "evidence_type": "MACRO_INDICATORS",
            "knowledge_object": "MacroObject",
            "source": "RBI",
            "collector": "macro_intelligence",
            "title": "RBI repo rate",
            "payload": {"repo": "known"},
            "confidence": 0.88,
            "available_from": "2024-05-01",
            "version": "1",
        },
        {
            "evidence_id": "doc_1",
            "evidence_type": "RISK_FACTORS",
            "knowledge_object": "AnnualReportObject",
            "source": "institutional_documents",
            "collector": "idi",
            "company": "INFY",
            "title": "INFY annual report / Risk Factors",
            "payload": {"text": "Currency risk remains material"},
            "confidence": 0.92,
            "available_from": "2024-06-15",
            "document_id": "doc_infy_ar",
            "section": "RISK_FACTORS",
            "page": 42,
            "paragraph": 3,
            "checksum": "chk1",
            "version": "1",
        },
        {
            "evidence_id": "ind_1",
            "evidence_type": "RELATIONSHIP_GRAPH",
            "knowledge_object": "IndustryIntelligenceObject",
            "source": "knowledge_factory",
            "collector": "industry_intelligence",
            "company": "INFY",
            "title": "IT services industry structure",
            "payload": {"peers": ["TCS", "WIPRO"]},
            "confidence": 0.7,
            "available_from": "2024-03-01",
            "version": "1",
        },
        {
            "evidence_id": "fut_1",
            "evidence_type": "FINANCIAL_METRICS",
            "knowledge_object": "LiveMarketObject",
            "source": "live_data",
            "collector": "lidi",
            "company": "INFY",
            "title": "future leaked quote",
            "payload": {},
            "confidence": 0.5,
            "available_from": "2099-01-01",
            "version": "1",
        },
    ]


def test_health_and_freeze_locks() -> None:
    h = health()
    assert h["status"] == "ok"
    assert h["version"] == IERE_VERSION
    assert h["deterministic_ranking"] is True
    assert FREEZE_LOCKS["reasoning"] is True
    assert FREEZE_LOCKS["governance"] is True
    assert FREEZE_LOCKS["never_pdf_to_reasoning"] is True


def test_discovery_intent_entities() -> None:
    d = discover("How does INFY revenue compare after the SEBI policy and RBI repo move?", ticker_hint="INFY")
    assert "INFY" in d["companies"]
    assert "FINANCIAL_METRICS" in d["evidence_types_required"]
    assert "government" in d["topics"] or "GOVERNMENT_POLICIES" in d["evidence_types_required"]
    assert d["fabricated"] is False


def test_company_industry_government_macro_document_retrieval(monkeypatch) -> None:
    monkeypatch.setattr(
        "evidence_retrieval.pipeline.discover_candidates",
        lambda discovery: [i for i in _synth_items() if i["available_from"] <= "2025-01-01"],
    )
    out = company("INFY")
    assert out["ok"] or out["ranked_count"] >= 1
    types = {r["evidence_type"] for r in out["ranked"]}
    assert "FINANCIAL_METRICS" in types
    assert "RELATIONSHIP_GRAPH" in types or any(p["kind"] == "INDUSTRY_EVIDENCE_PACK" for p in out["packs"])
    assert "GOVERNMENT_POLICIES" in types
    assert "MACRO_INDICATORS" in types
    assert any(r.get("document_id") for r in out["ranked"])
    assert out["reasoning_changed"] is False
    assert out["ask_envelope"]["pdf_sent_to_reasoning"] is False


def test_ranking_deterministic() -> None:
    discovery = discover("INFY financials and risk factors", ticker_hint="INFY", as_of="2024-12-01")
    items = [i for i in _synth_items() if i["available_from"] <= "2024-12-01"]
    a = rank_evidence(items, discovery=discovery, as_of="2024-12-01")
    b = rank_evidence(items, discovery=discovery, as_of="2024-12-01")
    assert [x["evidence_id"] for x in a] == [x["evidence_id"] for x in b]
    assert a[0]["rank"] == 1
    assert a[0]["ranking_engine"] == "iere_deterministic_v1"
    assert a[0]["rank_score"] >= a[-1]["rank_score"]


def test_provenance_and_citation_integrity() -> None:
    discovery = discover("INFY annual report risk factors", ticker_hint="INFY")
    ranked = attach_citations(rank_evidence(_synth_items()[:5], discovery=discovery))
    cov = citation_coverage(ranked)
    assert cov["coverage"] == 1.0
    cit = ranked[-1]["citation"] if ranked[-1].get("document_id") else next(
        r["citation"] for r in ranked if r.get("document_id")
    )
    assert cit["source"]
    assert cit["knowledge_object"]
    assert cit["document_id"] or cit["document"]
    assert cit["checksum"]
    assert cit["page"] == 42


def test_evidence_assembly_packs() -> None:
    discovery = discover("INFY portfolio holdings industry macro government", ticker_hint="INFY")
    discovery["portfolio_context"] = True
    ranked = attach_citations(rank_evidence(_synth_items()[:6], discovery=discovery, as_of="2024-12-01"))
    packs = assemble_packs(ranked, retrieval_id="test1", discovery=discovery)
    kinds = {p["kind"] for p in packs}
    assert "COMPANY_EVIDENCE_PACK" in kinds
    assert "DOCUMENT_EVIDENCE_PACK" in kinds
    assert kinds.issubset(set(PACK_KINDS))
    for p in packs:
        assert p["conclusions"] is None
        assert p["recommendation"] is None
        assert p["reasoning"] is False


def test_historical_replay_no_future_leakage(monkeypatch) -> None:
    monkeypatch.setattr(
        "evidence_retrieval.pipeline.discover_candidates",
        lambda discovery: list(_synth_items()),
    )
    out = replay(question="INFY financials", as_of="2024-06-30", ticker="INFY")
    assert out["replay"]["ok"] is True
    assert out["replay"]["future_leakage"] is False
    for r in out["ranked"]:
        assert str(r["available_from"])[:10] <= "2024-06-30"
    assert not any(r["evidence_id"] == "fut_1" for r in out["ranked"])


def test_graph_and_quality_gates() -> None:
    discovery = discover("INFY evidence", ticker_hint="INFY", as_of="2024-12-01")
    ranked = attach_citations(
        [r for r in rank_evidence(_synth_items()[:6], discovery=discovery, as_of="2024-12-01") if not r.get("duplicate")]
    )
    packs = assemble_packs(ranked, retrieval_id="g1", discovery=discovery)
    graph = build_evidence_graph(
        retrieval_id="g1",
        discovery=discovery,
        ranked=ranked,
        pack_ids=[p["pack_id"] for p in packs],
    )
    assert graph["nodes"]
    assert graph["edges"]
    for e in graph["edges"]:
        assert e.get("source") is not None
        assert e.get("weight") is not None
        assert e.get("confidence") is not None
    gates = evaluate_retrieval_gates(ranked=ranked, packs=packs, graph=graph, as_of="2024-12-01")
    assert "future_leakage" not in gates["failures"]
    assert "broken_graph" not in gates["failures"]
    assert "missing_provenance" not in gates["failures"]


def test_document_api_path(monkeypatch) -> None:
    monkeypatch.setattr(
        "evidence_retrieval.pipeline.discover_candidates",
        lambda discovery: list(_synth_items()),
    )
    # Full search then document filter
    search("INFY annual report", ticker="INFY")
    out = document("doc_infy_ar")
    assert out["document_id"] == "doc_infy_ar"
    assert out["n"] >= 1


def test_dashboard_metrics(monkeypatch) -> None:
    monkeypatch.setattr(
        "evidence_retrieval.pipeline.discover_candidates",
        lambda discovery: [i for i in _synth_items() if i["available_from"] <= "2025-01-01"],
    )
    retrieve_evidence("INFY institutional evidence", ticker_hint="INFY", as_of="2024-12-01")
    dash = dashboard()
    assert "evidence_coverage" in dash
    assert "evidence_freshness" in dash
    assert "citation_coverage" in dash
    assert "replay_health" in dash
    assert "evidence_confidence" in dash


def test_ask_integration_soft_wire(monkeypatch) -> None:
    monkeypatch.setattr(
        "evidence_retrieval.pipeline.discover_candidates",
        lambda discovery: [i for i in _synth_items() if i["available_from"] <= "2025-01-01"],
    )
    from ask_pipeline.evidence import assemble_evidence
    from ask_pipeline.knowledge import retrieve_knowledge

    knowledge = retrieve_knowledge(
        intent="Company",
        entities=[{"type": "company", "id": "INFY"}],
        question="What is the institutional evidence for INFY?",
    )
    assert knowledge.get("iere")
    assert knowledge["iere"].get("unavailable") is False
    assert knowledge["primary_engine"] == "evidence_retrieval"
    evidence = assemble_evidence(
        knowledge,
        intent="Company",
        entities=[{"type": "company", "id": "INFY"}],
    )
    assert "iere" in evidence["packs"]
    assert evidence["packs"]["iere"]["pdf_sent_to_reasoning"] is False
    assert evidence.get("iere_retrieval_id")


def test_research_office_integration(monkeypatch) -> None:
    monkeypatch.setattr(
        "evidence_retrieval.pipeline.discover_candidates",
        lambda discovery: [i for i in _synth_items() if i["available_from"] <= "2025-01-01"],
    )
    from research_office.templates.knowledge import read_best_evidence

    best = read_best_evidence("INFY")
    assert best.get("unavailable") is not True
    assert best.get("retrieval_id")
    assert best.get("source") == "evidence_retrieval"
    assert best.get("reasoning_changed") is False


def test_existing_reasoning_unchanged_ast() -> None:
    """Soft-wire only — govern_answer / planner / committees not rewritten by IERE."""
    iere_root = ROOT / "evidence_retrieval"
    banned = ("govern_answer", "run_planner", "InvestmentCommittee", "summarize_pdf")
    for path in iere_root.rglob("*.py"):
        if "tests" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in banned
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned


def test_scheduler_compatibility_import() -> None:
    # Soft import surfaces used by scheduler/MC must remain importable
    from evidence_retrieval.production import dashboard, health

    assert health()["status"] == "ok"
    assert "north_star" in dashboard() or dashboard().get("version")


def test_scheduler_evidence_pack_soft_wire(monkeypatch) -> None:
    monkeypatch.setattr(
        "evidence_retrieval.pipeline.discover_candidates",
        lambda discovery: [i for i in _synth_items() if i["available_from"] <= "2025-01-01"],
    )

    class _FakeStore:
        @staticmethod
        def alert(*_a, **_k):
            return None

    monkeypatch.setattr(
        "institutional_scheduler.execution.handlers.store",
        _FakeStore,
        raising=False,
    )

    def _fake_daily(**_kwargs):
        return {"ok": True, "fabricated": False}

    monkeypatch.setattr(
        "knowledge_factory.production.run_daily_pipeline",
        _fake_daily,
        raising=False,
    )
    # Import path used inside handler
    import knowledge_factory.production as kf_prod

    monkeypatch.setattr(kf_prod, "run_daily_pipeline", _fake_daily, raising=False)

    from institutional_scheduler.execution.handlers import handle_evidence_packs

    out = handle_evidence_packs({"completed": {}})
    assert out.get("status") in {"ok", "degraded"}
    assert out.get("evidence_retrieval_soft_wire") is True
    assert out.get("iere")
    assert out["iere"].get("ok") is True
    assert len(out["iere"].get("warmed") or []) == 3
