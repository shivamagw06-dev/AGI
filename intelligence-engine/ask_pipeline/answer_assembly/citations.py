"""Stage 6 — Citation mapping: paragraph/section → evidence IDs → docs/objects."""

from __future__ import annotations

from typing import Any


def map_citations(
    *,
    skeleton: dict[str, Any],
    ordered: dict[str, Any],
    retrieval_id: str | None = None,
    as_of: str | None = None,
) -> dict[str, Any]:
    by_id = {i.get("evidence_id"): i for i in (ordered.get("ordered") or []) if i.get("evidence_id")}
    section_map: dict[str, list[dict[str, Any]]] = {}

    for name, section in (skeleton.get("sections") or {}).items():
        rows = []
        for eid in section.get("evidence_ids") or []:
            item = by_id.get(eid) or {}
            cit = item.get("citation") if isinstance(item.get("citation"), dict) else {}
            rows.append(
                {
                    "section": name,
                    "evidence_id": eid,
                    "knowledge_object": cit.get("knowledge_object") or item.get("evidence_type"),
                    "source": cit.get("source") or item.get("source"),
                    "collector": cit.get("collector") or item.get("collector"),
                    "document_id": cit.get("document_id") or item.get("document_id"),
                    "section_ref": cit.get("section"),
                    "page": cit.get("page"),
                    "paragraph": cit.get("paragraph"),
                    "checksum": cit.get("checksum"),
                    "available_from": item.get("available_from"),
                    "replay_id": retrieval_id,
                    "as_of": as_of,
                }
            )
        section_map[name] = rows

    flat = [r for rows in section_map.values() for r in rows]
    complete = sum(1 for r in flat if r.get("source") and r.get("evidence_id"))
    return {
        "stage": "citation_mapping",
        "by_section": section_map,
        "flat": flat,
        "mapped_count": len(flat),
        "complete_count": complete,
        "coverage": round(complete / len(flat), 4) if flat else 0.0,
        "retrieval_id": retrieval_id,
        "fabricated": False,
    }
