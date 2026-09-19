"""Module 6 — Knowledge Graph.

Builds a stable-ID entity/relationship graph from the facts produced by
Modules 2-4: Company -> Sector/Industry (from document metadata), Executives
(from management statements), and Customers/Suppliers/Competition/Peers
(from Module 2 knowledge objects, via lightweight name extraction).

Node IDs are stable slugs (``company_reliance``, ``person_narayana_murthy``)
so repeated ingestion of new documents upserts into the same nodes rather
than duplicating them — this is what lets Module 10 (Incremental Learning)
grow the graph instead of rebuilding it.
"""

from __future__ import annotations

import re
from typing import Iterable

from kip_v2.schema import Fact, GraphEdge, GraphNode

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    return _SLUG_RE.sub("_", name.strip().lower()).strip("_") or "unknown"


def node_id(node_type: str, name: str) -> str:
    return f"{node_type}_{slugify(name)}"


def company_node(company_id: str, company_name: str, sector: str | None = None, industry: str | None = None) -> tuple[list[GraphNode], list[GraphEdge]]:
    nodes = [GraphNode(node_id=company_id, node_type="company", name=company_name)]
    edges: list[GraphEdge] = []
    if sector:
        sector_id = node_id("sector", sector)
        nodes.append(GraphNode(node_id=sector_id, node_type="sector", name=sector))
        edges.append(GraphEdge(edge_id=f"{company_id}__belongs_to__{sector_id}", source_id=company_id, target_id=sector_id, relation="belongs_to_sector"))
    if industry:
        industry_id = node_id("industry", industry)
        nodes.append(GraphNode(node_id=industry_id, node_type="industry", name=industry))
        edges.append(GraphEdge(edge_id=f"{company_id}__belongs_to__{industry_id}", source_id=company_id, target_id=industry_id, relation="belongs_to_industry"))
    return nodes, edges


_ENTITY_CATEGORY_RELATION = {
    "customers": ("customer", "has_customer"),
    "suppliers": ("supplier", "has_supplier"),
    "competition": ("peer", "competes_with"),
}


def graph_from_facts(company_id: str, facts: Iterable[Fact]) -> tuple[list[GraphNode], list[GraphEdge]]:
    """Derives graph nodes/edges from already-extracted, evidence-backed
    facts (management statements -> executives; customers/suppliers/
    competition knowledge objects -> relationship edges)."""

    nodes: list[GraphNode] = []
    edges: list[GraphEdge] = []
    seen_nodes: set[str] = set()
    seen_edges: set[str] = set()

    def add_node(node: GraphNode) -> None:
        if node.node_id not in seen_nodes:
            seen_nodes.add(node.node_id)
            nodes.append(node)

    def add_edge(edge: GraphEdge) -> None:
        if edge.edge_id not in seen_edges:
            seen_edges.add(edge.edge_id)
            edges.append(edge)

    for fact in facts:
        if fact.category == "management_statement":
            speaker = (fact.extra or {}).get("speaker")
            if speaker:
                exec_id = node_id("person", speaker)
                add_node(GraphNode(node_id=exec_id, node_type="executive", name=speaker,
                                    attributes={"title": (fact.extra or {}).get("title")}))
                edge_id = f"{exec_id}__works_at__{company_id}"
                add_edge(GraphEdge(edge_id=edge_id, source_id=exec_id, target_id=company_id, relation="works_at",
                                    confidence=fact.confidence, evidence_hash=fact.evidence.evidence_hash))
        elif fact.category in _ENTITY_CATEGORY_RELATION:
            node_type, relation = _ENTITY_CATEGORY_RELATION[fact.category]
            for mention in _extract_named_mentions(str(fact.value)):
                mention_id = node_id(node_type, mention)
                add_node(GraphNode(node_id=mention_id, node_type=node_type, name=mention))
                edge_id = f"{company_id}__{relation}__{mention_id}"
                add_edge(GraphEdge(edge_id=edge_id, source_id=company_id, target_id=mention_id, relation=relation,
                                    confidence=fact.confidence, evidence_hash=fact.evidence.evidence_hash))

    return nodes, edges


_PROPER_NOUN_RUN = re.compile(r"\b([A-Z][a-zA-Z&]*(?:\s+[A-Z][a-zA-Z&]*){0,2})\b")
_COMMON_START = {"The", "Our", "This", "It", "We", "In", "For", "As", "Key", "Top"}


def _extract_named_mentions(text: str, limit: int = 5) -> list[str]:
    found: list[str] = []
    for m in _PROPER_NOUN_RUN.finditer(text):
        phrase = m.group(1).strip()
        if phrase.split()[0] in _COMMON_START or len(phrase) < 4:
            continue
        if phrase not in found:
            found.append(phrase)
        if len(found) >= limit:
            break
    return found
