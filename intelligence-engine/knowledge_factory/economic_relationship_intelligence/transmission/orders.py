"""First / second / third-order economic transmission — from stored edges only."""

from __future__ import annotations

from typing import Any

from knowledge_factory.economic_relationship_intelligence.graph.engine import build_graph
from knowledge_factory.economic_relationship_intelligence.provenance import provenance
from knowledge_factory.economic_relationship_intelligence.schema import IERI_VERSION


def build_transmission_records(relationships: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Materialise explicit transmission edges into order records."""
    out: list[dict[str, Any]] = []
    for r in relationships:
        order = r.get("transmission_order")
        if order is None and r.get("relationship_type") != "transmission":
            continue
        tid = f"TX-{r.get('relationship_id')}"
        out.append(
            {
                "transmission_id": tid,
                "relationship_id": r.get("relationship_id"),
                "source_entity": r.get("source_entity"),
                "target_entity": r.get("target_entity"),
                "order": int(order or 1),
                "direction": r.get("shock_direction") or r.get("direction"),
                "strength": r.get("strength"),
                "time_horizon": r.get("time_horizon") or "UNKNOWN",
                "evidence": r.get("evidence"),
                "confidence": r.get("confidence"),
                "semantics": r.get("semantics"),
                "available_from": r.get("available_from"),
                "provenance": provenance(
                    source=str(r.get("source") or "unknown"),
                    collector="ieri.transmission",
                    confidence=float(r.get("confidence") or 0),
                    derived_from=[str(r.get("relationship_id"))],
                ),
                "version": IERI_VERSION,
                "fabricated": False,
            }
        )
    return out


def transmission_from_entity(
    entity: str,
    *,
    max_order: int = 3,
    shock_filter: str | None = None,
    as_of: str | None = None,
    limit: int = 50,
) -> dict[str, Any]:
    """Walk stored graph to surface 1st/2nd/3rd-order linked entities.

    Knowledge walk only — no autonomous inference of new edges.
    """
    g = build_graph(as_of=as_of)
    paths = g.paths(entity, max_depth=max_order, limit=limit * 3)
    by_order: dict[int, list[dict[str, Any]]] = {1: [], 2: [], 3: []}
    seen: set[tuple[int, str]] = set()

    for p in paths:
        order = min(int(p.get("length") or 1), 3)
        if not p.get("nodes") or len(p["nodes"]) < 2:
            continue
        terminal = p["nodes"][-1]
        key = (order, terminal)
        if key in seen:
            continue
        # optional shock filter on first edge
        if shock_filter:
            # inspect first relationship evidence via types — soft filter on path semantics
            pass
        seen.add(key)
        row = {
            "order": order,
            "entity": terminal,
            "path_nodes": p["nodes"],
            "types": p["types"],
            "semantics": p["semantics"],
            "min_confidence": p["min_confidence"],
            "relationship_ids": p["relationship_ids"],
        }
        by_order[order].append(row)
        if sum(len(v) for v in by_order.values()) >= limit:
            break

    # Also include direct edges with transmission_order / shock_direction
    direct = []
    for edge in g.neighbors(entity):
        if shock_filter and shock_filter not in str(edge.get("shock_direction") or ""):
            # allow partial match
            if shock_filter not in str(edge.get("notes") or ""):
                if edge.get("shock_direction") and shock_filter not in edge.get("shock_direction"):
                    continue
        order = int(edge.get("transmission_order") or 1)
        order = min(max(order, 1), 3)
        terminal = edge.get("to")
        key = (order, str(terminal))
        if key in seen:
            continue
        seen.add(key)
        item = {
            "order": order,
            "entity": terminal,
            "relationship_id": edge.get("relationship_id"),
            "relationship_type": edge.get("relationship_type"),
            "semantics": edge.get("semantics"),
            "strength": edge.get("strength"),
            "confidence": edge.get("confidence"),
            "shock_direction": edge.get("shock_direction"),
            "evidence": edge.get("evidence"),
            "time_horizon": edge.get("time_horizon"),
        }
        direct.append(item)
        by_order[order].append(item)

    return {
        "entity": entity,
        "max_order": max_order,
        "shock_filter": shock_filter,
        "first_order": by_order[1][:limit],
        "second_order": by_order[2][:limit],
        "third_order": by_order[3][:limit],
        "direct_edges": direct[:limit],
        "n": sum(len(by_order[i]) for i in (1, 2, 3)),
        "version": IERI_VERSION,
        "fabricated": False,
        "reasoning": False,
        "note": "Orders derived from stored relationship paths only.",
    }
