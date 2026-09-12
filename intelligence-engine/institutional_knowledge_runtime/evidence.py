"""Evidence Graph bridge — refs only, no storage."""

from __future__ import annotations

from typing import Any


def resolve_evidence_for_assertion(
    assertion: dict[str, Any],
    evidence_graph: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Load supporting, contradicting, and neutral evidence refs from graph pack."""
    refs = assertion.get("evidence_refs") or []
    graph = evidence_graph or {}
    index: dict[str, dict[str, Any]] = {}
    for bucket in ("items", "evidence", "nodes"):
        items = graph.get(bucket)
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and item.get("evidence_id"):
                    index[str(item["evidence_id"])] = item
        elif isinstance(items, dict):
            index.update({str(k): v for k, v in items.items() if isinstance(v, dict)})

    supporting: list[dict[str, Any]] = []
    contradicting: list[dict[str, Any]] = []
    neutral: list[dict[str, Any]] = []

    for ref in refs:
        ref_id = ref.get("evidence_id") if isinstance(ref, dict) else str(ref)
        if not ref_id:
            continue
        node = index.get(str(ref_id))
        if not node:
            neutral.append({"evidence_id": ref_id, "resolved": False})
            continue
        role = str(node.get("role") or node.get("relation") or "supporting").lower()
        entry = {
            "evidence_id": ref_id,
            "resolved": True,
            "source_quality": node.get("source_quality", 70),
            "freshness": node.get("freshness", 70),
            "confidence": node.get("confidence", 70),
        }
        if role in {"contradict", "contradicting", "contradicts"}:
            contradicting.append(entry)
        elif role in {"neutral", "context"}:
            neutral.append(entry)
        else:
            supporting.append(entry)

    return {
        "assertion_id": assertion.get("assertion_id"),
        "supporting": supporting,
        "contradicting": contradicting,
        "neutral": neutral,
        "unresolved_refs": [n for n in neutral if not n.get("resolved")],
    }


def resolve_evidence(
    assertions: list[dict[str, Any]],
    evidence_graph: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """Resolve evidence packs for all assertions."""
    return {
        str(a.get("assertion_id")): resolve_evidence_for_assertion(a, evidence_graph)
        for a in assertions
        if a.get("assertion_id")
    }
