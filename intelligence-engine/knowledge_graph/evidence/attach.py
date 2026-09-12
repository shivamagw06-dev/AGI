"""Evidence engine — every edge must link to a source; unsupported rejected."""

from __future__ import annotations

from typing import Any


def evidence_for_edge(edge: dict[str, Any]) -> list[dict[str, Any]]:
    items = list(edge.get("evidence") or [])
    if not items:
        return []
    return items


def is_supported(edge: dict[str, Any]) -> bool:
    return bool(evidence_for_edge(edge)) and bool(edge.get("validated", True))


def evidence_pack(edges: list[dict[str, Any]]) -> dict[str, Any]:
    supported = [e for e in edges if is_supported(e)]
    rejected = [e for e in edges if not is_supported(e)]
    return {
        "count": len(supported),
        "edge_count": len(edges),
        "unsupported_rejected": len(rejected),
        "rule": "No unsupported relationships — every edge linked to evidence",
        "items": [
            {
                "source": e.get("source"),
                "target": e.get("target"),
                "relation": e.get("relation"),
                "confidence": e.get("confidence"),
                "evidence": evidence_for_edge(e),
            }
            for e in supported[:50]
        ],
    }
