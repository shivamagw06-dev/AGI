"""Turn validated events into governed causal candidates."""

from __future__ import annotations

import hashlib
from typing import Any, Iterable

from causal_research_engine.schema import CausalEvent, CausalRelationship, EvidenceReference


def normalize_event(row: dict[str, Any], *, analysis_as_of: str) -> CausalEvent:
    available = str(row.get("available_at") or row.get("publication_date") or row.get("event_date") or "")
    if not available or available > analysis_as_of:
        raise ValueError("POINT_IN_TIME_VIOLATION")
    source_id = str(row.get("source_id") or row.get("document_id") or row.get("url") or "")
    if not source_id:
        raise ValueError("MISSING_EVENT_PROVENANCE")
    event_id = str(row.get("event_id") or "CRE-EVENT-" + hashlib.sha256(f"{source_id}|{available}".encode()).hexdigest()[:16].upper())
    evidence = EvidenceReference(event_id + ":e1", str(row.get("source_type") or "document"), source_id,
                                 publication_date=str(row.get("publication_date") or available), available_at=available,
                                 passage=str(row.get("passage") or row.get("summary") or ""), quality=str(row.get("quality") or "UNVALIDATED"))
    return CausalEvent(event_id, str(row.get("title") or row.get("event_type") or "Event"),
                       str(row.get("event_type") or "unknown"), str(row.get("event_date") or available), available,
                       row.get("company_id") or row.get("ticker"), row.get("industry"),
                       tuple(str(x) for x in (row.get("claims") or [])), (evidence,))


def event_candidates(event: CausalEvent, relationships: Iterable[CausalRelationship]) -> list[CausalRelationship]:
    text = " ".join((event.title, event.event_type, *event.claims)).lower()
    ranked = []
    for rel in relationships:
        tokens = {x for x in f"{rel.cause} {rel.effect}".lower().replace("_", " ").split() if len(x) > 2}
        overlap = sum(1 for token in tokens if token in text)
        company_match = bool(event.company_id and rel.company_id == event.company_id)
        industry_match = bool(event.industry and rel.industry == event.industry)
        if overlap or company_match or industry_match:
            ranked.append((overlap + 2 * company_match + industry_match, rel))
    return [row for _, row in sorted(ranked, key=lambda item: (-item[0], item[1].relationship_id))]
