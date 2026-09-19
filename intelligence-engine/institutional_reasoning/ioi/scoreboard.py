"""Module 7 — Framework Scoreboard.

Live accuracy, recent accuracy, failure modes, confidence trend.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.ioi.calibration import calibration_snapshot
from institutional_reasoning.ioi.schema import ies_confidence

SCOREBOARD_VERSION = "framework-scoreboard-v1.0.0"

_FAILURE_MODES: dict[str, list[str]] = {}


def reset_scoreboard() -> None:
    _FAILURE_MODES.clear()


def note_failure_mode(framework_id: str, mode: str) -> None:
    modes = _FAILURE_MODES.setdefault(framework_id, [])
    if mode and mode not in modes:
        modes.append(mode)
    if len(modes) > 12:
        del modes[:-12]


def build_scoreboard(calibration: dict[str, Any] | None = None) -> dict[str, Any]:
    cal = calibration or calibration_snapshot()
    rows = []
    for fw in cal.get("frameworks") or []:
        fid = str(fw.get("framework") or "")
        live = fw.get("live_outcome_confidence")
        rows.append(
            {
                "framework": fid,
                "label": fw.get("label") or fid,
                "ies": round(float(fw.get("ies_confidence") or ies_confidence(fid)) * 100, 1),
                "live": round(float(live) * 100, 1) if live is not None else None,
                "recent": round(float(live) * 100, 1) if live is not None else None,
                "trend": fw.get("trend") or "→",
                "failure_modes": list(_FAILURE_MODES.get(fid) or []),
                "samples": fw.get("samples") or 0,
            }
        )
    # Ensure core frameworks appear even without samples
    present = {r["framework"] for r in rows}
    for fid in ("rel_val_damodaran", "dcf_applicability", "business_quality_roic", "macro", "scenario", "policy"):
        if fid not in present:
            rows.append(
                {
                    "framework": fid,
                    "label": fid,
                    "ies": round(ies_confidence(fid) * 100, 1),
                    "live": None,
                    "recent": None,
                    "trend": "→",
                    "failure_modes": list(_FAILURE_MODES.get(fid) or []),
                    "samples": 0,
                }
            )
    return {
        "scoreboard_version": SCOREBOARD_VERSION,
        "frameworks": rows,
        "note": "Scoreboard is observational — Phase 7 may consume it for learning.",
    }
