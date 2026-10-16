"""Validate derived sector drafts before normalization."""

from __future__ import annotations

from typing import Any

from continuous_sector_knowledge.schema import SECTOR_UNIVERSE, RawSectorDraft, canonicalize


def validate_draft(draft: RawSectorDraft) -> dict[str, Any]:
    errors: list[str] = []
    key = canonicalize(draft.sector_key) or draft.sector_key
    if key not in SECTOR_UNIVERSE:
        errors.append("unknown_sector")
    if not draft.label:
        errors.append("label_required")
    if not draft.catalog:
        errors.append("catalog_required")
    if not draft.source_layers:
        errors.append("source_layers_required")
    # Must be derived from AGI layers — never claim external live fetch
    if "external_api" in draft.source_layers:
        errors.append("external_api_forbidden")
    return {
        "ok": not errors,
        "errors": errors,
        "sector_key": key,
        "providers_queried": [],
    }
