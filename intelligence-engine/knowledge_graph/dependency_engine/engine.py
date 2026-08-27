"""Dependency / contagion traversal — hidden exposures and reasoning paths."""

from __future__ import annotations

from typing import Any

from knowledge_graph.entity_resolution.resolve import resolve_entity
from knowledge_graph.graph.store import edges, node_for


def _adjacency(bidirectional: bool = False) -> dict[str, list[dict[str, Any]]]:
    adj: dict[str, list[dict[str, Any]]] = {}
    for e in edges():
        adj.setdefault(str(e["source"]), []).append(e)
        if bidirectional:
            # reverse walk for dependency discovery
            rev = dict(e)
            rev["_reversed"] = True
            adj.setdefault(str(e["target"]), []).append(rev)
    return adj


def traverse(
    start: str,
    *,
    max_depth: int = 4,
    max_paths: int = 12,
    relations: set[str] | None = None,
) -> list[dict[str, Any]]:
    resolved = resolve_entity(start)
    if not resolved:
        return []
    start_id = resolved["canonical_id"]
    adj = _adjacency(bidirectional=False)
    paths: list[dict[str, Any]] = []
    queue: list[tuple[str, list[dict[str, Any]]]] = [(start_id, [])]
    seen_paths: set[tuple[str, ...]] = set()
    while queue and len(paths) < max_paths * 3:
        node, path = queue.pop(0)
        if path:
            key = tuple([start_id] + [str(e.get("target") if not e.get("_reversed") else e.get("source")) for e in path])
            # rebuild node sequence
            nodes_path = [start_id]
            cur = start_id
            ok = True
            for e in path:
                nxt = str(e["target"])
                if e.get("_reversed"):
                    nxt = str(e["source"])
                nodes_path.append(nxt)
                cur = nxt
            key = tuple(nodes_path)
            if key not in seen_paths:
                seen_paths.add(key)
                labels = [(node_for(x) or {}).get("label") or x for x in nodes_path]
                paths.append(
                    {
                        "start": start_id,
                        "end": nodes_path[-1],
                        "depth": len(path),
                        "path": nodes_path,
                        "path_labels": labels,
                        "relations": [e.get("relation") for e in path],
                        "edges": path,
                        "path_strength": round(sum(float(e.get("strength") or 0) for e in path) / len(path), 3),
                        "path_confidence": round(sum(float(e.get("confidence") or 0) for e in path) / len(path), 3),
                    }
                )
        if len(path) >= max_depth:
            continue
        for e in adj.get(node, []):
            if relations and e.get("relation") not in relations:
                continue
            nxt = str(e["target"])
            if nxt in {start_id, *[str(x["target"]) for x in path]}:
                continue
            queue.append((nxt, path + [e]))
    paths.sort(key=lambda p: (-float(p.get("path_confidence") or 0), p.get("depth") or 99))
    return paths[:max_paths]


def dependencies_for(entity_id: str) -> dict[str, Any]:
    resolved = resolve_entity(entity_id)
    if not resolved:
        return {"found": False, "entity": entity_id}
    cid = resolved["canonical_id"]
    # Outbound depends_on / supplies / affected_by / customer_of
    dep_rels = {"depends_on", "supplies", "affected_by", "customer_of", "regulated_by", "drives", "imports_from"}
    paths = traverse(cid, max_depth=4, max_paths=15)
    dependency_paths = [p for p in paths if set(p.get("relations") or []) & dep_rels or True]
    # Classify exposures
    suppliers = []
    customers = []
    regulators = []
    macro = []
    tech = []
    for e in edges():
        if str(e.get("target")) == cid and e.get("relation") == "supplies":
            suppliers.append(e.get("source"))
        if str(e.get("source")) == cid and e.get("relation") == "customer_of":
            customers.append(e.get("target"))
        if str(e.get("source")) == cid and e.get("relation") == "regulated_by":
            regulators.append(e.get("target"))
        if str(e.get("target")) == cid and e.get("relation") in {"drives", "affected_by"}:
            src_node = node_for(str(e.get("source"))) or {}
            if src_node.get("type") in {"commodity", "currency", "interest_rate", "inflation", "central_bank", "event"}:
                macro.append(e.get("source"))
            if src_node.get("type") == "technology":
                tech.append(e.get("source"))
    return {
        "found": True,
        "canonical_id": cid,
        "suppliers": sorted(set(str(x) for x in suppliers)),
        "customers": sorted(set(str(x) for x in customers)),
        "regulators": sorted(set(str(x) for x in regulators)),
        "macro_drivers": sorted(set(str(x) for x in macro)),
        "technology_exposure": sorted(set(str(x) for x in tech)),
        "traversal_paths": dependency_paths[:12],
        "hidden_dependency_count": len(dependency_paths),
        "rule": "Dependency traversal is reproducible over the seeded institutional graph",
    }
