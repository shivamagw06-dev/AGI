"""Market knowledge graph — connect companies, sectors, themes, macro, research."""

from __future__ import annotations

from typing import Any

from app.investment_office.playbooks import PLAYBOOKS, playbook_for_sector
from app.schemas.models import KnowledgeGraphEdge, KnowledgeGraphNode


def build_knowledge_graph(
    *,
    symbols: list[str],
    sectors: list[str] | None = None,
    playbooks: list[dict[str, Any]] | None = None,
    queue: list[Any] | None = None,
    calendar: list[Any] | None = None,
    macro_labels: list[str] | None = None,
) -> dict[str, Any]:
    nodes: dict[str, KnowledgeGraphNode] = {}
    edges: list[KnowledgeGraphEdge] = []

    def add_node(node: KnowledgeGraphNode) -> None:
        nodes[node.node_id] = node

    def add_edge(source: str, target: str, relation: str, evidence: list[str] | None = None) -> None:
        if source in nodes and target in nodes:
            edges.append(
                KnowledgeGraphEdge(
                    source=source,
                    target=target,
                    relation=relation,
                    evidence=evidence or [],
                )
            )

    for pb in playbooks or list(PLAYBOOKS.values()):
        pid = f"playbook:{pb.get('id') or pb.get('title')}"
        add_node(
            KnowledgeGraphNode(
                node_id=pid,
                label=str(pb.get("title") or pb.get("id")),
                kind="playbook",
                meta={"id": pb.get("id")},
            )
        )
        for theme in pb.get("themes") or []:
            tid = f"theme:{theme}"
            add_node(KnowledgeGraphNode(node_id=tid, label=str(theme), kind="theme"))
            add_edge(pid, tid, "covers_theme", ["playbook_template"])
        for co in pb.get("leading_companies") or []:
            cid = f"company:{str(co).upper()}"
            add_node(
                KnowledgeGraphNode(node_id=cid, label=str(co).upper(), kind="company")
            )
            add_edge(pid, cid, "leading_company", ["playbook_template"])
            sid = f"sector:{pb.get('title')}"
            add_node(
                KnowledgeGraphNode(
                    node_id=sid,
                    label=str(pb.get("title")),
                    kind="sector",
                )
            )
            add_edge(cid, sid, "in_sector", ["playbook_template"])
        for risk in (pb.get("risks") or [])[:4]:
            rid = f"risk:{pb.get('id')}:{risk[:24]}"
            add_node(KnowledgeGraphNode(node_id=rid, label=str(risk), kind="risk"))
            add_edge(pid, rid, "has_risk", ["playbook_template"])

    for sector in sectors or []:
        pb = playbook_for_sector(sector)
        if not pb:
            sid = f"sector:{sector}"
            add_node(KnowledgeGraphNode(node_id=sid, label=sector, kind="sector"))
            continue
        # already linked via playbook

    for sym in symbols:
        cid = f"company:{sym.upper()}"
        add_node(KnowledgeGraphNode(node_id=cid, label=sym.upper(), kind="company"))

    for label in macro_labels or []:
        mid = f"macro:{label[:40]}"
        add_node(KnowledgeGraphNode(node_id=mid, label=str(label)[:80], kind="macro"))
        # Link macro to themes loosely when keyword overlap
        low = str(label).lower()
        for theme_key in ("rates", "inflation", "oil", "credit", "policy", "usd"):
            if theme_key in low:
                tid = f"theme:{theme_key}"
                add_node(KnowledgeGraphNode(node_id=tid, label=theme_key, kind="theme"))
                add_edge(mid, tid, "macro_theme", ["macro_briefing"])

    for item in queue or []:
        data = item.model_dump() if hasattr(item, "model_dump") else dict(item)
        sym = data.get("symbol")
        if not sym:
            continue
        rid = f"research:{sym}:{data.get('item_id') or data.get('title')}"
        add_node(
            KnowledgeGraphNode(
                node_id=rid,
                label=str(data.get("title") or sym),
                kind="research",
                meta={"priority": data.get("priority")},
            )
        )
        add_edge(f"company:{str(sym).upper()}", rid, "queued_research", data.get("evidence") or [])

    for ev in calendar or []:
        data = ev.model_dump() if hasattr(ev, "model_dump") else dict(ev)
        if data.get("status") == "withheld":
            continue
        eid = f"event:{data.get('event_id') or data.get('title')}"
        add_node(
            KnowledgeGraphNode(
                node_id=eid,
                label=str(data.get("title")),
                kind="event",
                meta={"category": data.get("category"), "date": data.get("date")},
            )
        )
        for sym in data.get("symbols") or []:
            add_edge(f"company:{str(sym).upper()}", eid, "has_event", data.get("evidence") or [])

    # Forecast nodes are structural placeholders — withheld without Forecast Layer
    add_node(
        KnowledgeGraphNode(
            node_id="forecast:layer",
            label="Forecast Intelligence",
            kind="forecast",
            meta={"status": "withheld_without_engine"},
        )
    )

    return {
        "nodes": [n.model_dump() for n in nodes.values()],
        "edges": [e.model_dump() for e in edges],
        "note": "Graph connects packaged entities only — no fabricated relationships.",
    }
