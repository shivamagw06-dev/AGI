"""Point-in-time filter for evidence graph nodes/edges."""

from __future__ import annotations

from typing import Any


def available_on_or_before(available_from: str | None, as_of: str | None) -> bool:
    if not as_of:
        return True
    if not available_from:
        return False  # unknown timing — exclude in replay (no leakage)
    return str(available_from)[:10] <= str(as_of)[:10]


def filter_nodes(nodes: list[dict[str, Any]], *, as_of: str | None) -> list[dict[str, Any]]:
    if not as_of:
        return list(nodes)
    out = []
    for n in nodes:
        if n.get("kind") in {"entity", "domain", "question"}:
            out.append(n)
            continue
        af = n.get("available_from") or n.get("timestamp")
        if available_on_or_before(af if isinstance(af, str) else None, as_of):
            out.append(n)
    return out


def filter_edges(
    edges: list[dict[str, Any]],
    *,
    node_ids: set[str],
    as_of: str | None,
) -> list[dict[str, Any]]:
    out = []
    for e in edges:
        if e.get("source") not in node_ids or e.get("target") not in node_ids:
            continue
        af = e.get("available_from")
        if as_of and af and not available_on_or_before(str(af), as_of):
            continue
        out.append(e)
    return out
