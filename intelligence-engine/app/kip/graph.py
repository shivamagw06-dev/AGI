"""Knowledge graph construction and entity neighborhood views."""

from __future__ import annotations

from app.kip.models import GraphEdge, GraphNode, KipDocument, KnowledgeGraphView


RELATION_PRIORITY = (
    "MENTIONS_COMPANY",
    "IN_SECTOR",
    "IN_INDUSTRY",
    "HAS_THEME",
    "MACRO_DRIVER",
    "SOURCED_FROM",
    "DOCUMENT_TYPE",
    "COMPETITOR_OF",
    "SUPPLIER_OF",
    "CUSTOMER_OF",
    "RELATED_RESEARCH",
    "RELATED_AGI_RESEARCH",
    "RELATED_BROKER_RESEARCH",
    "HAS_PREDICTION",
    "PREDICTION_OUTCOME",
    "IN_PORTFOLIO",
    "ON_TIMELINE",
)


def node_id(kind: str, key: str) -> str:
    return f"{kind}:{key}".upper()


def upsert_from_document(
    doc: KipDocument,
    *,
    nodes: dict[str, GraphNode],
    edges: list[GraphEdge],
) -> None:
    doc_node = node_id("document", doc.document_id)
    nodes[doc_node] = GraphNode(
        node_id=doc_node,
        kind="document",
        label=doc.document.title or doc.document_id,
        attributes={
            "document_type": doc.document.document_type.value,
            "version": doc.document.version,
            "source": doc.document.source,
            "broker": doc.document.broker,
        },
    )
    _edge(edges, doc_node, node_id("source", doc.document.source or "unknown"), "SOURCED_FROM", doc.document_id)
    nodes[node_id("source", doc.document.source or "unknown")] = GraphNode(
        node_id=node_id("source", doc.document.source or "unknown"),
        kind="source",
        label=doc.document.source or "unknown",
    )
    dtype = node_id("doctype", doc.document.document_type.value)
    nodes[dtype] = GraphNode(node_id=dtype, kind="document_type", label=doc.document.document_type.value)
    _edge(edges, doc_node, dtype, "DOCUMENT_TYPE", doc.document_id)

    for t in doc.investment.tickers:
        cid = node_id("company", t)
        nodes[cid] = GraphNode(node_id=cid, kind="company", label=t, attributes={"ticker": t})
        _edge(edges, doc_node, cid, "MENTIONS_COMPANY", doc.document_id)
        for sector in doc.investment.sectors:
            sid = node_id("sector", sector)
            nodes[sid] = GraphNode(node_id=sid, kind="sector", label=sector)
            _edge(edges, cid, sid, "IN_SECTOR", doc.document_id)
        for ind in doc.investment.industries:
            iid = node_id("industry", ind)
            nodes[iid] = GraphNode(node_id=iid, kind="industry", label=ind)
            _edge(edges, cid, iid, "IN_INDUSTRY", doc.document_id)
        for theme in doc.investment.themes:
            tid = node_id("theme", theme)
            nodes[tid] = GraphNode(node_id=tid, kind="theme", label=theme)
            _edge(edges, cid, tid, "HAS_THEME", doc.document_id)
            _edge(edges, doc_node, tid, "HAS_THEME", doc.document_id)
        for macro in doc.investment.macro_topics:
            mid = node_id("macro", macro)
            nodes[mid] = GraphNode(node_id=mid, kind="macro", label=macro)
            _edge(edges, cid, mid, "MACRO_DRIVER", doc.document_id)

    # Peer linkage among co-mentioned tickers
    tickers = doc.investment.tickers
    for i, a in enumerate(tickers):
        for b in tickers[i + 1 :]:
            _edge(edges, node_id("company", a), node_id("company", b), "COMPETITOR_OF", doc.document_id, weight=0.5)

    if doc.supersedes:
        prev = node_id("document", doc.supersedes)
        _edge(edges, doc_node, prev, "SUPERSEDES", doc.document_id)


def link_related_research(
    doc: KipDocument,
    related_docs: list[KipDocument],
    *,
    edges: list[GraphEdge],
) -> None:
    """Link broker ↔ AGI research sharing tickers; AGI articles ↔ each other."""
    doc_node = node_id("document", doc.document_id)
    dtype = doc.document.document_type.value
    is_agi = dtype.startswith("agi_")
    is_broker = "broker" in dtype or dtype in {"sell_side", "buy_side", "strategy_note", "newsletter"}
    for other in related_docs:
        if other.document_id == doc.document_id:
            continue
        other_type = other.document.document_type.value
        other_node = node_id("document", other.document_id)
        if is_agi and ("broker" in other_type or other_type in {"sell_side", "buy_side", "newsletter"}):
            _edge(edges, doc_node, other_node, "RELATED_BROKER_RESEARCH", doc.document_id, weight=0.8)
        elif is_broker and other_type.startswith("agi_"):
            _edge(edges, doc_node, other_node, "RELATED_AGI_RESEARCH", doc.document_id, weight=0.9)
        elif is_agi and other_type.startswith("agi_"):
            _edge(edges, doc_node, other_node, "RELATED_RESEARCH", doc.document_id, weight=0.7)


def link_prediction(
    prediction_id: str,
    ticker: str,
    document_id: str,
    *,
    nodes: dict[str, GraphNode],
    edges: list[GraphEdge],
    outcome: bool | None = None,
) -> None:
    pid = node_id("prediction", prediction_id)
    nodes[pid] = GraphNode(
        node_id=pid,
        kind="prediction",
        label=prediction_id,
        attributes={"ticker": ticker.upper(), "document_id": document_id},
    )
    _edge(edges, pid, node_id("company", ticker), "HAS_PREDICTION", document_id)
    _edge(edges, node_id("document", document_id), pid, "HAS_PREDICTION", document_id)
    if outcome is not None:
        oid = node_id("outcome", f"{prediction_id}_{'hit' if outcome else 'miss'}")
        nodes[oid] = GraphNode(
            node_id=oid,
            kind="outcome",
            label="hit" if outcome else "miss",
            attributes={"prediction_id": prediction_id},
        )
        _edge(edges, pid, oid, "PREDICTION_OUTCOME", document_id)


def view_for_entity(
    entity: str,
    *,
    nodes: dict[str, GraphNode],
    edges: list[GraphEdge],
) -> KnowledgeGraphView:
    key = entity.strip()
    candidates = [
        node_id("company", key),
        node_id("theme", key),
        node_id("sector", key),
        node_id("document", key),
        node_id("macro", key),
        key.upper() if ":" in key else "",
    ]
    root = next((c for c in candidates if c and c in nodes), None)
    if root is None:
        # fuzzy: match label
        for nid, n in nodes.items():
            if n.label.lower() == key.lower() or n.attributes.get("ticker", "").upper() == key.upper():
                root = nid
                break
    if root is None:
        return KnowledgeGraphView(entity=entity, nodes=[], edges=[])

    keep_nodes = {root}
    keep_edges: list[GraphEdge] = []
    for e in edges:
        if e.source == root or e.target == root:
            keep_edges.append(e)
            keep_nodes.add(e.source)
            keep_nodes.add(e.target)
    # one-hop expansion for company peers
    expanded = list(keep_edges)
    for e in edges:
        if e.source in keep_nodes and e.target in keep_nodes and e not in expanded:
            expanded.append(e)
            keep_nodes.add(e.source)
            keep_nodes.add(e.target)
    return KnowledgeGraphView(
        entity=entity,
        nodes=[nodes[n] for n in sorted(keep_nodes) if n in nodes],
        edges=expanded,
    )


def _edge(
    edges: list[GraphEdge],
    source: str,
    target: str,
    relation: str,
    document_id: str,
    weight: float = 1.0,
) -> None:
    for e in edges:
        if e.source == source and e.target == target and e.relation == relation and e.document_id == document_id:
            return
    edges.append(
        GraphEdge(
            source=source,
            target=target,
            relation=relation,
            document_id=document_id,
            weight=weight,
        )
    )
