"""Build directed execution graph (DAG) with topological order."""

from __future__ import annotations

from typing import Any


def build_execution_graph(
    participants: list[str],
    dependency_edges: list[dict[str, str]],
    *,
    modes: dict[str, str] | None = None,
    importance: dict[str, int] | None = None,
) -> dict[str, Any]:
    modes = modes or {}
    importance = importance or {}
    preds: dict[str, set[str]] = {p: set() for p in participants}
    succs: dict[str, set[str]] = {p: set() for p in participants}
    for e in dependency_edges:
        a, b = e["from"], e["to"]
        if a in preds and b in preds:
            preds[b].add(a)
            succs[a].add(b)

    # Kahn topological sort; stable by canonical order among ready nodes
    order_index = {p: i for i, p in enumerate(participants)}
    ready = sorted([p for p in participants if not preds[p]], key=lambda x: order_index[x])
    topo: list[str] = []
    pred_count = {p: len(preds[p]) for p in participants}
    while ready:
        node = ready.pop(0)
        topo.append(node)
        for s in sorted(succs[node], key=lambda x: order_index[x]):
            pred_count[s] -= 1
            if pred_count[s] == 0:
                ready.append(s)
                ready.sort(key=lambda x: order_index[x])

    # If cycle leftover, append remaining in original order
    if len(topo) < len(participants):
        for p in participants:
            if p not in topo:
                topo.append(p)

    nodes = [
        {
            "id": p,
            "layer": p,
            "mode": modes.get(p, "Required"),
            "importance": importance.get(p, 0),
            "depends_on": sorted(preds.get(p) or []),
            "status": "planned",
        }
        for p in topo
    ]
    return {
        "execution_order": topo,
        "nodes": nodes,
        "edges": dependency_edges,
        "node_count": len(nodes),
        "edge_count": len(dependency_edges),
    }
