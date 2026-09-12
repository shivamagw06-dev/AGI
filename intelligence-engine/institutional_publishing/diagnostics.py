"""PUB-01 diagnostics + Publication Center soft-slice metrics."""

from __future__ import annotations

from typing import Any, Sequence

from institutional_publishing.distribution import metrics as distribution_metrics
from institutional_publishing.models import InstitutionalPublication
from institutional_publishing.publication_registry import catalog
from institutional_publishing.schema import (
    PUBLICATION_ENGINE_VERSION,
    PUB_VERSION,
    PUB_WORKSTREAM_ID,
    RENDERERS,
)


def build_diagnostics(
    publication: InstitutionalPublication,
    *,
    latency_ms: float = 0.0,
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "workstream_id": PUB_WORKSTREAM_ID,
        "version": PUB_VERSION,
        "publication_engine_version": PUBLICATION_ENGINE_VERSION,
        "publication_id": publication.publication_id,
        "publication_type": publication.publication_type,
        "latency_ms": round(float(latency_ms), 2),
        "source_count": len(publication.source_objects),
        "evidence_count": len(publication.evidence),
        "section_count": len(publication.sections),
        "lineage_hash": publication.manifest.lineage_hash if publication.manifest else "",
        "template": publication.template,
        "validation": dict(validation or {}),
        "analyzes": False,
        "generates_recommendations": False,
        "compose_only": True,
        "manifest_is_audit_record": True,
    }


def publication_center_board(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    ok = sum(1 for r in rows if r.get("ok") is not False and r.get("status") != "failed")
    latencies = [
        float((r.get("diagnostics") or {}).get("latency_ms") or r.get("latency_ms") or 0)
        for r in rows
    ]
    missing_lineage = sum(
        1 for r in rows if not ((r.get("manifest") or {}).get("lineage_hash"))
    )
    failed_renders = sum(1 for r in rows if r.get("status") == "failed")
    types_covered = {r.get("publication_type") for r in rows if r.get("publication_type")}
    dist = distribution_metrics()
    return {
        "publication_success_rate": round(ok / total, 3) if total else 1.0,
        "generation_latency": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
        "template_coverage": len(catalog()),
        "types_generated": len(types_covered),
        "distribution_status": dist,
        "failed_renders": failed_renders,
        "version_integrity": missing_lineage == 0,
        "missing_lineage": missing_lineage,
        "publications_cached": total,
        "renderers": list(RENDERERS),
        "compose_only": True,
    }
