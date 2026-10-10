"""Confidence calibration — never invent arbitrary defaults."""

from __future__ import annotations

from typing import Any, Optional


def calibrate(
    *,
    overall: Optional[float] = None,
    section_confidence: Optional[dict[str, Any]] = None,
    evidence_count: int = 0,
    warehouse_freshness: Optional[str] = None,
    missing_data: Optional[list[str]] = None,
    entity_confidence: Optional[float] = None,
    providers_used: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Build an explicit confidence contract for Ask answers."""
    missing = list(missing_data or [])
    by_section = {}
    if isinstance(section_confidence, dict):
        for k, v in section_confidence.items():
            if isinstance(v, (int, float)):
                by_section[str(k)] = round(float(v), 1)
            elif isinstance(v, dict) and isinstance(v.get("confidence"), (int, float)):
                by_section[str(k)] = round(float(v["confidence"]), 1)

    pieces: list[tuple[float, float]] = []
    if isinstance(overall, (int, float)):
        o = float(overall)
        pieces.append((o / 100.0 if o > 1 else o, 2.0))
    if isinstance(entity_confidence, (int, float)):
        e = float(entity_confidence)
        pieces.append((e / 100.0 if e > 1 else e, 1.5))
    if evidence_count > 0:
        pieces.append((min(1.0, evidence_count / 6.0), 1.0))
    if by_section:
        avg_sec = sum(by_section.values()) / len(by_section)
        pieces.append((avg_sec / 100.0 if avg_sec > 1 else avg_sec, 1.0))

    if not pieces:
        calibrated = None
        level = "Unknown"
        note = "Confidence unavailable — no engine or entity scores were supplied."
    else:
        tw = sum(w for _, w in pieces) or 1.0
        calibrated = round(100.0 * sum(c * w for c, w in pieces) / tw, 1)
        # Penalise missing institutional sections.
        if missing:
            calibrated = round(max(0.0, calibrated - min(25.0, 4.0 * len(missing))), 1)
        level = "High" if calibrated >= 75 else "Medium" if calibrated >= 55 else "Low"
        note = "Calibrated from engine, entity, evidence, and section scores."

    return {
        "overall_confidence": calibrated,
        "level": level,
        "section_confidence": by_section,
        "evidence_count": int(evidence_count or 0),
        "warehouse_freshness": warehouse_freshness,
        "missing_data": missing,
        "providers_used": list(providers_used or []),
        "entity_confidence": entity_confidence,
        "note": note,
    }
