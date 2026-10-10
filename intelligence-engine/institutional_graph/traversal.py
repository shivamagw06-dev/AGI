"""KG-01 traversal engine — path finding without hardcoded answer templates."""

from __future__ import annotations

from collections import deque
from typing import List, Optional, Sequence, Tuple

from institutional_graph.graph import InstitutionalKnowledgeGraph
from institutional_graph.relationships import Relationship


def _edges(graph: InstitutionalKnowledgeGraph) -> List[Relationship]:
    return list(graph.relationships.values())


def path_between(
    graph: InstitutionalKnowledgeGraph,
    source_id: str,
    target_id: str,
    *,
    max_depth: int = 8,
) -> List[str]:
    """BFS shortest node-id path from source to target (outbound edges)."""
    if source_id not in graph.nodes or target_id not in graph.nodes:
        return []
    if source_id == target_id:
        return [source_id]
    q: deque[str] = deque([source_id])
    prev: dict[str, Optional[str]] = {source_id: None}
    while q:
        cur = q.popleft()
        depth = 0
        walk = cur
        while prev.get(walk) is not None:
            depth += 1
            walk = prev[walk]  # type: ignore[assignment]
            if depth > max_depth:
                break
        if depth >= max_depth:
            continue
        for rel in graph.neighbors(cur, outbound=True):
            nxt = rel.target_id
            if nxt in prev:
                continue
            prev[nxt] = cur
            if nxt == target_id:
                # reconstruct
                path = [target_id]
                while path[-1] != source_id:
                    parent = prev[path[-1]]
                    if parent is None:
                        break
                    path.append(parent)
                path.reverse()
                return path
            q.append(nxt)
    return []


def shortest_reason_path(
    graph: InstitutionalKnowledgeGraph,
    *,
    from_type: str = "Evidence",
    to_type: str = "Decision",
) -> List[str]:
    """Shortest path from any Evidence node to the Decision node (via reasons)."""
    decision_id = graph.decision_node_id
    if not decision_id:
        targets = [n.id for n in graph.nodes_by_type(to_type)]
        decision_id = targets[0] if targets else ""
    if not decision_id:
        return []
    best: List[str] = []
    for src in graph.nodes_by_type(from_type):
        path = path_between(graph, src.id, decision_id)
        if path and (not best or len(path) < len(best)):
            best = path
    return best


def evidence_chain(graph: InstitutionalKnowledgeGraph, reason_or_decision_id: str) -> List[str]:
    """Collect Evidence node ids that reach the given reason/decision (reverse BFS)."""
    if reason_or_decision_id not in graph.nodes:
        return []
    seen: set[str] = set()
    q: deque[str] = deque([reason_or_decision_id])
    evidence: list[str] = []
    while q:
        cur = q.popleft()
        for rel in graph.neighbors(cur, outbound=False):
            src = rel.source_id
            if src in seen:
                continue
            seen.add(src)
            node = graph.get(src)
            if node and node.type == "Evidence":
                evidence.append(src)
            q.append(src)
    return evidence


def decision_chain(graph: InstitutionalKnowledgeGraph) -> List[str]:
    """Canonical chain labels for the decision lineage through the graph."""
    if not graph.decision_node_id:
        return []
    # Prefer Evidence → Reason → Decision → Calibration
    path = shortest_reason_path(graph)
    if graph.calibration_node_id and path:
        cal_path = path_between(graph, graph.decision_node_id, graph.calibration_node_id)
        if cal_path and len(cal_path) > 1:
            path = path + cal_path[1:]
    return path


def impact_chain(graph: InstitutionalKnowledgeGraph) -> List[dict]:
    """Ordered impact-bearing nodes from metrics/macro/risk to decision."""
    rows: list[tuple[int, str, int, str]] = []
    for node in graph.nodes.values():
        if node.impact_score == 0 and node.type not in {
            "FinancialMetric",
            "ValuationMetric",
            "MacroVariable",
            "Risk",
            "Management",
            "Decision",
        }:
            continue
        if node.type in {
            "FinancialMetric",
            "ValuationMetric",
            "MacroVariable",
            "Risk",
            "Management",
            "Decision",
            "Calibration",
        }:
            rows.append((abs(int(node.impact_score)), node.id, int(node.impact_score), node.label))
    rows.sort(reverse=True)
    return [
        {"node_id": nid, "label": label, "impact_score": score}
        for _, nid, score, label in rows
    ]


def explain_via_traversal(
    graph: InstitutionalKnowledgeGraph,
    question: str,
) -> dict:
    """
    Answer institutional questions by traversing the graph (not templates).

    Returns structured path payloads — callers render language elsewhere.
    """
    q = str(question or "").strip().lower()
    decision = graph.get(graph.decision_node_id) if graph.decision_node_id else None
    rec = str((decision.attributes or {}).get("recommendation") or "").upper() if decision else ""

    result: dict = {
        "question": question,
        "recommendation": rec,
        "paths": [],
        "nodes": [],
        "evidence_ids": [],
    }

    if "buy" in q and "why not" not in q:
        # Paths that support the decision
        bq = (graph.meta or {}).get("metric_ids", {}).get("business_quality")
        if bq and graph.decision_node_id:
            path = path_between(graph, bq, graph.decision_node_id)
            result["paths"].append(path)
    elif "hold" in q:
        if graph.decision_node_id:
            result["paths"].append(decision_chain(graph))
    elif "confidence" in q or "fell" in q or "fall" in q:
        if graph.calibration_node_id:
            result["paths"].append(
                path_between(graph, graph.decision_node_id, graph.calibration_node_id)
                or [graph.decision_node_id, graph.calibration_node_id]
            )
        result["nodes"] = [
            n.to_dict()
            for n in graph.nodes.values()
            if n.type in {"Risk", "ValuationMetric", "MacroVariable"} and n.impact_score < 0
        ]
    elif "changed" in q or "what changed" in q:
        result["paths"].append(decision_chain(graph))
        result["nodes"] = impact_chain(graph)[:8]
    elif "evidence" in q or "mattered" in q:
        if graph.decision_node_id:
            ev = evidence_chain(graph, graph.decision_node_id)
            result["evidence_ids"] = ev
            result["paths"].append(shortest_reason_path(graph))
    elif "valuation" in q or "assumption" in q:
        val_id = (graph.meta or {}).get("valuation_node_id")
        if val_id and graph.decision_node_id:
            result["paths"].append(path_between(graph, val_id, graph.decision_node_id))
    elif "macro" in q or "rbi" in q or "earnings" in q:
        rbi = (graph.meta or {}).get("rbi_node_id")
        profit = (graph.meta or {}).get("metric_ids", {}).get("profitability")
        if rbi and profit:
            result["paths"].append(path_between(graph, rbi, profit))
        if profit and graph.decision_node_id:
            result["paths"].append(path_between(graph, profit, graph.decision_node_id))
    elif "risk" in q:
        for risk in graph.nodes_by_type("Risk")[:4]:
            if graph.decision_node_id:
                result["paths"].append(path_between(graph, risk.id, graph.decision_node_id))
    else:
        result["paths"].append(decision_chain(graph))

    # Attach node labels for path readability
    labeled = []
    for path in result["paths"]:
        labeled.append(
            [
                {
                    "id": nid,
                    "label": (graph.get(nid).label if graph.get(nid) else nid),
                    "type": (graph.get(nid).type if graph.get(nid) else ""),
                    "impact_score": (graph.get(nid).impact_score if graph.get(nid) else 0),
                }
                for nid in path
            ]
        )
    result["labeled_paths"] = labeled
    return result
