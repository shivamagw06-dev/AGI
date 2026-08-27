"""Module 9 — Concept Relationships.

Builds a deterministic graph directly from every card's ``related_concepts``
field (already validated to have zero dangling references — see
``concepts.validate_related_concepts``), so the graph and the library are
always in sync by construction rather than hand-maintained separately.

Illustrative chains from the Phase 2.6 brief:
    Enterprise Value -> Net Debt -> Interest Coverage -> Credit Ratings
        -> Cost of Debt -> WACC -> DCF
    ROE Decomposition -> DuPont Model -> (Financial Leverage, Asset Turnover)
"""

from __future__ import annotations

from collections import deque

from financial_concepts.concepts import ALL_CONCEPTS


def build_graph() -> dict[str, set[str]]:
    """Undirected adjacency: every related_concepts link is treated as a
    two-way edge, since 'A relates to B' is naturally symmetric even when
    only one card's author happened to list the link."""

    graph: dict[str, set[str]] = {k: set() for k in ALL_CONCEPTS}
    for key, card in ALL_CONCEPTS.items():
        for related in card.related_concepts:
            graph[key].add(related)
            graph.setdefault(related, set()).add(key)
    return graph


_GRAPH = build_graph()


def neighbors(key: str) -> list[str]:
    return sorted(_GRAPH.get(key, set()))


def shortest_path(start: str, end: str) -> list[str] | None:
    """BFS shortest path between two concept keys, or None if unreachable."""

    if start not in _GRAPH or end not in _GRAPH:
        return None
    if start == end:
        return [start]
    visited = {start}
    queue: deque[list[str]] = deque([[start]])
    while queue:
        path = queue.popleft()
        node = path[-1]
        for nxt in sorted(_GRAPH.get(node, set())):
            if nxt in visited:
                continue
            new_path = path + [nxt]
            if nxt == end:
                return new_path
            visited.add(nxt)
            queue.append(new_path)
    return None


def subgraph(keys: list[str]) -> dict[str, list[str]]:
    """Edges restricted to a given set of keys (e.g. one module)."""

    key_set = set(keys)
    return {
        k: sorted(v & key_set)
        for k, v in _GRAPH.items()
        if k in key_set
    }


def graph_summary() -> dict[str, int]:
    edge_count = sum(len(v) for v in _GRAPH.values()) // 2
    isolated = [k for k, v in _GRAPH.items() if not v]
    return {
        "nodes": len(_GRAPH),
        "edges": edge_count,
        "isolated_nodes": len(isolated),
        "avg_degree": round(sum(len(v) for v in _GRAPH.values()) / max(1, len(_GRAPH)), 2),
    }


def isolated_concepts() -> list[str]:
    return sorted(k for k, v in _GRAPH.items() if not v)
