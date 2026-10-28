"""Explain confidence bands from evidence completeness — never unexplained."""

from __future__ import annotations

from typing import Any

from institutional_communication.styles.institutional import bullet


def render_confidence_section(institutional_answer: dict[str, Any]) -> dict[str, Any]:
    conf = institutional_answer.get("confidence") or {}
    gaps = institutional_answer.get("gaps") or {}
    fw_conf = ((institutional_answer.get("frameworks") or {}).get("confidence") or {})

    band = conf.get("band") or fw_conf.get("band") or "Insufficient"
    score = conf.get("score") if conf.get("score") is not None else fw_conf.get("score")
    pct = conf.get("pct") if conf.get("pct") is not None else fw_conf.get("pct")
    coverage = conf.get("coverage") if conf.get("coverage") is not None else gaps.get("coverage")

    lines = [
        bullet(f"Confidence band: {band}" + (f" ({pct}%)" if pct is not None else "")),
    ]
    if score is not None:
        lines.append(bullet(f"Calibrated score: {score}"))
    if coverage is not None:
        lines.append(bullet(f"Evidence coverage used in calibration: {coverage}"))
    missing = conf.get("missing_domains") or gaps.get("missing_domains") or []
    if missing:
        lines.append(bullet(f"Coverage gaps reducing confidence: {', '.join(map(str, missing))}"))
    else:
        lines.append(bullet("No hard domain gaps after softening rules — confidence not inflated beyond coverage."))

    # Plain-language band meaning
    meaning = {
        "High": "Evidence domains required for this intent are largely present.",
        "Moderate": "Core evidence present with material gaps or softened requirements.",
        "Low": "Evidence incomplete; treat conclusions as provisional.",
        "Insufficient": "Evidence too thin for institutional confidence.",
    }.get(str(band), "Band derived from deterministic completeness rules.")
    lines.append(bullet(f"Interpretation: {meaning}"))

    return {
        "section": "confidence",
        "title": "Confidence",
        "bullets": lines,
        "band": band,
        "visible": True,
    }
