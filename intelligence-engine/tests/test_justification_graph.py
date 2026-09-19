"""Decision Justification Graph — every conclusion is machine-explainable."""

from __future__ import annotations

from institutional_reasoning.execution_governance import govern_answer, telemetry_rows
from institutional_reasoning.justification_graph import (
    DJG_VERSION,
    ancestors,
    build_justification_graph,
    graph_telemetry_row,
    node_by_id,
    render_ascii,
    validate_graph,
    why,
)


def _graph(question: str, **kwargs):
    record = govern_answer(question, **kwargs)
    graph = record.get("justification_graph") or {}
    assert graph, "governance must attach a justification graph"
    return record, graph


def test_graph_attached_to_every_governed_answer():
    for q in (
        "Is Infosys expensive?",
        "Should DCF be used for HDFC Bank?",
        "What is ROIC?",
        "Is it expensive versus history?",
    ):
        _, graph = _graph(q)
        assert graph["djg_version"] == DJG_VERSION
        assert graph["integrity"]["valid"] is True, graph["integrity"]["problems"]


def test_supported_conclusion_traces_to_evidence_and_frameworks():
    _, graph = _graph("Is Infosys expensive?")
    w = why(graph)
    assert w["found"] is True
    assert graph["integrity"]["gated"] is False
    # Conclusion must trace back to question, frameworks and present evidence
    chain = w["reasoning_chain"]
    assert "question" in chain
    assert "applicability" in chain
    assert "committee" in chain
    assert "framework:rel_val_damodaran" in w["frameworks_in_path"]
    assert "evidence:current_pe" in w["evidence_used"]
    assert "evidence:historical_pe" in w["evidence_used"]
    assert w["supported_by"][0]["kind"] == "CONCLUDES"


def test_withheld_conclusion_traces_to_missing_evidence():
    _, graph = _graph("Is Nifty Bank expensive versus history?")
    w = why(graph)
    assert graph["integrity"]["gated"] is True
    assert w["supported_by"][0]["kind"] == "WITHHOLDS"
    assert "evidence:historical_pe" in w["evidence_missing"]
    # A gated conclusion must name a withholding reason somewhere in the graph
    reasons = [
        (e.get("attrs") or {}).get("reason")
        for e in graph["edges"]
        if e["kind"] == "WITHHOLDS"
    ]
    assert any(reasons)


def test_conflicts_are_nodes_with_explanations():
    _, graph = _graph("Value Zomato.")
    conflicts = [n for n in graph["nodes"] if n["kind"] == "conflict"]
    assert conflicts
    for c in conflicts:
        assert c["attrs"]["explanation"]
        assert c["attrs"]["evidence_shown"] is True
    # Conflicts must feed the decision policy, never be dropped
    policy_edges = [
        e for e in graph["edges"] if e["kind"] == "WEIGHTED_BY" and e["target"] == "decision_policy"
    ]
    assert any(e["source"].startswith("conflict:") for e in policy_edges)


def test_applicability_rejection_recorded_as_edge():
    _, graph = _graph("Should DCF be used for HDFC Bank?")
    rejected = [
        e
        for e in graph["edges"]
        if e["kind"] == "REJECTED" and e["target"].startswith("framework:dcf")
    ]
    assert rejected
    reason = " ".join(str((e.get("attrs") or {}).get("reason") or "") for e in rejected).lower()
    assert "financial" in reason or "institution" in reason or "sector" in reason


def test_education_graph_is_short_and_valid():
    _, graph = _graph("What is ROIC?")
    kinds = {n["kind"] for n in graph["nodes"]}
    assert kinds == {"question", "classification", "conclusion"}
    assert graph["integrity"]["valid"] is True
    assert node_by_id(graph, "conclusion")["attrs"]["gated"] is False


def test_validate_graph_detects_unsupported_conclusion():
    fake = {
        "path": "research",
        "terminal": "conclusion",
        "nodes": [
            {"id": "question", "kind": "question", "label": "q", "attrs": {}},
            {"id": "conclusion", "kind": "conclusion", "label": "c", "attrs": {"gated": False}},
        ],
        "edges": [{"source": "question", "kind": "CONCLUDES", "target": "conclusion", "attrs": {}}],
    }
    verdict = validate_graph(fake)
    assert verdict["valid"] is False
    assert "ungated_conclusion_without_executed_framework" in verdict["problems"]
    assert "ungated_conclusion_without_present_evidence" in verdict["problems"]


def test_validate_graph_detects_dangling_edge():
    fake = {
        "path": "research",
        "terminal": "conclusion",
        "nodes": [{"id": "conclusion", "kind": "conclusion", "label": "c", "attrs": {"gated": True}}],
        "edges": [{"source": "ghost", "kind": "CONCLUDES", "target": "conclusion", "attrs": {}}],
    }
    verdict = validate_graph(fake)
    assert verdict["valid"] is False
    assert any(p.startswith("dangling_edge_source") for p in verdict["problems"])


def test_ancestors_are_cycle_safe():
    cyclic = {
        "path": "research",
        "terminal": "b",
        "nodes": [
            {"id": "a", "kind": "question", "label": "a", "attrs": {}},
            {"id": "b", "kind": "conclusion", "label": "b", "attrs": {"gated": True}},
        ],
        "edges": [
            {"source": "a", "kind": "SUPPORTS", "target": "b", "attrs": {}},
            {"source": "b", "kind": "SUPPORTS", "target": "a", "attrs": {}},
        ],
    }
    assert set(ancestors(cyclic, "b")) == {"a", "b"}


def test_telemetry_carries_graph_summary():
    record, graph = _graph("Is Infosys expensive?")
    rows = telemetry_rows(record)
    assert rows
    summary = rows[0].get("justification_graph") or {}
    assert summary["integrity_valid"] is True
    assert summary["node_count"] == graph["counts"]["nodes"]
    direct = graph_telemetry_row(graph)
    assert direct["djg_version"] == DJG_VERSION


def test_render_ascii_is_debuggable():
    _, graph = _graph("Is Infosys expensive?")
    text = render_ascii(graph)
    assert "Decision Justification Graph" in text
    assert "applicability" in text
    assert "committee" in text
    assert "integrity: valid" in text


def test_graph_builder_is_pure_on_record():
    record = govern_answer("Is Infosys expensive?")
    rebuilt = build_justification_graph(record)
    assert rebuilt["counts"] == record["justification_graph"]["counts"]
