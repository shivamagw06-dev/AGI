"""Historical validation — reject missing/duplicate/future-leaking records."""

from __future__ import annotations

from typing import Any


def validate_pit_record(record: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    if not record.get("period"):
        reasons.append("missing_period")
    if not record.get("available_from"):
        reasons.append("missing_available_from")
    if not record.get("period_end"):
        reasons.append("missing_period_end")
    # available_from must not precede period_end by more than absurd margin,
    # and must not be empty. Look-ahead: available_from < period_end is OK
    # only for forecasts — for results, available_from >= period_end.
    pe = str(record.get("period_end") or "")
    af = str(record.get("available_from") or "")
    kind = str(record.get("kind") or "")
    if pe and af and kind.startswith("financials") and af < pe:
        reasons.append("available_from_before_period_end")
    if not record.get("payload"):
        reasons.append("missing_payload")
    return {
        "ok": not reasons,
        "rejected": bool(reasons),
        "reasons": reasons,
        "entity": record.get("entity"),
        "period": record.get("period"),
    }


def validate_series(series: dict[str, Any] | None) -> dict[str, Any]:
    if not series:
        return {"ok": False, "rejected": True, "reasons": ["missing_series"], "failures": []}
    failures = []
    seen = set()
    for r in series.get("records") or []:
        v = validate_pit_record(r)
        if not v["ok"]:
            failures.append(v)
        key = (r.get("period"), r.get("available_from"))
        if key in seen:
            failures.append({"ok": False, "reasons": ["duplicate_period"], "period": r.get("period")})
        seen.add(key)
    return {
        "ok": len(failures) == 0,
        "rejected": len(failures) > 0,
        "entity": series.get("entity"),
        "n": len(series.get("records") or []),
        "failures": failures,
    }


def assert_no_future_leak(records: list[dict[str, Any]], as_of: str) -> dict[str, Any]:
    """Hard PIT guarantee check — any record with available_from > as_of is a leak."""
    leaks = [r for r in records if str(r.get("available_from") or "") > as_of]
    return {
        "ok": len(leaks) == 0,
        "as_of": as_of,
        "leaks": [
            {"period": r.get("period"), "available_from": r.get("available_from"), "kind": r.get("kind")}
            for r in leaks
        ],
        "n_checked": len(records),
    }
