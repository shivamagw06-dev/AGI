"""AGIB v3.6 Sprint 2.1 — Institutional Evidence Graph acceptance tests."""

from __future__ import annotations

import ast
from pathlib import Path

from institutional_evidence_graph import IEG_VERSION, build_evidence_graph
from institutional_evidence_graph.production import company, dashboard, health
from institutional_evidence_graph.schema import ENTITY_DOMAINS
from institutional_communication import communicate_from_ask

ROOT = Path(__file__).resolve().parents[1]


def test_ieg_health_and_domains() -> None:
    assert IEG_VERSION.startswith("institutional-evidence-graph")
    assert len(ENTITY_DOMAINS) == 18
    assert "competitors" in ENTITY_DOMAINS
    assert "historical_events" in ENTITY_DOMAINS
    assert health()["status"] == "ok"
    assert dashboard()["n_domains"] == 18


def test_infosys_entity_tree_and_competitors() -> None:
    g = build_evidence_graph(
        question="Compare Infosys competitive position and valuation frameworks",
        entities=[{"type": "company", "id": "INFY", "confidence": 0.99}],
        ticker_hint="INFY",
    )
    assert g["ok"] is True
    assert "INFY" in g["entities"]
    tree = g["entity_trees"]["INFY"]
    assert tree["coverage"]["n_filled"] >= 4
    assert (tree["domains"]["competitors"]["n_nodes"] or 0) >= 1
    assert (tree["domains"]["historical_events"]["n_nodes"] or 0) >= 1
    assert g["n_nodes"] >= 20
    assert g["n_edges"] >= 10
    assert g["reasoning_changed"] is False
    assert (g.get("validation") or {}).get("passed") is True


def test_hdfc_bank_credit_and_macro_domains() -> None:
    g = company("HDFCBANK")
    tree = g["entity_trees"]["HDFCBANK"]
    assert (tree["domains"]["competitors"]["n_nodes"] or 0) >= 1
    assert (tree["domains"]["credit"]["n_nodes"] or 0) >= 1 or (
        tree["domains"]["macro_exposure"]["n_nodes"] or 0
    ) >= 1
    assert any("Evidence chain" in b or "domains filled" in b for b in g["surface_bullets"])


def test_replay_excludes_future_events() -> None:
    g = build_evidence_graph(
        question="Replay Infosys as of 31 March 2020. Describe only evidence available on that date.",
        entities=[{"type": "company", "id": "INFY", "confidence": 0.99}],
        ticker_hint="INFY",
        as_of="2020-03-31",
    )
    assert g["as_of"] == "2020-03-31"
    # Future AI-strategy nodes must not appear
    titles = " ".join(
        str(n.get("title") or n.get("paragraph") or "")
        for n in g["nodes"]
        if n.get("kind") in {"historical_event", "evidence"}
    ).lower()
    assert "2020" in titles or "covid" in titles or "lockdown" in titles
    assert "generative ai" not in titles
    assert "2024" not in titles and "2025" not in titles
    # Explicit future leakage gate
    assert (g.get("validation") or {}).get("passed") is True
    hist_n = g["entity_trees"]["INFY"]["domains"]["historical_events"]["n_nodes"]
    assert hist_n >= 1
    # Surface bullets mention replay
    assert any("as_of=2020-03-31" in b for b in g["surface_bullets"])


def test_evidence_node_shape() -> None:
    g = company("RELIANCE")
    ev_nodes = [n for n in g["nodes"] if n.get("kind") in {"evidence", "relationship", "historical_event", "relationship_stub"}]
    assert ev_nodes
    sample = ev_nodes[0]
    for key in (
        "source",
        "timestamp",
        "confidence",
        "document",
        "paragraph",
        "entity",
        "relationship",
        "expiry",
        "evidence_strength",
    ):
        assert key in sample


def test_relationship_chains_present() -> None:
    g = build_evidence_graph(
        question="If crude oil prices fall, which industries benefit?",
        concept_mode=True,
    )
    # May have no company — still ok
    assert g["ok"] is True
    # With RELIANCE / INDIGO alias from question? oil question may not bind company
    g2 = company("INDIGO")
    assert g2["chains"] or g2["entity_trees"]["INDIGO"]["domains"]["macro_exposure"]["n_nodes"] >= 1


def test_ice_surfaces_evidence_graph() -> None:
    g = build_evidence_graph(
        question="Replay Infosys as of 31 March 2020.",
        entities=[{"type": "company", "id": "INFY", "confidence": 0.99}],
        as_of="2020-03-31",
    )
    comm = communicate_from_ask(
        question="Replay Infosys as of 31 March 2020.",
        intent_resolution={"intent": "HistoricalReplay", "as_of": "2020-03-31", "concept_mode": False},
        framework_selection={"framework_ids": ["FW_DCF"], "explanation": {"reason": "IT"}, "confidence": {"band": "medium", "pct": 60}},
        playbook_selection={"playbook_id": "PB_IND_IT_SERVICES", "playbook_name": "IT Services"},
        evidence_graph=g,
        institutional_answer={"sections": {"evidence": {"bullets": ["Thin prior evidence"]}}},
    )
    prose = (comm.get("prose") or "").lower()
    assert "evidence graph" in prose or "historical event" in prose or "domains filled" in prose
    assert comm.get("evidence_graph_visible") is True


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
