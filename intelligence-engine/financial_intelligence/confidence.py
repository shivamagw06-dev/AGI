"""Confidence scoring from coverage, validation, and history depth."""

from __future__ import annotations

from typing import Any

from financial_intelligence.schema import CONF_HIGH, CONF_LOW, CONF_MEDIUM


def score_confidence(
    *,
    history_n: int,
    windows_n: int,
    validation_status: str | None = None,
    quality_score: float | None = None,
    coverage_pct: float | None = None,
) -> str:
    """Deterministic High / Medium / Low."""
    points = 0
    if history_n >= 8:
        points += 2
    elif history_n >= 4:
        points += 1
    if windows_n >= 3:
        points += 2
    elif windows_n >= 1:
        points += 1
    status = (validation_status or "").upper()
    if status in {"APPROVED", "APPROVED_WITH_WARNINGS", "PUBLISHABLE"}:
        points += 2 if status == "APPROVED" else 1
    if isinstance(quality_score, (int, float)):
        if quality_score >= 0.8:
            points += 1
        elif quality_score < 0.5:
            points -= 1
    if isinstance(coverage_pct, (int, float)):
        if coverage_pct >= 80:
            points += 1
        elif coverage_pct < 40:
            points -= 1
    if points >= 5:
        return CONF_HIGH
    if points >= 3:
        return CONF_MEDIUM
    return CONF_LOW


def confidence_distribution(findings: list[dict[str, Any]]) -> dict[str, int]:
    dist = {CONF_HIGH: 0, CONF_MEDIUM: 0, CONF_LOW: 0}
    for f in findings:
        c = f.get("confidence") or CONF_LOW
        if c not in dist:
            dist[c] = 0
        dist[c] += 1
    return dist
