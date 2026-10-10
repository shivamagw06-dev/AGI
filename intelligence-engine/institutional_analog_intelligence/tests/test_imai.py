"""AGIB v3.6 Sprint 2.2 — Institutional Memory & Analog Intelligence acceptance tests."""

from __future__ import annotations

import ast
from pathlib import Path

from institutional_analog_intelligence import IMAI_VERSION, retrieve
from institutional_analog_intelligence.company_memory.lookup import company_memories
from institutional_analog_intelligence.macro_memory.lookup import macro_memories
from institutional_analog_intelligence.policy_memory.lookup import policy_memories
from institutional_analog_intelligence.production import board, catalog, status
from institutional_analog_intelligence.regime_memory.classify import classify_regimes
from institutional_analog_intelligence.registry.index import list_memories, type_counts
from institutional_communication import communicate_from_ask
from institutional_evidence_graph import build_evidence_graph

ROOT = Path(__file__).resolve().parents[1]


def test_imai_health_and_registry() -> None:
    assert IMAI_VERSION.startswith("institutional-analog-intelligence")
    assert status()["status"] == "ready"
    assert status()["distinct_from"].startswith("institutional_memory")
    assert len(list_memories()) >= 15
    assert type_counts()
    assert board()["historical_coverage"] >= 15
    assert catalog(limit=10)


def test_rbi_rate_cut_bank_analog_retrieval() -> None:
    pack = retrieve(
        question="How do Indian private banks perform after RBI rate cuts?",
        top_k=5,
    )
    assert pack["have_we_seen_this_before"] is True
    assert pack["reasoning_changed"] is False
    assert pack["invented_analogues"] is False
    ids = " ".join(pack.get("top_memory_ids") or [])
    assert "MEM_RBI_CUT_2009" in ids or "MEM_RBI_COVID_CUT_2020" in ids
    assert (pack.get("quality") or {}).get("status") == "pass"
    # Ranking present
    sims = [m.get("similarity_score") for m in pack["memories"]]
    assert sims and all(isinstance(s, (int, float)) and s >= 12 for s in sims)
    assert sims == sorted(sims, reverse=True)


def test_macro_and_commodity_cycle_retrieval() -> None:
    oil = retrieve(question="If crude oil prices fall by 25%, which industries benefit?", top_k=5)
    assert oil["have_we_seen_this_before"] is True
    assert any("oil" in str(m.get("memory_id")).lower() or "oil" in str(m.get("title")).lower()
               for m in oil["memories"])
    assert macro_memories(regime="oil_collapse") or oil["memories"]


def test_company_earnings_analog() -> None:
    pack = retrieve(
        question="Infosys missed earnings — how have IT services stocks reacted historically?",
        evidence_graph={"entities": ["INFY"], "chain_bullets": []},
        top_k=5,
    )
    assert pack["have_we_seen_this_before"] is True
    assert company_memories("INFY")
    assert any("INFY" in (m.get("entities") or []) or "infy" in str(m.get("title")).lower()
               for m in pack["memories"])


def test_policy_analog_retrieval() -> None:
    pack = retrieve(question="What happened to markets after GST implementation?", top_k=5)
    assert pack["have_we_seen_this_before"] is True
    assert policy_memories()
    assert any("gst" in str(m.get("title")).lower() or "gst" in " ".join(m.get("cues") or [])
               for m in pack["memories"])


def test_regime_classification() -> None:
    regs = classify_regimes(question="RBI rate cut cycle and private bank credit growth")
    assert "rate_cutting_cycle" in regs


def test_similarity_ranking_order() -> None:
    pack = retrieve(
        question="Private banks after RBI repo rate cuts — credit growth and NIM",
        top_k=5,
    )
    scores = [float(m["similarity_score"]) for m in pack["memories"]]
    assert scores == sorted(scores, reverse=True)


def test_replay_no_future_leakage() -> None:
    pack = retrieve(
        question="How do Indian private banks perform after RBI rate cuts?",
        as_of="2012-12-31",
        top_k=8,
    )
    for m in pack["memories"]:
        assert str(m["available_from"])[:10] <= "2012-12-31"
    # 2020 COVID cut must not appear
    assert "MEM_RBI_COVID_CUT_2020" not in (pack.get("top_memory_ids") or [])
    assert (pack.get("quality") or {}).get("status") == "pass"


def test_evidence_graph_integration() -> None:
    g = build_evidence_graph(
        question="How do Indian private banks perform after RBI rate cuts?",
        entities=[{"type": "company", "id": "HDFCBANK", "confidence": 0.99}],
        ticker_hint="HDFCBANK",
    )
    pack = retrieve(
        question="How do Indian private banks perform after RBI rate cuts?",
        evidence_graph=g,
        top_k=5,
    )
    assert pack["have_we_seen_this_before"] is True
    assert pack["candidate_count"] >= 1


def test_playbook_integration() -> None:
    pack = retrieve(
        question="Private banks after rate cuts",
        playbook={"playbook_id": "PB_RATE_SENSITIVE_BANKS", "category": "banks"},
        top_k=5,
    )
    assert pack["have_we_seen_this_before"] is True


def test_ice_surfaces_historical_analogues() -> None:
    pack = retrieve(
        question="How do Indian private banks perform after RBI rate cuts?",
        top_k=4,
    )
    comm = communicate_from_ask(
        question="How do Indian private banks perform after RBI rate cuts?",
        intent_resolution={"intent": "Macro", "concept_mode": True},
        framework_selection={
            "framework_ids": ["FW_CREDIT_CYCLE"],
            "explanation": {"reason": "banks"},
            "confidence": {"band": "medium", "pct": 65},
        },
        playbook_selection={"playbook_id": "PB_BANKS", "playbook_name": "Banks"},
        institutional_memory=pack,
        institutional_answer={"sections": {"evidence": {"bullets": ["Thin prior evidence"]}}},
    )
    prose = (comm.get("prose") or "").lower()
    assert "have we seen this before" in prose or "historical analogue" in prose or "mem_rbi" in prose
    assert comm.get("institutional_memory_visible") is True
    assert comm.get("have_we_seen_this_before") is True


def test_research_office_soft_wire() -> None:
    from research_office.publications.builders import _historical_analogues_section

    sec = _historical_analogues_section(
        title="Macro brief: RBI rate cuts and private banks",
        covered_entities=["HDFCBANK", "banks"],
    )
    assert sec.get("omitted_no_evidence") is False
    assert sec.get("historical_analogues")
    assert sec.get("invented_analogues") is False


def test_existing_reasoning_untouched_flag() -> None:
    pack = retrieve(question="Oil collapse transmission to airlines and paint companies")
    assert pack["reasoning_changed"] is False
    assert pack["knowledge_factory_changed"] is False
    assert pack["governance_changed"] is False


def test_no_llm_imports() -> None:
    banned = ("openai", "anthropic", "litellm", "langchain")
    for path in ROOT.rglob("*.py"):
        if "tests" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not any(b in alias.name.lower() for b in banned)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert not any(b in node.module.lower() for b in banned)


def test_ilm_package_untouched() -> None:
    """IMAI must not redesign Institutional Learning & Memory (ILM)."""
    ilm = Path(__file__).resolve().parents[2] / "institutional_memory"
    assert ilm.exists()
    # Smoke: ILM still importable as learning package
    import institutional_memory  # noqa: F401
