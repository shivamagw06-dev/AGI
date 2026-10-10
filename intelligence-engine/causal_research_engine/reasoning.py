"""Contradiction and temporal reasoning for CRE objects."""
from __future__ import annotations
import hashlib
from dataclasses import replace
from typing import Iterable
from causal_research_engine.schema import CausalRelationship, ContradictionGroup

def active_at(row: CausalRelationship, as_of: str) -> bool:
    return (not row.valid_from or row.valid_from <= as_of) and (not row.valid_to or row.valid_to >= as_of)

def temporal_slice(rows: Iterable[CausalRelationship], *, as_of: str) -> list[CausalRelationship]:
    return [row for row in rows if active_at(row, as_of)]

def detect_contradictions(rows: Iterable[CausalRelationship]) -> list[ContradictionGroup]:
    groups: dict[tuple[str, str, str | None], list[CausalRelationship]] = {}
    for row in rows:
        groups.setdefault((row.cause.lower(), row.effect.lower(), row.company_id), []).append(row)
    out = []
    for key, matches in groups.items():
        directions = {row.direction for row in matches}
        if not ({"POSITIVE", "NEGATIVE"} <= directions or "MIXED" in directions): continue
        ids = tuple(sorted(row.relationship_id for row in matches))
        evidence_ids = tuple(sorted({e.evidence_id for row in matches for e in row.evidence}))
        cid = "CRE-CONTRA-" + hashlib.sha256(f"{key}|{ids}".encode()).hexdigest()[:16].upper()
        out.append(ContradictionGroup(cid, ids, evidence_ids, company_id=key[2], severity="HIGH"))
    return out

def expire_stale(row: CausalRelationship, *, as_of: str) -> CausalRelationship:
    return replace(row, status="EXPIRED") if row.valid_to and row.valid_to < as_of and row.status not in {"REJECTED", "SUPERSEDED"} else row
