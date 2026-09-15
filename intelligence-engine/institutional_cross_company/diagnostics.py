"""CCI-01 diagnostics + Relationship Center soft-slice metrics."""

from __future__ import annotations

from collections import Counter
from typing import Any, Sequence

from institutional_cross_company.models import InstitutionalRelationship
from institutional_cross_company.schema import (
    CCI_VERSION,
    CCI_WORKSTREAM_ID,
    RELATIONSHIP_ENGINE_VERSION,
)
from institutional_cross_company.relationship_registry import catalog


def build_diagnostics(
    rels: Sequence[InstitutionalRelationship],
    *,
    latency_ms: float = 0.0,
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    types = Counter(r.relationship_type for r in rels)
    hubs = Counter()
    for r in rels:
        hubs[r.source_entity] += 1
        hubs[r.target_entity] += 1
    missing_evidence = sum(1 for r in rels if not r.evidence)
    kg_backed = sum(1 for r in rels if r.kg_backed)
    return {
        "workstream_id": CCI_WORKSTREAM_ID,
        "version": CCI_VERSION,
        "relationship_engine_version": RELATIONSHIP_ENGINE_VERSION,
        "latency_ms": round(float(latency_ms), 2),
        "relationship_count": len(rels),
        "type_counts": dict(types),
        "missing_evidence": missing_evidence,
        "kg_backed_count": kg_backed,
        "strongest_hubs": [{"entity": e, "degree": n} for e, n in hubs.most_common(8)],
        "provider_count": len(catalog()),
        "validation": dict(validation or {}),
        "owns_graph": False,
        "graph_system_of_record": "KG-01",
        "predictive": False,
        "generates_recommendations": False,
    }


def relationship_center_board(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    coverage = 0
    missing = 0
    hubs: Counter = Counter()
    latencies: list[float] = []
    for row in rows:
        diag = row.get("diagnostics") or {}
        coverage += int(diag.get("relationship_count") or 0)
        missing += int(diag.get("missing_evidence") or 0)
        for h in diag.get("strongest_hubs") or []:
            hubs[h.get("entity")] += int(h.get("degree") or 0)
        if diag.get("latency_ms") is not None:
            latencies.append(float(diag["latency_ms"]))
    providers = catalog()
    return {
        "relationship_coverage": coverage,
        "missing_links": missing,
        "strongest_hubs": [{"entity": e, "degree": n} for e, n in hubs.most_common(6)],
        "propagation_latency": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        "graph_integrity": "delegated_to_KG-01",
        "cluster_health": "ok",
        "provider_count": len(providers),
        "providers_missing": [p["relationship_type"] for p in providers if not p.get("has_provider")],
        "owns_graph": False,
    }
