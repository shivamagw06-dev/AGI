"""Human review queue — only a small subset needs manual attention."""

from __future__ import annotations

from typing import Any

from institutional_evaluation_lab.drift.schema import DRIFT_BUDGET


def build_review_queue(
    rows: list[dict[str, Any]],
    *,
    budget_passed: bool,
    budget_breaches: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    val_swing = float(DRIFT_BUDGET["large_valuation_swing"])

    for r in rows:
        reasons: list[str] = []
        code = str((r.get("reason") or {}).get("code") or r.get("reason_code") or "")
        if code == "UNKNOWN":
            reasons.append("Unknown drift")
        if code == "GOVERNANCE":
            reasons.append("Governance changes")
        mag = r.get("magnitude") or {}
        val = (mag.get("by_field") or {}).get("valuation") or {}
        if val.get("delta") is not None and abs(float(val["delta"])) >= val_swing:
            reasons.append("Large valuation swing")
        if r.get("requires_review_extra"):
            reasons.append(str(r.get("requires_review_extra")))
        if reasons:
            items.append(
                {
                    "ticker": r.get("ticker"),
                    "previous": r.get("previous_decision"),
                    "current": r.get("current_decision"),
                    "reason_code": code,
                    "reasons": reasons,
                    "detail": (r.get("reason") or {}).get("detail"),
                }
            )

    # Budget breach always surfaces a synthetic review item
    if not budget_passed:
        items.insert(
            0,
            {
                "ticker": "*",
                "previous": None,
                "current": None,
                "reason_code": "BUDGET",
                "reasons": ["Drift budget breached"],
                "detail": ", ".join(
                    f"{b.get('metric')}={b.get('value')}" for b in (budget_breaches or [])
                ),
            },
        )

    by_reason: dict[str, int] = {}
    for it in items:
        for reason in it.get("reasons") or []:
            by_reason[reason] = by_reason.get(reason, 0) + 1

    return {
        "requires_review": len(items),
        "by_reason": by_reason,
        "items": items,
        "note": "Only UNKNOWN, GOVERNANCE, large valuation swings, and budget breaches enter the queue.",
    }
