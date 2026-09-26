"""Confidence scoring via FKB modifiers + fusion-specific adjustments."""

from __future__ import annotations

from typing import Any

from evidence_fusion.schema import CONF_HIGH, CONF_LOW, CONF_MEDIUM


def score_fusion_confidence(
    *,
    history_n: int = 0,
    windows_n: int = 0,
    validation_status: str | None = None,
    coverage_pct: float | None = None,
    supporting_sources_n: int = 0,
    conflict: bool = False,
    missing_periods: int = 0,
) -> dict[str, Any]:
    """Return High/Medium/Low using FKB apply_points when available."""
    points = 0
    applied: list[str] = []
    band_downgrade = 0

    try:
        from financial_knowledge.confidence import apply_points

        mod = apply_points(
            history_n=history_n,
            windows_n=windows_n,
            validation_status=validation_status,
            coverage_pct=coverage_pct,
            missing_periods=missing_periods,
            conflict=conflict,
        )
        points = int(mod.get("points") or 0)
        applied = list(mod.get("applied") or [])
        band_downgrade = int(mod.get("band_downgrade") or 0)
    except Exception:  # noqa: BLE001
        if coverage_pct is not None:
            if coverage_pct >= 80:
                points += 1
            elif coverage_pct < 40:
                points -= 1
        if history_n >= 4:
            points += 1
        if conflict:
            points -= 1
            band_downgrade = 1

    # Number of supporting sources (FIRE-01 / FIRE-02 / metrics)
    if supporting_sources_n >= 3:
        points += 2
        applied.append("supporting_sources_rich")
    elif supporting_sources_n >= 2:
        points += 1
        applied.append("supporting_sources_moderate")
    elif supporting_sources_n == 0 and not conflict:
        points -= 1
        applied.append("supporting_sources_none")

    bands = [CONF_LOW, CONF_MEDIUM, CONF_HIGH]
    if points >= 5:
        idx = 2
    elif points >= 2:
        idx = 1
    else:
        idx = 0
    idx = max(0, idx - band_downgrade)
    return {
        "confidence": bands[idx],
        "points": points,
        "applied_modifiers": applied,
        "band_downgrade": band_downgrade,
    }


def confidence_distribution(findings: list[dict[str, Any]]) -> dict[str, int]:
    dist = {CONF_HIGH: 0, CONF_MEDIUM: 0, CONF_LOW: 0}
    for f in findings:
        c = f.get("confidence") or CONF_LOW
        dist[c] = dist.get(c, 0) + 1
    return dist
