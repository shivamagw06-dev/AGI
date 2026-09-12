"""Provenance helpers — no orphan nodes; every node must carry origin."""

from __future__ import annotations

from typing import Iterable, List

from institutional_graph.entities import Entity, Provenance
from institutional_graph.relationships import Relationship
from institutional_graph.schema import GRAPH_ENGINE_VERSION


def require_provenance(entity: Entity) -> List[str]:
    errors: list[str] = []
    if entity.provenance is None:
        errors.append(f"orphan node (missing provenance): {entity.id}")
        return errors
    if not entity.provenance.origin:
        errors.append(f"provenance.origin missing: {entity.id}")
    if not entity.provenance.timestamp:
        errors.append(f"provenance.timestamp missing: {entity.id}")
    if not entity.provenance.engine:
        errors.append(f"provenance.engine missing: {entity.id}")
    return errors


def require_relationship_source(rel: Relationship) -> List[str]:
    errors: list[str] = []
    if not rel.evidence_ids and not rel.inferred:
        # Inferred edges must still have provenance; base edges need evidence
        if rel.provenance is None or not rel.provenance.origin:
            errors.append(f"relationship without source: {rel.id}")
    if rel.provenance is None:
        errors.append(f"relationship missing provenance: {rel.id}")
    return errors


def build_provenance(
    *,
    origin: str,
    timestamp: str,
    source_document: str = "",
    evidence_ids: Iterable[str] = (),
    engine: str = GRAPH_ENGINE_VERSION,
    version: str = "",
) -> Provenance:
    return Provenance(
        origin=origin,
        timestamp=timestamp,
        source_document=source_document,
        evidence_ids=tuple(str(e) for e in evidence_ids if str(e).strip()),
        engine=engine,
        version=version or GRAPH_ENGINE_VERSION,
    )


LINEAGE_CHAIN = (
    "Evidence",
    "Entity",
    "Relationship",
    "Inference",
    "Reason",
    "Decision",
    "Calibration",
    "Report",
)
