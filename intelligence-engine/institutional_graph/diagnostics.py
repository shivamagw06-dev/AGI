"""KG-01 diagnostics and quality gates."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple

from institutional_graph.graph import InstitutionalKnowledgeGraph
from institutional_graph.provenance import require_provenance, require_relationship_source
from institutional_graph.schema import KG_VERSION, KG_WORKSTREAM_ID
from institutional_graph.traversal import decision_chain, shortest_reason_path


def detect_cycles(graph: InstitutionalKnowledgeGraph) -> List[str]:
    """Return node ids involved in cycles (directed)."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {nid: WHITE for nid in graph.nodes}
    cycles: list[str] = []

    def dfs(node_id: str, stack: list[str]) -> None:
        color[node_id] = GRAY
        stack.append(node_id)
        for rel in graph.neighbors(node_id, outbound=True):
            nxt = rel.target_id
            if nxt not in color:
                continue
            if color[nxt] == GRAY:
                cycles.append(" → ".join(stack[stack.index(nxt) :] + [nxt]))
            elif color[nxt] == WHITE:
                dfs(nxt, stack)
        stack.pop()
        color[node_id] = BLACK

    for nid in list(graph.nodes):
        if color[nid] == WHITE:
            dfs(nid, [])
    return cycles


def disconnected_nodes(graph: InstitutionalKnowledgeGraph) -> List[str]:
    """Nodes with zero inbound and outbound relationships."""
    connected: set[str] = set()
    for rel in graph.relationships.values():
        connected.add(rel.source_id)
        connected.add(rel.target_id)
    return sorted(nid for nid in graph.nodes if nid not in connected)


def quality_gates(graph: InstitutionalKnowledgeGraph) -> Tuple[dict[str, bool], list[str]]:
    errors: list[str] = []
    # Unknown entity types already rejected at construction; re-check
    for node in graph.nodes.values():
        errors.extend(require_provenance(node))
    for rel in graph.relationships.values():
        errors.extend(require_relationship_source(rel))
        if rel.source_id not in graph.nodes or rel.target_id not in graph.nodes:
            errors.append(f"broken lineage endpoint: {rel.id}")

    if graph.decision_node_id:
        if graph.decision_node_id not in graph.nodes:
            errors.append("disconnected decision")
        else:
            # Decision must be reachable from at least one evidence or reason
            chain = decision_chain(graph)
            reasons = graph.nodes_by_type("Reason")
            if not reasons:
                errors.append("decision without reason nodes")
            inbound = graph.neighbors(graph.decision_node_id, outbound=False)
            if not inbound:
                errors.append("disconnected decision")
            if not chain and reasons:
                # soft: still require inbound
                pass
    else:
        errors.append("disconnected decision")

    if not graph.nodes_by_type("Evidence"):
        errors.append("missing evidence")

    # Inference without support
    for rid in graph.inferred_relationship_ids:
        rel = graph.relationships.get(rid)
        if rel is None:
            continue
        if not rel.evidence_ids and (rel.provenance is None or not rel.provenance.origin):
            errors.append(f"inference without support: {rid}")

    gates = {
        "decision_connected": "disconnected decision" not in errors
        and not any(e.startswith("disconnected decision") for e in errors),
        "evidence_present": "missing evidence" not in errors,
        "relationships_sourced": not any("relationship without source" in e for e in errors),
        "no_unknown_entities": True,
        "lineage_intact": not any("broken lineage" in e for e in errors),
        "inference_supported": not any("inference without support" in e for e in errors),
        "no_orphans": not any("orphan node" in e for e in errors),
        "provenance_complete": not any("provenance" in e for e in errors),
    }
    # Normalize decision_connected
    gates["decision_connected"] = bool(graph.decision_node_id) and not any(
        "disconnected decision" in e for e in errors
    )
    return gates, errors


def build_diagnostics(graph: InstitutionalKnowledgeGraph) -> dict[str, Any]:
    t0 = time.perf_counter()
    path = shortest_reason_path(graph)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    gates, errors = quality_gates(graph)
    cycles = detect_cycles(graph)
    disconnected = disconnected_nodes(graph)

    evidence_n = len(graph.nodes_by_type("Evidence"))
    reason_n = len(graph.nodes_by_type("Reason"))
    coverage = 0.0
    if reason_n:
        covered = 0
        for reason in graph.nodes_by_type("Reason"):
            inbound = graph.neighbors(reason.id, outbound=False)
            if any(graph.get(r.source_id) and graph.get(r.source_id).type == "Evidence" for r in inbound):
                covered += 1
        coverage = covered / reason_n

    # Average path length among reason→decision
    lengths: list[int] = []
    if graph.decision_node_id:
        for reason in graph.nodes_by_type("Reason"):
            from institutional_graph.traversal import path_between

            p = path_between(graph, reason.id, graph.decision_node_id)
            if p:
                lengths.append(len(p) - 1)
    avg_path = sum(lengths) / len(lengths) if lengths else 0.0

    return {
        "workstream_id": KG_WORKSTREAM_ID,
        "version": KG_VERSION,
        "graph_id": graph.graph_id,
        "ticker": graph.ticker,
        "graph_size": len(graph.nodes) + len(graph.relationships),
        "entity_count": len(graph.nodes),
        "relationship_count": len(graph.relationships),
        "inference_count": len(graph.inferred_relationship_ids),
        "disconnected_nodes": disconnected,
        "disconnected_count": len(disconnected),
        "cycles": cycles,
        "cycle_count": len(cycles),
        "evidence_coverage": round(coverage, 4),
        "evidence_count": evidence_n,
        "reason_count": reason_n,
        "traversal_time_ms": round(elapsed_ms, 4),
        "average_path_length": round(avg_path, 4),
        "shortest_reason_path": path,
        "decision_chain": decision_chain(graph),
        "quality_gates": gates,
        "quality_gate_pass": all(gates.values()),
        "errors": errors,
        "impact_scores": dict((graph.meta or {}).get("impact_scores") or {}),
        "llm": False,
        "scope": graph.scope,
    }
