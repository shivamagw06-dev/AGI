"""Intelligence delta — previous vs current for every analyst / overall IQ."""

from __future__ import annotations

from typing import Any

ANALYST_KEYS = [
    "business",
    "financial",
    "valuation",
    "risk",
    "sector",
    "macro",
    "management",
    "ownership",
    "committee",
    "cio",
    "research_writer",
    "portfolio",
]


def compute_delta(previous: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    prev_scores = (previous or {}).get("reasoning_scores") or (previous or {}).get("snapshot", {}).get("reasoning_scores") or {}
    curr_scores = current.get("reasoning_scores") or {}
    prev_iq = float(
        (previous or {}).get("overall_institutional_iq")
        or (previous or {}).get("snapshot", {}).get("overall_institutional_iq")
        or 0.0
    )
    curr_iq = float(current.get("overall_institutional_iq") or 0.0)

    analysts = {}
    for key in ANALYST_KEYS:
        # map ownership from management/risk blend if absent
        p = float(prev_scores.get(key) or prev_scores.get("management" if key == "ownership" else key) or prev_iq or 0.0)
        if key == "ownership" and key not in curr_scores:
            c = float(curr_scores.get("management") or curr_iq)
        else:
            c = float(curr_scores.get(key) or 0.0)
        if key not in curr_scores and key == "ownership":
            c = float(curr_scores.get("management") or curr_iq)
        delta = round(c - p, 2)
        analysts[key] = {
            "previous": round(p, 2),
            "current": round(c, 2),
            "delta": delta,
            "arrow": "↑" if delta > 0.05 else ("↓" if delta < -0.05 else "="),
        }

    iq_delta = round(curr_iq - prev_iq, 2)
    return {
        "overall_institutional_iq": {
            "previous": round(prev_iq, 2),
            "current": round(curr_iq, 2),
            "delta": iq_delta,
            "arrow": "↑" if iq_delta > 0.05 else ("↓" if iq_delta < -0.05 else "="),
        },
        "analysts": analysts,
        "hallucinations": {
            "previous_critical": int(((previous or {}).get("hallucinations") or {}).get("critical") or 0),
            "current_critical": int((current.get("hallucinations") or {}).get("critical_count") or 0),
            "previous_high": int(((previous or {}).get("hallucinations") or {}).get("high") or 0),
            "current_high": int((current.get("hallucinations") or {}).get("high_count") or 0),
        },
        "analyst_drift": {
            "previous": int((previous or {}).get("analyst_drift_total") or 0),
            "current": int((current.get("analyst_drift") or {}).get("total") or 0),
        },
    }
