"""Pull evidence-like objects from pipeline surfaces without mutating frozen modules."""

from __future__ import annotations

from typing import Any


def _as_list(v: Any) -> list[Any]:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def from_evidence_graph(evidence_graph: dict[str, Any] | None) -> list[dict[str, Any]]:
    eg = evidence_graph or {}
    out: list[dict[str, Any]] = []
    for node in _as_list(eg.get("nodes")):
        if not isinstance(node, dict):
            continue
        item = dict(node)
        item.setdefault("kind", item.get("kind") or "evidence")
        item["_iew_origin"] = "evidence_graph"
        out.append(item)
    return out


def from_institutional_memory(institutional_memory: dict[str, Any] | None) -> list[dict[str, Any]]:
    im = institutional_memory or {}
    out: list[dict[str, Any]] = []
    memories = im.get("memories")
    if not memories:
        # scored[{memory: {...}}] shape
        for row in _as_list(im.get("scored")):
            if isinstance(row, dict) and isinstance(row.get("memory"), dict):
                m = dict(row["memory"])
                if row.get("similarity_score") is not None:
                    m["similarity_score"] = row.get("similarity_score")
                m["_iew_origin"] = "institutional_memory"
                m.setdefault("kind", "memory")
                m.setdefault("source", m.get("source") or "analogue")
                out.append(m)
        return out
    for m in _as_list(memories):
        if not isinstance(m, dict):
            continue
        item = dict(m)
        item["_iew_origin"] = "institutional_memory"
        item.setdefault("kind", "memory")
        item.setdefault("source", item.get("source") or "analogue")
        out.append(item)
    return out


def from_evidence_pack(evidence: dict[str, Any] | None) -> list[dict[str, Any]]:
    ev = evidence or {}
    out: list[dict[str, Any]] = []
    for item in _as_list(ev.get("top_evidence")):
        if isinstance(item, dict):
            row = dict(item)
            row["_iew_origin"] = "evidence_pack"
            out.append(row)
    # IERE nested pack
    for pack in _as_list((ev.get("packs") or {}).get("iere") if isinstance(ev.get("packs"), dict) else None):
        if not isinstance(pack, dict):
            continue
        for item in _as_list(pack.get("top_evidence") or pack.get("evidence")):
            if isinstance(item, dict):
                row = dict(item)
                row["_iew_origin"] = "iere"
                out.append(row)
    gov = ev.get("governance_packs") or {}
    if isinstance(gov, dict):
        for _k, pack in gov.items():
            if not isinstance(pack, dict):
                continue
            for item in _as_list(pack.get("top_evidence") or pack.get("evidence")):
                if isinstance(item, dict):
                    row = dict(item)
                    row["_iew_origin"] = "governance_pack"
                    out.append(row)
    return out


def collect_candidates(
    *,
    evidence_graph: dict[str, Any] | None = None,
    institutional_memory: dict[str, Any] | None = None,
    evidence: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Deduplicate by evidence_id / node_id / memory_id (first wins)."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for item in (
        from_evidence_graph(evidence_graph)
        + from_evidence_pack(evidence)
        + from_institutional_memory(institutional_memory)
    ):
        eid = str(
            item.get("evidence_id")
            or item.get("node_id")
            or item.get("memory_id")
            or item.get("document_id")
            or ""
        )
        if not eid:
            # Stable synthetic id from title+source for determinism
            eid = f"anon:{item.get('source')}:{item.get('title') or item.get('label')}"
            item["evidence_id"] = eid
        if eid in seen:
            continue
        seen.add(eid)
        out.append(item)
    return out
