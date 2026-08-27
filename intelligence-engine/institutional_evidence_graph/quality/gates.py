"""IEG quality gates."""

from __future__ import annotations

from typing import Any


def validate_graph(
    *,
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
    entity_trees: dict[str, Any],
    as_of: str | None,
) -> dict[str, Any]:
    failures: list[str] = []
    if not nodes:
        failures.append("empty_nodes")
    if any(n.get("fabricated") for n in nodes):
        failures.append("fabricated_node")
    # Replay: no future leakage check on historical_event timestamps
    if as_of:
        for n in nodes:
            if n.get("kind") not in {"evidence", "historical_event", "relationship", "relationship_stub"}:
                continue
            af = n.get("available_from") or n.get("timestamp")
            if af and str(af)[:10] > str(as_of)[:10]:
                failures.append(f"future_leak:{n.get('node_id')}")
                break
    return {
        "passed": not failures,
        "failures": failures,
        "n_nodes": len(nodes),
        "n_edges": len(edges),
        "n_entities": len(entity_trees),
        "as_of": as_of,
        "fabricated": False,
    }
