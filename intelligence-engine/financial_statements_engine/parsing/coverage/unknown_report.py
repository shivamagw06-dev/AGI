"""Unknown label coverage report — projects into Unknown Metric Review Queue."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.parsing.quality.unknown_queue import list_queue


def build_unknown_label_report(
    matrix: dict[str, Any],
    *,
    unknown_fields: dict[str, Any] | list[str] | None = None,
    queued: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Nothing is discarded. Labels are audit-projected for Mission Control."""
    labels: list[str] = []
    if isinstance(unknown_fields, dict):
        labels = sorted(str(k) for k in unknown_fields.keys())
    elif isinstance(unknown_fields, list):
        labels = sorted(str(x) for x in unknown_fields)
    else:
        # Fall back to section attachments
        seen: set[str] = set()
        for sec in matrix.get("sections") or []:
            for u in sec.get("unknown_labels") or []:
                seen.add(str(u))
        labels = sorted(seen)

    queue_by_label: dict[str, dict[str, Any]] = {}
    for q in queued or list_queue(status=None):
        lab = str(q.get("original_label") or q.get("label") or "")
        if lab:
            queue_by_label[lab] = q

    rows: list[dict[str, Any]] = []
    for label in labels:
        q = queue_by_label.get(label) or {}
        # Find first section that attached this unknown
        section = None
        page = None
        for sec in matrix.get("sections") or []:
            if label in (sec.get("unknown_labels") or []):
                section = sec.get("domain")
                pages = sec.get("page_numbers") or []
                page = pages[0] if pages else None
                break
        rows.append(
            {
                "original_label": label,
                "page": page,
                "section": section,
                "document": matrix.get("document_hash"),
                "document_type": matrix.get("document_type"),
                "ticker": matrix.get("ticker"),
                "manifest_id": matrix.get("manifest_id"),
                "candidate_metric": q.get("candidate_metric") or q.get("proposed_canonical"),
                "confidence": q.get("confidence"),
                "review_status": q.get("review_status") or q.get("status") or "open",
                "queue_id": q.get("queue_id"),
            }
        )

    return {
        "matrix_id": matrix.get("matrix_id"),
        "ticker": matrix.get("ticker"),
        "n": len(rows),
        "rows": rows,
        "nothing_discarded": True,
        "issues_recommendations": False,
    }
