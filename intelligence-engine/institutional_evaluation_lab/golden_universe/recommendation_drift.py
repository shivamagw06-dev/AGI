"""Recommendation drift — compare current run vs previous release baseline."""

from __future__ import annotations

from typing import Any


def _classify_change(
    *,
    prev: dict[str, Any],
    cur: dict[str, Any],
    decision_changed: bool,
) -> tuple[str, str]:
    """Return (class, reason)."""
    if not decision_changed:
        return "no_change", "No change"

    prev_ready = prev.get("recommendation_readiness")
    cur_ready = cur.get("recommendation_readiness")
    prev_ev = prev.get("evidence_class")
    cur_ev = cur.get("evidence_class")
    prev_gate = prev.get("gate")
    cur_gate = cur.get("gate")

    # Evidence / readiness moved meaningfully → expected new evidence
    try:
        if prev_ready is not None and cur_ready is not None:
            if abs(float(cur_ready) - float(prev_ready)) >= 5:
                return "expected_new_evidence", "Updated readiness / evidence profile"
    except (TypeError, ValueError):
        pass
    if prev_ev and cur_ev and prev_ev != cur_ev:
        return "expected_new_evidence", f"Evidence class {prev_ev} → {cur_ev}"
    if prev_gate != cur_gate:
        return "expected_new_evidence", f"Gate {prev_gate} → {cur_gate}"

    # Same evidence class + similar readiness but decision flipped → unexpected
    try:
        ready_delta = abs(float(cur_ready or 0) - float(prev_ready or 0))
    except (TypeError, ValueError):
        ready_delta = 0
    if prev_ev == cur_ev and ready_delta < 3:
        return "unexpected_possible_regression", "Decision changed without material evidence shift"

    return "expected_algorithm_improvement", "Decision shift with modest evidence change"


def compare_recommendation_drift(
    current_rows: list[dict[str, Any]],
    previous_rows: list[dict[str, Any]] | None,
    *,
    previous_label: str = "previous",
    current_label: str = "current",
) -> dict[str, Any]:
    prev_by = {
        str(r.get("ticker") or "").upper(): r
        for r in (previous_rows or [])
        if isinstance(r, dict) and r.get("ticker")
    }
    table: list[dict[str, Any]] = []
    by_class: dict[str, int] = {
        "no_change": 0,
        "expected_new_evidence": 0,
        "expected_algorithm_improvement": 0,
        "unexpected_possible_regression": 0,
    }

    for cur in current_rows:
        t = str(cur.get("ticker") or "").upper()
        prev = prev_by.get(t)
        if not prev:
            table.append(
                {
                    "ticker": t,
                    previous_label: None,
                    current_label: cur.get("decision"),
                    "reason": "New to benchmark / no prior baseline",
                    "class": "expected_new_evidence",
                }
            )
            by_class["expected_new_evidence"] = by_class.get("expected_new_evidence", 0) + 1
            continue
        changed = str(prev.get("decision") or "") != str(cur.get("decision") or "")
        klass, reason = _classify_change(prev=prev, cur=cur, decision_changed=changed)
        by_class[klass] = by_class.get(klass, 0) + 1
        table.append(
            {
                "ticker": t,
                previous_label: prev.get("decision"),
                current_label: cur.get("decision"),
                "previous_readiness": prev.get("recommendation_readiness"),
                "current_readiness": cur.get("recommendation_readiness"),
                "reason": reason,
                "class": klass,
                "changed": changed,
            }
        )

    unexpected = [r for r in table if r.get("class") == "unexpected_possible_regression"]
    return {
        "previous_label": previous_label,
        "current_label": current_label,
        "n": len(table),
        "changed": sum(1 for r in table if r.get("changed")),
        "by_class": by_class,
        "unexpected_count": len(unexpected),
        "unexpected": unexpected[:40],
        "rows": table,
        "note": (
            "Unexpected drift = decision changed without material evidence/readiness shift — investigate."
        ),
    }
