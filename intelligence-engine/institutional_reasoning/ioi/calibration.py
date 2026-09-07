"""Module 5 — Confidence Calibration.

Dual confidence: IES (implementation) vs Live Outcome (reality).
Reports trends only — does NOT update framework behaviour (no learning).
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.ioi.schema import ies_confidence

CALIBRATION_VERSION = "confidence-calibration-v1.0.0"

# Rolling live accuracy store (memory only — not a learning update to engines).
_LIVE: dict[str, list[float]] = {}


def reset_calibration() -> None:
    _LIVE.clear()


def _trend(series: list[float]) -> str:
    if len(series) < 2:
        return "→"
    a, b = series[-2], series[-1]
    if b - a >= 0.03:
        return "↗"
    if a - b >= 0.03:
        return "↘"
    return "→"


def record_live_accuracy(framework_id: str, correct: bool) -> None:
    series = _LIVE.setdefault(framework_id, [])
    series.append(1.0 if correct else 0.0)
    if len(series) > 50:
        del series[:-50]


def calibrate_frameworks(attribution: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for c in attribution.get("components") or []:
        fid = str(c.get("component") or "")
        kind = str(c.get("kind") or "")
        # Map kinds to calibration ids
        cal_id = fid if fid in {
            "rel_val_damodaran",
            "hist_multiples",
            "margin_of_safety",
            "dcf_applicability",
            "business_quality_roic",
            "accounting_quality_screen",
            "peer_comparison",
        } else kind
        if cal_id in seen or cal_id in {"evidence", "assumption", "other", "method"}:
            if cal_id == "method":
                cal_id = "dcf_applicability"
            elif cal_id in {"evidence", "assumption", "other"}:
                continue
        if cal_id in seen:
            continue
        seen.add(cal_id)
        ok = c.get("verdict") == "Correct"
        record_live_accuracy(cal_id, ok)
        series = _LIVE.get(cal_id) or []
        live = sum(series) / len(series) if series else (1.0 if ok else 0.0)
        ies = ies_confidence(cal_id if cal_id != "business_quality" else "business_quality_roic")
        if cal_id == "business_quality":
            ies = ies_confidence("business_quality_roic")
        rows.append(
            {
                "framework": cal_id,
                "label": c.get("label") or cal_id,
                "ies_confidence": round(ies, 4),
                "live_outcome_confidence": round(live, 4),
                "trend": _trend(series),
                "samples": len(series),
                "last_verdict": c.get("verdict"),
            }
        )

    return {
        "calibration_version": CALIBRATION_VERSION,
        "note": "Reports only — does not update framework behaviour (no learning).",
        "frameworks": rows,
    }


def calibration_snapshot() -> dict[str, Any]:
    out = []
    for fid, series in sorted(_LIVE.items()):
        live = sum(series) / len(series) if series else None
        out.append(
            {
                "framework": fid,
                "ies_confidence": ies_confidence(fid),
                "live_outcome_confidence": round(live, 4) if live is not None else None,
                "trend": _trend(series),
                "samples": len(series),
            }
        )
    return {"calibration_version": CALIBRATION_VERSION, "frameworks": out}
