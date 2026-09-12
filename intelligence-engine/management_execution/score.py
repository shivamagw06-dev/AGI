"""Management Execution Score — deterministic, non-judgemental."""

from __future__ import annotations

from typing import Any

from management_execution.schema import (
    STATUS_CANNOT,
    STATUS_DELIVERED,
    STATUS_NOT_YET,
    STATUS_PARTIAL,
    STATUS_SUPERSEDED,
)


def execution_score(
    findings: list[dict[str, Any]],
    *,
    coverage_pct: float | None = None,
) -> dict[str, Any]:
    delivered = sum(1 for f in findings if f.get("current_status") == STATUS_DELIVERED)
    partial = sum(1 for f in findings if f.get("current_status") == STATUS_PARTIAL)
    outstanding = sum(1 for f in findings if f.get("current_status") == STATUS_NOT_YET)
    cannot = sum(1 for f in findings if f.get("current_status") == STATUS_CANNOT)
    superseded = sum(1 for f in findings if f.get("current_status") == STATUS_SUPERSEDED)

    applicable = delivered + partial + outstanding
    if applicable > 0:
        raw = 100.0 * (delivered + 0.5 * partial) / applicable
    else:
        raw = None

    # Evidence quality / coverage soft adjustment (never subjective judgement)
    adjusted = raw
    if raw is not None and coverage_pct is not None:
        if coverage_pct >= 80:
            adjusted = min(100.0, raw + 2.0)
        elif coverage_pct < 40:
            adjusted = max(0.0, raw - 5.0)

    delivery_months = [
        float(f["delivery_months"])
        for f in findings
        if f.get("current_status") == STATUS_DELIVERED and isinstance(f.get("delivery_months"), (int, float))
    ]
    avg_delivery = round(sum(delivery_months) / len(delivery_months), 1) if delivery_months else None

    delivered_pct = round(100.0 * delivered / applicable, 2) if applicable else None
    outstanding_pct = round(100.0 * outstanding / applicable, 2) if applicable else None

    return {
        "management_execution_score": round(adjusted, 2) if adjusted is not None else None,
        "raw_score": round(raw, 2) if raw is not None else None,
        "delivered": delivered,
        "partially_delivered": partial,
        "outstanding": outstanding,
        "cannot_yet_evaluate": cannot,
        "superseded": superseded,
        "applicable_n": applicable,
        "objectives_tracked": len(findings),
        "delivered_pct": delivered_pct,
        "outstanding_pct": outstanding_pct,
        "average_delivery_months": avg_delivery,
        "coverage_pct": coverage_pct,
        "subjective_judgement": False,
    }
