"""Period recognition — never infer missing periods."""

from __future__ import annotations

from typing import Any


def recognise_period(meta: dict[str, Any] | None) -> dict[str, Any]:
    meta = meta or {}
    period_end = meta.get("period_end")
    period_type = meta.get("period_type") or meta.get("period_kind")
    consolidation = meta.get("consolidation_type") or meta.get("consolidation")
    scope = meta.get("statement_scope")

    unresolved = []
    if not period_end:
        unresolved.append("period_end")
    if not period_type:
        unresolved.append("period_type")

    kind = None
    if period_type:
        pt = str(period_type).lower()
        kind = {
            "annual": "annual",
            "yearly": "annual",
            "fy": "annual",
            "quarterly": "quarterly",
            "quarter": "quarterly",
            "half_year": "half_year",
            "half-yearly": "half_year",
            "h1": "half_year",
            "h2": "half_year",
            "nine_months": "nine_months",
            "9m": "nine_months",
            "ttm": "other",
        }.get(pt, pt if pt in ("annual", "quarterly", "half_year", "nine_months", "other") else "other")

    return {
        "period_end": period_end,  # may be null — never inferred
        "period_kind": kind,
        "fiscal_year": meta.get("fiscal_year"),
        "quarter": meta.get("fiscal_period") or meta.get("quarter"),
        "consolidation_type": consolidation or "unknown",
        "statement_scope": scope or "as_reported",
        "period_unresolved": unresolved,
        "inferred": False,
        "layer": "period_recognition",
    }
