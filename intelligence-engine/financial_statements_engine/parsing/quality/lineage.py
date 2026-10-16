"""Lineage graph — Raw Document → … → Canonical Draft (validated hops later)."""

from __future__ import annotations

import hashlib
from typing import Any

from financial_statements_engine.util import now_iso


def build_lineage_root(
    *,
    evidence_id: str,
    document_hash: str,
    ticker: str,
    manifest_id: str,
    draft_id: str,
) -> dict[str, Any]:
    root_id = f"lin:{hashlib.sha256(f'{evidence_id}|{manifest_id}'.encode()).hexdigest()[:20]}"
    return {
        "lineage_root_id": root_id,
        "nodes": [
            {"hop": "raw_document", "ref": evidence_id, "document_hash": document_hash},
            {"hop": "parse_manifest", "ref": manifest_id},
            {"hop": "canonical_draft", "ref": draft_id},
            # Future: validated_fact → derived_metric → consumer
        ],
        "ticker": ticker,
        "as_of": now_iso(),
        "layer": "lineage_graph",
    }


def fact_lineage(
    *,
    lineage_root_id: str,
    section: str | None,
    source_field: str | None,
    metric: str,
    evidence_id: str,
    table_id: str | None = None,
    row_id: str | None = None,
    column_id: str | None = None,
    cell_id: str | None = None,
) -> dict[str, Any]:
    return {
        "lineage_root_id": lineage_root_id,
        "path": [
            {"hop": "raw_document", "ref": evidence_id},
            {"hop": "section", "ref": section},
            {"hop": "table", "ref": table_id},
            {"hop": "row", "ref": row_id},
            {"hop": "cell", "ref": cell_id or column_id},
            {"hop": "metric_label", "ref": source_field},
            {"hop": "canonical_metric", "ref": metric},
            {"hop": "canonical_draft", "ref": None},  # filled by caller
        ],
        "explainable": True,
    }
