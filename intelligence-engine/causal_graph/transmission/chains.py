"""Transmission engine — never stop at one relationship; build chains."""

from __future__ import annotations

from typing import Any

from causal_graph.company_links.seed import COMPANY_LINKS
from causal_graph.graph.store import edges as all_edges
from causal_graph.graph.store import node_for, resolve_company
from causal_graph.probabilities.model import chain_probability, edge_probability
from causal_graph.sector_links.models import model_for_sector


def _adjacency() -> dict[str, list[dict[str, Any]]]:
    adj: dict[str, list[dict[str, Any]]] = {}
    for e in all_edges():
        adj.setdefault(str(e["source"]), []).append(e)
    return adj


def transmission_from(
    start: str,
    *,
    max_depth: int = 5,
    max_chains: int = 12,
) -> list[dict[str, Any]]:
    """BFS-style path enumeration for first/second/third-order effects."""
    start_id = str(start)
    adj = _adjacency()
    chains: list[dict[str, Any]] = []
    queue: list[tuple[str, list[dict[str, Any]]]] = [(start_id, [])]
    seen_paths: set[tuple[str, ...]] = set()

    while queue and len(chains) < max_chains * 3:
        node, path = queue.pop(0)
        depth = len(path)
        if depth >= 1:
            key = tuple([start_id] + [str(e["target"]) for e in path])
            if key not in seen_paths:
                seen_paths.add(key)
                order = min(depth, 3)
                if depth == 1:
                    order_label = "primary"
                elif depth == 2:
                    order_label = "secondary"
                else:
                    order_label = "third_order" if depth == 3 else f"order_{depth}"
                path_nodes = [start_id] + [str(e["target"]) for e in path]
                labels = []
                for nid in path_nodes:
                    n = node_for(nid)
                    labels.append((n or {}).get("label") or nid)
                chains.append(
                    {
                        "start": start_id,
                        "end": path_nodes[-1],
                        "depth": depth,
                        "order": order,
                        "order_label": order_label,
                        "path": path_nodes,
                        "path_labels": labels,
                        "edges": path,
                        "path_strength": round(
                            sum(float(e.get("strength") or 0) for e in path) / len(path), 3
                        ),
                        "path_confidence": round(
                            sum(float(e.get("confidence") or 0) for e in path) / len(path), 3
                        ),
                        "transmission_probability": chain_probability(path),
                        "edge_probabilities": [edge_probability(e) for e in path],
                        "net_direction_sign": _net_sign(path),
                    }
                )
        if depth >= max_depth:
            continue
        for e in adj.get(node, []):
            nxt = str(e["target"])
            if nxt in {start_id, *[str(x["target"]) for x in path]}:
                continue
            queue.append((nxt, path + [e]))

    # Prefer stronger / higher-confidence shorter-to-medium chains
    chains.sort(
        key=lambda c: (
            -float(c.get("transmission_probability") or 0),
            -float(c.get("path_confidence") or 0),
            c.get("depth") or 99,
        )
    )
    return chains[:max_chains]


def _net_sign(path: list[dict[str, Any]]) -> int:
    sign = 1
    for e in path:
        sign *= int(e.get("direction_sign") or 1)
    return 1 if sign >= 0 else -1


def transmissions_for_company(ticker: str, *, max_chains: int = 10) -> dict[str, Any]:
    t = resolve_company(ticker)
    if not t:
        return {"ticker": (ticker or "").upper(), "found": False, "chains": [], "upstream_drivers": []}
    links = COMPANY_LINKS.get(t) or {}
    upstream = list(links.get("upstream") or [])
    # Chains ending at company + chains from each upstream driver
    inbound = [c for c in transmission_from(upstream[0], max_chains=max_chains * 2) if t in c.get("path", [])] if upstream else []
    # Also walk from sector / key drivers toward company via reverse lookup of useful paths
    driver_chains: list[dict[str, Any]] = []
    for driver in upstream[:5]:
        for c in transmission_from(driver, max_depth=4, max_chains=6):
            if t in c.get("path", []) or c.get("end") in {t, *(links.get("upstream") or [])}:
                driver_chains.append(c)
    # Direct company-centric view: paths that include the company node as end via synthetic reverse
    company_paths = []
    for e in all_edges():
        if str(e.get("target")) == t:
            company_paths.append(
                {
                    "start": str(e.get("source")),
                    "end": t,
                    "depth": 1,
                    "order": 1,
                    "order_label": "primary",
                    "path": [str(e.get("source")), t],
                    "path_labels": [
                        (node_for(str(e.get("source"))) or {}).get("label") or e.get("source"),
                        (node_for(t) or {}).get("label") or t,
                    ],
                    "edges": [e],
                    "path_strength": float(e.get("strength") or 0),
                    "path_confidence": float(e.get("confidence") or 0),
                    "transmission_probability": edge_probability(e),
                    "edge_probabilities": [edge_probability(e)],
                    "net_direction_sign": int(e.get("direction_sign") or 1),
                }
            )
    merged = company_paths + inbound + driver_chains
    # Dedup by path tuple
    seen: set[tuple[str, ...]] = set()
    uniq: list[dict[str, Any]] = []
    for c in merged:
        key = tuple(c.get("path") or [])
        if key in seen or not key:
            continue
        seen.add(key)
        uniq.append(c)
    uniq.sort(key=lambda c: (-float(c.get("transmission_probability") or 0), c.get("depth") or 99))
    sector = links.get("sector")
    model = model_for_sector(sector) if sector else None
    return {
        "ticker": t,
        "found": True,
        "sector": sector,
        "upstream_drivers": upstream,
        "sector_model": {
            "narrative": (model or {}).get("narrative"),
            "chain": (model or {}).get("chain"),
        }
        if model
        else None,
        "chains": uniq[:max_chains],
        "primary_effects": [c for c in uniq if c.get("order") == 1][:5],
        "secondary_effects": [c for c in uniq if c.get("order") == 2][:5],
        "third_order_effects": [c for c in uniq if (c.get("order") or 0) >= 3][:5],
    }
