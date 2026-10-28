"""IDS-02 calibration models — confidence decomposition & explainability."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class ConfidenceContributor:
    """One positive or negative contributor to calibrated confidence."""

    key: str
    label: str
    direction: str  # positive | negative | unknown | bonus | penalty
    points: float
    detail: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Calibration:
    """
    Computed confidence decomposition.

    final_confidence is ALWAYS derived — never manually assigned.
    """

    final_confidence: int
    evidence_quality: int
    evidence_freshness: int
    evidence_coverage: int
    reasoning_strength: int
    rule_consistency: int
    valuation_certainty: int
    forecast_stability: int
    macro_stability: int
    unknown_penalty: int
    contradiction_penalty: int
    profile_version: str
    positive_contributors: List[ConfidenceContributor] = field(default_factory=list)
    negative_contributors: List[ConfidenceContributor] = field(default_factory=list)
    unknowns: List[str] = field(default_factory=list)
    bonuses: List[ConfidenceContributor] = field(default_factory=list)
    penalties: List[ConfidenceContributor] = field(default_factory=list)
    weighted_components: Dict[str, float] = field(default_factory=dict)
    formula_trace: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "final_confidence": self.final_confidence,
            "evidence_quality": self.evidence_quality,
            "evidence_freshness": self.evidence_freshness,
            "evidence_coverage": self.evidence_coverage,
            "reasoning_strength": self.reasoning_strength,
            "rule_consistency": self.rule_consistency,
            "valuation_certainty": self.valuation_certainty,
            "forecast_stability": self.forecast_stability,
            "macro_stability": self.macro_stability,
            "unknown_penalty": self.unknown_penalty,
            "contradiction_penalty": self.contradiction_penalty,
            "profile_version": self.profile_version,
            "positive_contributors": [c.to_dict() for c in self.positive_contributors],
            "negative_contributors": [c.to_dict() for c in self.negative_contributors],
            "unknowns": list(self.unknowns),
            "bonuses": [c.to_dict() for c in self.bonuses],
            "penalties": [c.to_dict() for c in self.penalties],
            "weighted_components": dict(self.weighted_components),
            "formula_trace": list(self.formula_trace),
        }


@dataclass(frozen=True)
class ScorecardLine:
    dimension: str
    points: int
    note: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DecisionScorecard:
    """Decision scorecard — dimensional contribution to the call."""

    lines: List[ScorecardLine]
    recommendation: str
    confidence: int
    total_points: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lines": [line.to_dict() for line in self.lines],
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "total_points": self.total_points,
        }


@dataclass(frozen=True)
class DecisionExplainability:
    """Complete explainability surface for a recommendation."""

    why_buy: List[str]
    why_hold: List[str]
    why_sell: List[str]
    why_not_buy: List[str]
    why_not_sell: List[str]
    what_reduced_confidence: List[str]
    what_increased_confidence: List[str]
    what_would_change: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DecisionDrift:
    """Previous → current decision drift."""

    has_previous: bool
    previous_recommendation: Optional[str]
    current_recommendation: Optional[str]
    recommendation_changed: bool
    previous_confidence: Optional[int]
    current_confidence: Optional[int]
    confidence_delta: Optional[int]
    reason_changes: List[str]
    evidence_changes: List[str]
    explanation_chain: List[str]
    previous_decision_id: Optional[str] = None
    current_decision_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DecisionLineage:
    """Full Evidence → Reasons → Decision → Calibration → Report lineage."""

    evidence_snapshot_id: str
    reason_ids: List[str]
    reason_version: str
    decision_id: str
    decision_version: str
    calibration_version: str
    profile_version: str
    report_version: str
    chain: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CalibrationBundle:
    """Full IDS-02 output attached to a calibrated decision."""

    calibration: Calibration
    scorecard: DecisionScorecard
    explainability: DecisionExplainability
    drift: DecisionDrift
    lineage: DecisionLineage
    diagnostics: Dict[str, Any]
    quality_gates: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "calibration": self.calibration.to_dict(),
            "scorecard": self.scorecard.to_dict(),
            "explainability": self.explainability.to_dict(),
            "drift": self.drift.to_dict(),
            "lineage": self.lineage.to_dict(),
            "diagnostics": dict(self.diagnostics),
            "quality_gates": dict(self.quality_gates),
        }
