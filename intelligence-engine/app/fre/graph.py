"""Step 14 — Knowledge graph update from evidence / documents."""

from __future__ import annotations

import re
from typing import Any

from app.fre.models import FreDocument, FreEvidence, GraphEdge, GraphNode
from app.fre.store import FreStore

_REL_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)\b(jio|retail|oil-to-chemicals|o2c|new energy)\b"), "operates"),
    (re.compile(r"(?i)\bcompet(?:e|es|ing)\b|\brival\b"), "competes_with"),
    (re.compile(r"(?i)\bcrude|oil prices|commodity\b"), "affected_by"),
    (re.compile(r"(?i)\bpolicy|regulation|rbi|sebi|government\b"), "affected_by"),
    (re.compile(r"(?i)\bacqui(?:re|sition)|subsidiary|owns\b"), "owns"),
]


def update_graph(store: FreStore, *, documents: list[FreDocument], evidence: list[FreEvidence]) -> dict[str, Any]:
    nodes: dict[str, GraphNode] = {}
    edges: list[GraphEdge] = []

    def node_for(label: str, kind: str = "entity", company: str | None = None) -> GraphNode:
        key = f"{kind}:{label.lower()}"
        if key not in nodes:
            nodes[key] = GraphNode(label=label, kind=kind, company=company)
        return nodes[key]

    for doc in documents:
        if doc.company:
            co = node_for(doc.company, "company", doc.company)
            src = node_for(doc.document_type or "document", "document_type")
            edges.append(
                GraphEdge(
                    source_id=co.node_id,
                    target_id=src.node_id,
                    relation="has_document",
                    confidence=0.9,
                )
            )
        text = doc.raw_text or ""
        if doc.company:
            co = node_for(doc.company, "company", doc.company)
            for pattern, relation in _REL_PATTERNS:
                m = pattern.search(text)
                if not m:
                    continue
                target_label = m.group(0)
                # normalize a few known entities
                if relation == "operates" and "jio" in target_label.lower():
                    target_label = "Jio"
                if relation == "affected_by" and "oil" in target_label.lower():
                    target_label = "Oil Prices"
                if relation == "affected_by" and any(k in target_label.lower() for k in ("rbi", "sebi", "policy", "government")):
                    target_label = "Government Policy"
                tgt = node_for(target_label, "theme" if relation == "affected_by" else "entity")
                edges.append(
                    GraphEdge(
                        source_id=co.node_id,
                        target_id=tgt.node_id,
                        relation=relation,
                        confidence=0.65,
                    )
                )

    for ev in evidence:
        if not ev.company and not ev.symbol:
            continue
        label = ev.company or ev.symbol or "Unknown"
        co = node_for(label, "company", ev.company)
        claim_node = node_for(ev.claim[:80], "claim")
        edges.append(
            GraphEdge(
                source_id=co.node_id,
                target_id=claim_node.node_id,
                relation="supported_by_claim",
                confidence=ev.confidence,
                evidence_ids=[ev.evidence_id],
            )
        )

    store.put_graph(list(nodes.values()), edges)
    return {
        "nodes": [n.to_dict() for n in nodes.values()],
        "edges": [e.to_dict() for e in edges],
        "count_nodes": len(nodes),
        "count_edges": len(edges),
    }


def graph_for_entity(store: FreStore, key: str) -> dict[str, Any]:
    k = (key or "").lower()
    nodes = [
        n
        for n in store.nodes.values()
        if k in n.label.lower() or k in (n.company or "").lower()
    ]
    node_ids = {n.node_id for n in nodes}
    # expand one hop
    edges = [
        e
        for e in store.edges.values()
        if e.source_id in node_ids or e.target_id in node_ids
    ]
    linked = {e.source_id for e in edges} | {e.target_id for e in edges}
    all_nodes = [n for n in store.nodes.values() if n.node_id in linked or n.node_id in node_ids]
    return {
        "entity": key,
        "nodes": [n.to_dict() for n in all_nodes],
        "edges": [e.to_dict() for e in edges],
    }
