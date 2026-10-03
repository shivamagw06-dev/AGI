"""Relationship chains — institutional analyst path rendering."""

from __future__ import annotations

from typing import Any


def build_chains(
    *,
    entity: str,
    transmission: dict[str, Any] | None,
    relationship_buckets: dict[str, list[dict[str, Any]]] | None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    """Produce ordered relationship chains (not isolated facts)."""
    chains: list[dict[str, Any]] = []
    eid = str(entity).upper()

    # Competitors chain
    comps = (relationship_buckets or {}).get("competitors") or []
    if comps:
        nodes = [eid] + [str(c.get("counterpart")) for c in comps[:4] if c.get("counterpart")]
        chains.append(
            {
                "chain_id": f"competitors:{eid}",
                "kind": "competitors",
                "nodes": nodes,
                "arrow_text": " → ".join(nodes),
                "order": 1,
                "source": "ieri",
            }
        )

    # Commodity / macro exposure
    commodities = (relationship_buckets or {}).get("commodity_inputs") or []
    if commodities:
        for c in commodities[:3]:
            cp = str(c.get("counterpart") or "commodity")
            chains.append(
                {
                    "chain_id": f"macro:{eid}:{cp}",
                    "kind": "macro_exposure",
                    "nodes": [cp, eid],
                    "arrow_text": f"{cp} → {eid}",
                    "order": int(c.get("transmission_order") or 1),
                    "source": "ieri",
                    "shock": c.get("shock_direction"),
                }
            )

    # Transmission paths from IERI (first/second/third_order)
    tx = transmission or {}
    for order_key, order_n in (
        ("first_order", 1),
        ("second_order", 2),
        ("third_order", 3),
    ):
        rows = tx.get(order_key)
        if not isinstance(rows, list):
            continue
        for row in rows[:4]:
            path = row.get("path_nodes") or row.get("nodes") or []
            if not path and row.get("entity"):
                path = [eid, str(row.get("entity"))]
            if len(path) < 2:
                continue
            chains.append(
                {
                    "chain_id": f"tx:{eid}:{'-'.join(map(str, path))[:48]}",
                    "kind": "transmission",
                    "nodes": list(path),
                    "arrow_text": " → ".join(map(str, path)),
                    "order": int(row.get("order") or order_n),
                    "source": "ieri.transmission",
                }
            )

    # Deduplicate by arrow_text
    seen: set[str] = set()
    uniq = []
    for c in chains:
        key = c.get("arrow_text") or c.get("chain_id")
        if key in seen:
            continue
        seen.add(str(key))
        uniq.append(c)
        if len(uniq) >= limit:
            break
    return uniq


def chain_bullets(chains: list[dict[str, Any]], *, max_items: int = 8) -> list[str]:
    out = []
    for c in chains[:max_items]:
        kind = c.get("kind") or "relationship"
        arrow = c.get("arrow_text")
        if arrow:
            out.append(f"Evidence chain ({kind}): {arrow}")
    return out
