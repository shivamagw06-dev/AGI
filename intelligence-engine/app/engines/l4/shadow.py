"""L4-005 Shadow Validation — compare L4Opinion vs production E03 (never mutates E03)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.engines.e03.alpha import E03Alpha
from app.engines.l4.mapping import ENGINE_VERSION, MODEL_VERSION
from app.engines.l4.opinion import L4Opinion


class ShadowComparison(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    as_of: str
    legacy_label: str
    legacy_confidence: float
    l4_label: str
    l4_confidence: float
    agreement: bool
    disagreement_reason: str | None = None
    dominant_driver: str | None = None
    evidence_summary: str
    timestamp: str
    engine_version: str = ENGINE_VERSION
    model_version: str = MODEL_VERSION
    shadow: bool = True


def build_shadow_comparison(
    opinion: L4Opinion,
    e03: E03Alpha | None,
    *,
    generated_at: datetime | None = None,
) -> ShadowComparison:
    ts = generated_at or datetime.now(timezone.utc)
    legacy_label = e03.label if e03 is not None else "Unknown"
    legacy_conf = float(e03.confidence) if e03 is not None else 0.0
    agree = opinion.label == legacy_label
    reason = None
    if not agree:
        reasons = []
        if opinion.conflict_resolution not in {"none", ""}:
            reasons.append(f"conflict:{opinion.conflict_resolution}")
        if opinion.confidence_mult < 0.9:
            reasons.append(f"confidence_mult={opinion.confidence_mult:.2f}")
        if opinion.conflict_resolution in {"prefer_neutral", "block", "override", "haircut"}:
            reasons.append("hierarchy_prefer_neutral")
        drivers = ",".join(d.get("engine", "?") for d in opinion.dominant_drivers[:2])
        reasons.append(f"drivers={drivers}")
        reason = "; ".join(reasons) if reasons else "label_divergence"

    dominant = None
    if opinion.dominant_drivers:
        dominant = str(opinion.dominant_drivers[0].get("engine"))

    pos_n = len(opinion.positive_evidence)
    neg_n = len(opinion.negative_evidence)
    con_n = len(opinion.contradictions)
    summary = f"+{pos_n}/-{neg_n}/contradictions={con_n}"

    return ShadowComparison(
        symbol=opinion.symbol,
        as_of=opinion.as_of,
        legacy_label=legacy_label,
        legacy_confidence=legacy_conf,
        l4_label=opinion.label,
        l4_confidence=opinion.confidence,
        agreement=agree,
        disagreement_reason=reason,
        dominant_driver=dominant,
        evidence_summary=summary,
        timestamp=ts.isoformat(),
    )
