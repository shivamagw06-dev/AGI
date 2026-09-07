"""Configurable CalibrationProfile — weights recorded on every decision for reproducibility."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from institutional_calibration.schema import CALIBRATION_PROFILE_VERSION


@dataclass(frozen=True)
class CalibrationProfile:
    """Tunable weights — engine architecture stays fixed; profile version is stored."""

    evidence_quality_weight: float = 0.25
    reasoning_strength_weight: float = 0.20
    valuation_certainty_weight: float = 0.15
    forecast_stability_weight: float = 0.15
    macro_stability_weight: float = 0.10
    unknown_penalty_weight: float = 0.10
    contradiction_penalty_weight: float = 0.05
    # Secondary / scorecard-only inputs (normalized into bonuses)
    evidence_freshness_weight: float = 0.0  # folded into evidence_quality by default
    evidence_coverage_weight: float = 0.0
    rule_consistency_weight: float = 0.0
    profile_version: str = CALIBRATION_PROFILE_VERSION
    profile_id: str = "default"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def weight_sum(self) -> float:
        return (
            self.evidence_quality_weight
            + self.reasoning_strength_weight
            + self.valuation_certainty_weight
            + self.forecast_stability_weight
            + self.macro_stability_weight
            + self.unknown_penalty_weight
            + self.contradiction_penalty_weight
        )


DEFAULT_PROFILE = CalibrationProfile()
