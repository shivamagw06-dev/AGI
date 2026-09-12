"""Assign Low / Medium / High / Critical significance to change events."""

from __future__ import annotations

from typing import Any


_CRITICAL_TYPES = {
    "management_changes",
    "capital_raising",
    "guidance_revisions",
    "rating_revisions",
}
_HIGH_TYPES = {
    "margin_compression",
    "cash_flow_deterioration",
    "debt_increase",
    "revenue_deceleration",
    "roe_deterioration",
}
_MEDIUM_TYPES = {
    "margin_expansion",
    "revenue_acceleration",
    "debt_reduction",
    "cash_flow_improvement",
    "roe_improvement",
    "valuation_expansion",
    "valuation_compression",
    "dividend_changes",
    "buybacks",
}


def score_significance(change: dict[str, Any]) -> str:
    ctype = str(change.get("change_type") or "")
    mag = change.get("magnitude")
    try:
        mag_f = abs(float(mag)) if mag is not None else 0.0
    except Exception:
        mag_f = 0.0

    if ctype in _CRITICAL_TYPES:
        return "Critical"
    if ctype in _HIGH_TYPES:
        if mag_f >= 15:
            return "Critical"
        return "High"
    if ctype in _MEDIUM_TYPES:
        if mag_f >= 20:
            return "High"
        if mag_f >= 8:
            return "Medium"
        return "Low" if mag_f < 3 else "Medium"
    if ctype == "evidence_influx" and mag_f >= 10:
        return "Medium"
    if ctype == "house_view_label_change":
        return "High"
    return "Low"


def annotate(changes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for c in changes:
        row = dict(c)
        row["significance"] = score_significance(row)
        out.append(row)
    return out
