"""Evidence attachment for causal edges — no unsupported claims."""

from __future__ import annotations

from typing import Any


def evidence_for_edge(edge: dict[str, Any]) -> list[dict[str, Any]]:
    items = list(edge.get("evidence") or [])
    if not items:
        items.append(
            {
                "kind": "unvalidated",
                "note": "No historical validation attached — claim suppressed",
                "source": "causal_graph.evidence",
            }
        )
    return items


def evidence_pack(edges: list[dict[str, Any]]) -> dict[str, Any]:
    backed = [e for e in edges if e.get("validated") and (e.get("evidence") or e.get("evidence_years"))]
    return {
        "count": len(backed),
        "edge_count": len(edges),
        "unsupported_claims": max(0, len(edges) - len(backed)),
        "rule": "No unsupported causal claims — every edge requires evidence",
        "items": [
            {
                "source": e.get("source"),
                "target": e.get("target"),
                "confidence": e.get("confidence"),
                "evidence_years": e.get("evidence_years"),
                "evidence": evidence_for_edge(e),
            }
            for e in backed[:40]
        ],
    }
