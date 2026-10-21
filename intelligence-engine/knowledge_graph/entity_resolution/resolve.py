"""Entity resolution — one canonical identity per real-world entity."""

from __future__ import annotations

from typing import Any

from knowledge_graph.graph.store import node_for, nodes


def _norm(s: str) -> str:
    return (
        (s or "")
        .strip()
        .upper()
        .replace(".NS", "")
        .replace(".BO", "")
        .replace(" LTD.", "")
        .replace(" LTD", "")
        .replace(" LIMITED", "")
        .replace(".", "")
        .replace(",", "")
        .replace("  ", " ")
    )


def resolve_entity(query: str) -> dict[str, Any] | None:
    q = (query or "").strip()
    if not q:
        return None
    # Direct id
    direct = node_for(q) or node_for(q.upper())
    if direct:
        return {
            "canonical_id": direct["id"],
            "node": direct,
            "matched_on": "id",
            "duplicate_free": True,
        }
    nq = _norm(q)
    # Alias / label match
    for n in nodes():
        candidates = [n.get("id"), n.get("label"), n.get("ticker"), *(n.get("aliases") or [])]
        for c in candidates:
            if c and _norm(str(c)) == nq:
                return {
                    "canonical_id": n["id"],
                    "node": deepcopy_node(n),
                    "matched_on": str(c),
                    "duplicate_free": True,
                }
        # NSE:/BSE: style
        for c in n.get("aliases") or []:
            if ":" in str(c) and _norm(str(c).split(":", 1)[-1]) == nq:
                return {
                    "canonical_id": n["id"],
                    "node": deepcopy_node(n),
                    "matched_on": str(c),
                    "duplicate_free": True,
                }
    return None


def deepcopy_node(n: dict[str, Any]) -> dict[str, Any]:
    from copy import deepcopy

    return deepcopy(n)


def resolve_ticker(ticker: str) -> str | None:
    aliases = {
        "HDFC": "HDFCBANK",
        "NESTLE": "NESTLEIND",
        "HUL": "HINDUNILVR",
        "SBI": "SBIN",
    }
    t = (ticker or "").upper().replace(".NS", "").replace(".BO", "")
    t = aliases.get(t, t)
    hit = resolve_entity(t)
    if hit and (hit.get("node") or {}).get("type") == "company":
        return hit["canonical_id"]
    # also allow resolving when ticker field matches
    if hit:
        return hit["canonical_id"]
    return None


def canonical_identity_report() -> dict[str, Any]:
    """Verify no duplicate companies for same canonical aliases."""
    seen_alias: dict[str, str] = {}
    duplicates: list[dict[str, str]] = []
    for n in nodes():
        if n.get("type") != "company":
            continue
        for a in [n.get("id"), n.get("ticker"), *(n.get("aliases") or [])]:
            if not a:
                continue
            key = _norm(str(a))
            if key in seen_alias and seen_alias[key] != n["id"]:
                duplicates.append({"alias": str(a), "a": seen_alias[key], "b": n["id"]})
            else:
                seen_alias[key] = n["id"]
    return {
        "duplicate_entities": duplicates,
        "no_duplicate_entities": len(duplicates) == 0,
        "canonical_companies": sum(1 for n in nodes() if n.get("type") == "company" and n.get("canonical")),
    }
