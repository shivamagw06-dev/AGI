"""IERE quality gates."""

from __future__ import annotations

from typing import Any


def evaluate_retrieval_gates(
    *,
    ranked: list[dict[str, Any]],
    packs: list[dict[str, Any]],
    graph: dict[str, Any],
    as_of: str | None,
) -> dict[str, Any]:
    failures: list[str] = []
    day = str(as_of)[:10] if as_of else None

    for item in ranked:
        cit = item.get("citation") or {}
        if not cit.get("source") or not cit.get("knowledge_object"):
            failures.append("missing_provenance")
        if day and str(item.get("available_from") or "")[:10] > day:
            failures.append("future_leakage")
        if item.get("duplicate"):
            failures.append("duplicate_evidence")
        if not item.get("source"):
            failures.append("unknown_source")
        # citation mismatch
        if cit.get("evidence_id") and cit.get("evidence_id") != item.get("evidence_id"):
            failures.append("citation_mismatch")

    if graph:
        for e in graph.get("edges") or []:
            if e.get("weight") is None or not e.get("from") or not e.get("to"):
                failures.append("broken_graph")
        node_ids = {n.get("id") for n in (graph.get("nodes") or [])}
        for e in graph.get("edges") or []:
            if e.get("from") not in node_ids or e.get("to") not in node_ids:
                failures.append("broken_graph")

    if not packs and ranked:
        failures.append("assembly_empty")

    # conflicting versions: same document_id different checksums
    by_doc: dict[str, set[str]] = {}
    for item in ranked:
        did = item.get("document_id")
        if did and item.get("checksum"):
            by_doc.setdefault(str(did), set()).add(str(item["checksum"]))
    for checksums in by_doc.values():
        if len(checksums) > 1:
            failures.append("conflicting_versions")

    failures = sorted(set(failures))
    return {
        "passed": not failures,
        "failures": failures,
        "checked_items": len(ranked),
        "checked_packs": len(packs),
    }
