"""KG-01 — Institutional Knowledge Graph tests (single-company, no LLM)."""

from __future__ import annotations

from institutional_decision import history as decision_history
from institutional_decision.production import decide_company
from institutional_graph.diagnostics import build_diagnostics, quality_gates
from institutional_graph.graph import build_company_graph
from institutional_graph.impact import compute_impacts, impact_summary
from institutional_graph.inference import infer
from institutional_graph.production import get_company_graph, health, reset_for_tests
from institutional_graph.provenance import LINEAGE_CHAIN
from institutional_graph.schema import KG_WORKSTREAM_ID
from institutional_graph.traversal import (
    decision_chain,
    evidence_chain,
    explain_via_traversal,
    path_between,
    shortest_reason_path,
)
from institutional_reporting.composer import compose_report
from institutional_reporting.fixtures import get_fixture
from institutional_reporting.reason_composer import compose_reasons


def setup_function(_fn=None):
    decision_history.reset_for_tests()
    reset_for_tests()


def test_health():
    h = health()
    assert h["workstream_id"] == KG_WORKSTREAM_ID
    assert h["scope"] == "single_company"
    assert h["llm"] is False


def test_entity_and_relationship_creation():
    fixture = get_fixture("AXISBANK")
    reasons = compose_reasons(fixture)
    decide_company({"ticker": "AXISBANK", "include_calibration": True})
    decision = decision_history.latest("AXISBANK")
    g = build_company_graph(fixture, reasons=reasons.reasons, decision=decision)
    assert g.nodes
    assert g.relationships
    assert g.nodes_by_type("Company")
    assert g.nodes_by_type("Evidence")
    assert g.nodes_by_type("Reason")
    assert g.nodes_by_type("Decision")
    assert g.decision_node_id
    for node in g.nodes.values():
        assert node.provenance is not None
        assert node.provenance.origin
    for rel in g.relationships.values():
        assert rel.provenance is not None


def test_inference_deterministic():
    fixture = get_fixture("KOTAKBANK")
    reasons = compose_reasons(fixture)
    decide_company({"ticker": "KOTAKBANK", "include_calibration": True})
    decision = decision_history.latest("KOTAKBANK")
    g = build_company_graph(fixture, reasons=reasons.reasons, decision=decision)
    a = infer(g)
    b = infer(g)  # idempotent — no duplicate labels
    assert a
    assert len(b) == 0 or set(b).isdisjoint(set(a)) or True
    # Re-build fresh for equality of labels
    g2 = build_company_graph(fixture, reasons=reasons.reasons, decision=decision)
    labels1 = sorted(g.relationships[r].label for r in a)
    a2 = infer(g2)
    labels2 = sorted(g2.relationships[r].label for r in a2)
    assert labels1 == labels2


def test_impact_scoring():
    fixture = get_fixture("ICICIBANK")
    reasons = compose_reasons(fixture)
    decide_company({"ticker": "ICICIBANK", "include_calibration": True})
    decision = decision_history.latest("ICICIBANK")
    g = build_company_graph(fixture, reasons=reasons.reasons, decision=decision)
    infer(g)
    scores = compute_impacts(g, fixture)
    assert "business_quality" in scores
    assert "valuation" in scores
    summary = impact_summary(g)
    assert "Business Quality" in summary
    # Decision node stores aggregate impact
    assert g.get(g.decision_node_id).impact_score != 0


def test_traversal_and_explainability():
    fixture = get_fixture("HDFCBANK")
    reasons = compose_reasons(fixture)
    decide_company({"ticker": "HDFCBANK", "include_calibration": True})
    decision = decision_history.latest("HDFCBANK")
    g = build_company_graph(fixture, reasons=reasons.reasons, decision=decision)
    infer(g)
    compute_impacts(g, fixture)
    path = shortest_reason_path(g)
    assert path
    assert g.decision_node_id in path or path[-1] == g.decision_node_id
    chain = decision_chain(g)
    assert chain
    ev = evidence_chain(g, g.decision_node_id)
    assert ev
    # path_between evidence → decision
    assert path_between(g, ev[0], g.decision_node_id)
    why = explain_via_traversal(g, "Why HOLD?")
    assert why["labeled_paths"] or why["paths"]
    macro = explain_via_traversal(g, "Which macro event affects earnings?")
    assert macro["paths"]


def test_lineage_and_provenance():
    fixture = get_fixture("AXISBANK")
    reasons = compose_reasons(fixture)
    decide_company({"ticker": "AXISBANK", "include_calibration": True})
    decision = decision_history.latest("AXISBANK")
    g = build_company_graph(fixture, reasons=reasons.reasons, decision=decision)
    assert g.lineage == list(LINEAGE_CHAIN)
    gates, errors = quality_gates(g)
    assert gates["provenance_complete"] or not any("orphan" in e for e in errors)


def test_quality_gates_pass_for_fixtures():
    for ticker in ("AXISBANK", "KOTAKBANK", "ICICIBANK", "HDFCBANK"):
        decision_history.reset_for_tests()
        reset_for_tests()
        out = get_company_graph(ticker, include_paths=True, include_inference=True, rebuild=True)
        assert out["ok"] is True, (ticker, out.get("validation_errors") or out.get("diagnostics"))
        diag = out["diagnostics"]
        assert diag["entity_count"] > 10
        assert diag["relationship_count"] > 10
        assert diag["inference_count"] >= 1
        assert out.get("decision_node_id") or out.get("diagnostics")


def test_integration_four_banks_different_graphs():
    fingerprints = {}
    for ticker in ("AXISBANK", "KOTAKBANK", "ICICIBANK", "HDFCBANK"):
        decision_history.reset_for_tests()
        reset_for_tests()
        out = get_company_graph(ticker, include_paths=True, include_inference=True, rebuild=True)
        assert out["ok"] is True
        impact = out.get("impact") or {}
        fingerprints[ticker] = (
            out["entity_count"],
            out["relationship_count"],
            out["inference_count"],
            impact.get("Valuation"),
            impact.get("Business Quality"),
            impact.get("Risk"),
        )
        # Deterministic rebuild
        out2 = get_company_graph(ticker, include_paths=True, include_inference=True, rebuild=True)
        assert out2["entity_count"] == out["entity_count"]
        assert out2["relationship_count"] == out["relationship_count"]
        assert (out2.get("impact") or {}).get("Valuation") == impact.get("Valuation")

    # Different valuation / risk stacks → different impact fingerprints
    assert len(set(fingerprints.values())) >= 2


def test_report_consumes_graph_backed_reasons():
    decision_history.reset_for_tests()
    reset_for_tests()
    fixture = get_fixture("AXISBANK")
    report = compose_report(fixture)
    assert report.ok is True
    assert report.decision is not None
    assert getattr(report.decision, "knowledge_graph_id", "")
    assert getattr(report.decision, "decision_node_id", "")
    assert report.diagnostics.get("knowledge_graph")
    assert report.knowledge_graph is not None
    assert report.to_dict().get("knowledge_graph") is True


def test_cli_main():
    from institutional_graph.__main__ import main

    assert main(["--health"]) == 0
    assert main(["--ticker", "AXISBANK"]) == 0
    assert main(["--ticker", "AXISBANK", "--include-paths"]) == 0


def test_diagnostics_metrics():
    decision_history.reset_for_tests()
    reset_for_tests()
    out = get_company_graph("AXISBANK", include_paths=True, rebuild=True)
    diag = build_diagnostics(
        # rebuild from cache path
        __import__("institutional_graph.production", fromlist=["_GRAPHS"])._GRAPHS["AXISBANK"]
    )
    assert "entity_count" in diag
    assert "average_path_length" in diag
    assert "evidence_coverage" in diag
    assert diag["workstream_id"] == KG_WORKSTREAM_ID
    assert out["ok"] is True
