"""Drift detector — flag material prior→posterior belief shifts."""

from __future__ import annotations

from typing import Any

DRIFT_THRESHOLD = 0.12
MAJOR_DRIFT_THRESHOLD = 0.25


def detect_drift(prior: float, posterior: float) -> dict[str, Any]:
    delta = round(float(posterior) - float(prior), 4)
    abs_delta = abs(delta)
    if abs_delta >= MAJOR_DRIFT_THRESHOLD:
        level = "major"
    elif abs_delta >= DRIFT_THRESHOLD:
        level = "material"
    else:
        level = "stable"
    direction = "up" if delta > 0 else "down" if delta < 0 else "flat"
    return {
        "drift_level": level,
        "direction": direction,
        "delta": delta,
        "abs_delta": abs_delta,
        "threshold_material": DRIFT_THRESHOLD,
        "threshold_major": MAJOR_DRIFT_THRESHOLD,
        "requires_committee_attention": level in ("material", "major"),
        "note": (
            f"Belief drifted {direction} by {abs_delta:.0%}"
            if level != "stable"
            else "Belief remained stable relative to prior"
        ),
    }


def package_drift_summary(beliefs: list[dict[str, Any]]) -> dict[str, Any]:
    material = [b for b in beliefs if (b.get("drift") or {}).get("drift_level") in ("material", "major")]
    return {
        "material_drift_count": len(material),
        "major_drift_count": sum(1 for b in material if (b.get("drift") or {}).get("drift_level") == "major"),
        "requires_committee_attention": len(material) > 0,
        "flagged_hypothesis_ids": [b.get("hypothesis_id") for b in material],
    }
