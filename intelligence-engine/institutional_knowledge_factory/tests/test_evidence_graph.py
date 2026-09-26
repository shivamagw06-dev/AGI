"""Evidence Graph ownership tests — KPE infrastructure."""

from __future__ import annotations

from institutional_knowledge_factory.evidence_graph import (
    apply_delta,
    get_graph_pack,
    graph_stats,
    load_graph,
)
from institutional_knowledge_factory.pipeline import process_evidence


def test_kpe_owns_evidence_graph_writes():
    delta = [{
        "evidence_id": "EV_TEST_001",
        "source_id": "SRC_TEST",
        "entity_id": "TCS",
        "claim_id": "CLAIM_TCS_TEST",
        "trust_score": 85,
        "freshness": 80,
    }]
    graph = apply_delta("TCS", delta)
    assert graph["owned_by"] == "kpe"
    assert "EV_TEST_001" in graph["nodes"]
    assert len(graph["edges"]) >= 1


def test_graph_pack_for_kr_bridge():
    apply_delta("INFY", [{
        "evidence_id": "EV_INFY_1",
        "claim_id": "CLAIM_INFY_1",
        "trust_score": 90,
        "freshness": 85,
    }])
    pack = get_graph_pack("INFY")
    assert pack["owned_by"] == "kpe"
    assert pack["node_count"] >= 1
    assert isinstance(pack["items"], list)


def test_incremental_pipeline_writes_graph():
    evidence = [{
        "source_id": "QR",
        "source_type": "quarterly_results",
        "entity_id": "WIPRO",
        "extracts": [{
            "template_id": "CLAIM_FINANCIAL_CASH_GENERATION",
            "statement": "WIPRO generates stable cash flow.",
            "confidence": 80,
            "evidence_id": "EV_WIPRO_CF",
        }],
    }]
    result = process_evidence("WIPRO", evidence)
    assert result.get("evidence_graph")
    assert result["evidence_graph"]["owned_by"] == "kpe"
    stats = graph_stats("WIPRO")
    assert stats["node_count"] >= 1


def test_graph_never_duplicates_nodes():
    apply_delta("RELIANCE", [{"evidence_id": "EV_R1", "claim_id": "C1"}])
    apply_delta("RELIANCE", [{"evidence_id": "EV_R1", "claim_id": "C1"}])
    graph = load_graph("RELIANCE")
    assert len([e for e in graph["edges"] if e["evidence_id"] == "EV_R1"]) == 1
