"""PUB-01 quality gates — reject incomplete or non-reproducible publications."""

from __future__ import annotations

from typing import Any, Optional

from institutional_publishing.models import InstitutionalPublication
from institutional_publishing.publication_registry import get
from institutional_publishing.schema import RENDERERS


def validate_publication(
    publication: InstitutionalPublication,
    *,
    renderer: str = "",
    known_ids: Optional[set[str]] = None,
) -> dict[str, Any]:
    errors: list[str] = []
    gates: dict[str, bool] = {}

    reg = get(publication.publication_type)
    gates["registered_type"] = reg is not None
    if not reg:
        errors.append("unknown publication type")

    # Source objects
    missing_sources = [s for s in publication.source_objects if not s.object_id]
    gates["source_objects_present"] = len(publication.source_objects) > 0 and not missing_sources
    if not publication.source_objects:
        errors.append("source objects missing")

    required = list(reg.required_sources) if reg else []
    have_types = {s.object_type for s in publication.source_objects}
    missing_required = [r for r in required if r not in have_types]
    gates["required_sources"] = not missing_required
    if missing_required:
        errors.append(f"source objects missing: {', '.join(missing_required)}")

    # Evidence
    gates["evidence_resolved"] = len(publication.evidence) > 0
    if not publication.evidence:
        errors.append("unresolved evidence references")

    # Lineage
    gates["lineage_intact"] = bool(publication.lineage) and bool(
        publication.manifest and publication.manifest.lineage_hash
    )
    if not publication.lineage or not (publication.manifest and publication.manifest.lineage_hash):
        errors.append("broken lineage")

    # Template
    gates["template_valid"] = bool(publication.template)
    if not publication.template:
        errors.append("template validation fails")

    # Duplicate id
    if known_ids and publication.publication_id in known_ids:
        errors.append("duplicate publication ID")
        gates["unique_id"] = False
    else:
        gates["unique_id"] = True

    # Renderer
    if renderer:
        gates["renderer_supported"] = renderer.lower() in RENDERERS
        if renderer.lower() not in RENDERERS:
            errors.append("unsupported renderer")
    else:
        gates["renderer_supported"] = True

    # Compose-only invariant
    if publication.analyzes:
        errors.append("publication must not analyze")
        gates["compose_only"] = False
    else:
        gates["compose_only"] = True

    ok = len(errors) == 0
    return {
        "ok": ok,
        "errors": errors,
        "gates": gates,
        "analyzes": False,
        "compose_only": True,
    }
