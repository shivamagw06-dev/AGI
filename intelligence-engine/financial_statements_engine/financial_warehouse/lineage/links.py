"""Lineage references — every warehouse fact must be explainable."""

from __future__ import annotations

from typing import Any


def build_lineage_refs(draft: dict[str, Any], validated_pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "validation_id": validated_pack.get("validation_id") or draft.get("validation_id"),
        "draft_id": draft.get("draft_id") or validated_pack.get("draft_id"),
        "manifest_id": draft.get("manifest_id") or validated_pack.get("manifest_id"),
        "coverage_matrix_id": draft.get("coverage_matrix_id") or validated_pack.get("coverage_matrix_id"),
        "document_hash": draft.get("document_hash") or validated_pack.get("document_hash"),
        "evidence_id": draft.get("evidence_id"),
        "lineage_root_id": (draft.get("lineage") or {}).get("lineage_root_id"),
        "explainable": True,
    }
