"""Significance engine — materiality with hysteresis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from institutional_observation.classifier import ClassifiedChange
from institutional_observation.detector import CompanySnapshot
from institutional_observation.hysteresis import (
    DEFAULT_HYSTERESIS,
    HysteresisProfile,
    severity_rank,
    should_emit_observation,
)


@dataclass(frozen=True)
class SignificanceResult:
    materiality: str  # ignore | minor | material | critical
    severity: str
    emit_observation: bool
    recompute_decision: bool
    silent_graph_update: bool
    rationale: str

    def to_dict(self) -> dict:
        return {
            "materiality": self.materiality,
            "severity": self.severity,
            "emit_observation": self.emit_observation,
            "recompute_decision": self.recompute_decision,
            "silent_graph_update": self.silent_graph_update,
            "rationale": self.rationale,
        }


def _valuation_material(before: str, after: str, profile: HysteresisProfile) -> bool:
    # Band changes are always material; numeric % would use threshold — bands map to ~full change
    b, a = str(before or "").title(), str(after or "").title()
    if not b or not a or b == a:
        return False
    # Treat band change as > 2% institutional move
    return profile.valuation_change_pct_min <= 100.0


def assess_significance(
    classified: List[ClassifiedChange],
    *,
    previous: Optional[CompanySnapshot],
    current: CompanySnapshot,
    profile: HysteresisProfile | None = None,
) -> SignificanceResult:
    profile = profile or DEFAULT_HYSTERESIS
    if not classified:
        return SignificanceResult(
            materiality="ignore",
            severity="ignore",
            emit_observation=False,
            recompute_decision=False,
            silent_graph_update=False,
            rationale="No detected changes",
        )

    # Peak severity among classified
    top = max(classified, key=lambda c: (severity_rank(c.severity), c.confidence))
    severity = top.severity

    # Hysteresis: confidence-only micro moves
    only_confidence = all(c.change.key == "confidence" for c in classified)
    if only_confidence and previous is not None:
        delta = abs(int(current.confidence) - int(previous.confidence))
        if delta < profile.confidence_change_min:
            return SignificanceResult(
                materiality="ignore",
                severity="ignore",
                emit_observation=False,
                recompute_decision=False,
                silent_graph_update=True,
                rationale=f"Confidence delta {delta} below hysteresis ({profile.confidence_change_min})",
            )

    # Hysteresis: tiny BQ moves
    bq_only = all(c.change.key == "business_quality" for c in classified)
    if bq_only:
        mag = max(float(c.change.magnitude or 0) for c in classified)
        if mag < profile.business_quality_change_min:
            return SignificanceResult(
                materiality="minor",
                severity="ignore",
                emit_observation=False,
                recompute_decision=False,
                silent_graph_update=True,
                rationale=f"Business quality delta {mag} below hysteresis",
            )

    # Forecast revision below threshold → silent
    forecast_only = all(c.change.kind == "forecast" for c in classified)
    if forecast_only:
        mag = max(float(c.change.magnitude or 0) for c in classified)
        if mag < profile.forecast_revision_min:
            return SignificanceResult(
                materiality="minor",
                severity="ignore",
                emit_observation=False,
                recompute_decision=False,
                silent_graph_update=True,
                rationale=f"Forecast revision {mag} below hysteresis ({profile.forecast_revision_min})",
            )

    # Share split / cosmetic corporate actions — observe medium/low, no recompute
    if top.change.key in {"share_split"} or (
        top.category == "Corporate Actions" and severity_rank(severity) <= severity_rank("low")
    ):
        return SignificanceResult(
            materiality="minor",
            severity=severity if severity_rank(severity) else "low",
            emit_observation=should_emit_observation(severity or "low", profile=profile),
            recompute_decision=False,
            silent_graph_update=not should_emit_observation(severity or "low", profile=profile),
            rationale="Corporate action below decision-recompute threshold",
        )

    # Valuation band change always material for observation; recompute if high+
    if any(c.change.kind == "valuation" for c in classified):
        emit = True
        recompute = severity_rank(severity) >= severity_rank(profile.recompute_min_severity)
        return SignificanceResult(
            materiality="material" if recompute else "minor",
            severity=severity,
            emit_observation=emit,
            recompute_decision=recompute,
            silent_graph_update=False,
            rationale="Valuation band change",
        )

    # Critical / high always emit + recompute
    if severity_rank(severity) >= severity_rank("high"):
        return SignificanceResult(
            materiality="critical" if severity == "critical" else "material",
            severity=severity,
            emit_observation=True,
            recompute_decision=True,
            silent_graph_update=False,
            rationale=f"Severity {severity} exceeds recompute threshold",
        )

    emit = should_emit_observation(severity, profile=profile)
    return SignificanceResult(
        materiality="material" if emit else "minor",
        severity=severity,
        emit_observation=emit,
        recompute_decision=False,
        silent_graph_update=not emit,
        rationale="Below high-severity recompute gate; observation per hysteresis",
    )
