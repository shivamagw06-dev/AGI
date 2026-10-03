"""Confidence computation — always derived from CalibrationProfile + component scores."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from institutional_calibration.models import Calibration, ConfidenceContributor
from institutional_calibration.profile import CalibrationProfile, DEFAULT_PROFILE
from institutional_calibration.schema import clamp_int


def _evidence_composite(components: Dict[str, int], profile: CalibrationProfile) -> Tuple[float, Dict[str, float]]:
    """Blend quality / freshness / coverage using profile secondary weights when set."""
    eq = float(components["evidence_quality"])
    fresh = float(components["evidence_freshness"])
    cov = float(components["evidence_coverage"])
    fw = float(profile.evidence_freshness_weight or 0.0)
    cw = float(profile.evidence_coverage_weight or 0.0)
    if fw <= 0 and cw <= 0:
        blended = 0.50 * eq + 0.25 * fresh + 0.25 * cov
        return blended, {"evidence_quality": 0.50, "evidence_freshness": 0.25, "evidence_coverage": 0.25}
    qw = max(0.0, 1.0 - fw - cw)
    total = qw + fw + cw
    if total <= 0:
        return eq, {"evidence_quality": 1.0}
    blended = (qw * eq + fw * fresh + cw * cov) / total
    return blended, {
        "evidence_quality": qw / total,
        "evidence_freshness": fw / total,
        "evidence_coverage": cw / total,
    }


def _penalty_health(penalty_points: int) -> float:
    """Map display penalty (e.g. -9) to a 0–100 health score for weighted averaging."""
    return float(clamp_int(100 + int(penalty_points)))


def compute_calibration(
    components: Dict[str, int],
    *,
    profile: CalibrationProfile | None = None,
) -> Calibration:
    """Compute Calibration — final_confidence is never manually assigned.

    Profile weights are expected to sum to ~1.0 across:
    evidence / reasoning / valuation / forecast / macro / unknown / contradiction.
    Penalties participate as health scores (100 + penalty_points), not hard subtractions.
    """
    profile = profile or DEFAULT_PROFILE
    evidence_composite, evidence_mix = _evidence_composite(components, profile)

    unk = int(components["unknown_penalty"])
    contra = int(components["contradiction_penalty"])
    unk_health = _penalty_health(unk)
    contra_health = _penalty_health(contra)

    weights = {
        "evidence_quality": float(profile.evidence_quality_weight),
        "reasoning_strength": float(profile.reasoning_strength_weight),
        "valuation_certainty": float(profile.valuation_certainty_weight),
        "forecast_stability": float(profile.forecast_stability_weight),
        "macro_stability": float(profile.macro_stability_weight),
        "unknown_penalty": float(profile.unknown_penalty_weight),
        "contradiction_penalty": float(profile.contradiction_penalty_weight),
    }
    rule_w = float(profile.rule_consistency_weight or 0.0)
    if rule_w > 0:
        weights["rule_consistency"] = rule_w

    weight_sum = sum(weights.values()) or 1.0
    values = {
        "evidence_quality": evidence_composite,
        "reasoning_strength": float(components["reasoning_strength"]),
        "valuation_certainty": float(components["valuation_certainty"]),
        "forecast_stability": float(components["forecast_stability"]),
        "macro_stability": float(components["macro_stability"]),
        "unknown_penalty": unk_health,
        "contradiction_penalty": contra_health,
        "rule_consistency": float(components["rule_consistency"]),
    }

    weighted_components: Dict[str, float] = {}
    blended = 0.0
    formula_trace: List[str] = [
        f"profile_version={profile.profile_version}",
        f"evidence_composite={evidence_composite:.2f} mix={evidence_mix}",
        f"unknown_health={unk_health:.1f} (from penalty {unk})",
        f"contradiction_health={contra_health:.1f} (from penalty {contra})",
    ]
    for key, weight in weights.items():
        share = weight / weight_sum
        contrib = values[key] * share
        weighted_components[key] = round(contrib, 4)
        blended += contrib
        formula_trace.append(f"{key}={values[key]:.2f} * {share:.4f} → {contrib:.2f}")

    bonuses: List[ConfidenceContributor] = []
    bonus_pts = 0.0
    if components["rule_consistency"] >= 100 and rule_w <= 0:
        bonus_pts = 1.0
        bonuses.append(
            ConfidenceContributor(
                key="rule_consistency_bonus",
                label="Consistent valuation / rule path",
                direction="bonus",
                points=bonus_pts,
                detail="Decision rule_path and graph are complete",
            )
        )
        formula_trace.append("bonus_rule_consistency=+1")

    final_i = clamp_int(blended + bonus_pts)
    formula_trace.append(f"final_confidence={final_i}")

    positives, negatives, penalties, unknowns = build_contributors(components, final_i)

    return Calibration(
        final_confidence=final_i,
        evidence_quality=int(components["evidence_quality"]),
        evidence_freshness=int(components["evidence_freshness"]),
        evidence_coverage=int(components["evidence_coverage"]),
        reasoning_strength=int(components["reasoning_strength"]),
        rule_consistency=int(components["rule_consistency"]),
        valuation_certainty=int(components["valuation_certainty"]),
        forecast_stability=int(components["forecast_stability"]),
        macro_stability=int(components["macro_stability"]),
        unknown_penalty=unk,
        contradiction_penalty=contra,
        profile_version=profile.profile_version,
        positive_contributors=positives,
        negative_contributors=negatives,
        unknowns=unknowns,
        bonuses=bonuses,
        penalties=penalties,
        weighted_components=weighted_components,
        formula_trace=formula_trace,
    )


def build_contributors(
    components: Dict[str, int],
    final_confidence: int,
) -> Tuple[List[ConfidenceContributor], List[ConfidenceContributor], List[ConfidenceContributor], List[str]]:
    positives: List[ConfidenceContributor] = []
    negatives: List[ConfidenceContributor] = []
    penalties: List[ConfidenceContributor] = []
    unknowns: List[str] = []

    def add_pos(key: str, label: str, threshold: int = 75) -> None:
        val = int(components[key])
        if val >= threshold:
            positives.append(
                ConfidenceContributor(
                    key=key,
                    label=label,
                    direction="positive",
                    points=float(val),
                    detail=f"{key}={val}",
                )
            )
        elif val < 60:
            negatives.append(
                ConfidenceContributor(
                    key=key,
                    label=f"Limited {label.lower()}",
                    direction="negative",
                    points=float(val - 60),
                    detail=f"{key}={val}",
                )
            )

    add_pos("evidence_coverage", "Strong evidence coverage", 80)
    add_pos("evidence_quality", "High evidence quality", 80)
    add_pos("evidence_freshness", "Fresh evidence timestamps", 80)
    add_pos("reasoning_strength", "Stable reasoning strength", 75)
    add_pos("valuation_certainty", "Consistent valuation", 75)
    add_pos("forecast_stability", "Stable financial / forecast metrics", 75)
    if components["macro_stability"] < 72:
        negatives.append(
            ConfidenceContributor(
                key="macro_stability",
                label="Macro uncertainty",
                direction="negative",
                points=float(components["macro_stability"] - 72),
                detail=f"macro_stability={components['macro_stability']}",
            )
        )
    elif components["macro_stability"] >= 80:
        positives.append(
            ConfidenceContributor(
                key="macro_stability",
                label="Macro stability",
                direction="positive",
                points=float(components["macro_stability"]),
                detail=f"macro_stability={components['macro_stability']}",
            )
        )

    if components["forecast_stability"] < 70:
        negatives.append(
            ConfidenceContributor(
                key="forecast_visibility",
                label="Limited forecast visibility",
                direction="negative",
                points=float(components["forecast_stability"] - 70),
                detail=f"forecast_stability={components['forecast_stability']}",
            )
        )

    if components["unknown_penalty"] < 0:
        penalties.append(
            ConfidenceContributor(
                key="unknown_penalty",
                label="Unknowns penalty",
                direction="penalty",
                points=float(components["unknown_penalty"]),
                detail="Unresolved unknowns reduce calibrated confidence",
            )
        )
        negatives.append(
            ConfidenceContributor(
                key="unknown_penalty",
                label="Unresolved unknowns",
                direction="negative",
                points=float(components["unknown_penalty"]),
                detail=f"unknown_penalty={components['unknown_penalty']}",
            )
        )
        unknowns.append("Unresolved unknowns reduce trust in the current decision")

    if components["contradiction_penalty"] < 0:
        penalties.append(
            ConfidenceContributor(
                key="contradiction_penalty",
                label="Contradiction penalty",
                direction="penalty",
                points=float(components["contradiction_penalty"]),
                detail="Contradicting reasons / risks reduce calibrated confidence",
            )
        )
        negatives.append(
            ConfidenceContributor(
                key="contradiction_penalty",
                label="Contradicting evidence / risks",
                direction="negative",
                points=float(components["contradiction_penalty"]),
                detail=f"contradiction_penalty={components['contradiction_penalty']}",
            )
        )

    if not positives and final_confidence >= 50:
        positives.append(
            ConfidenceContributor(
                key="base_stack",
                label="Decision stack intact",
                direction="positive",
                points=float(final_confidence),
                detail="Core evidence→reason→decision chain present",
            )
        )
    return positives, negatives, penalties, unknowns


def confidence_breakdown_dict(calibration: Calibration) -> Dict[str, Any]:
    return {
        "confidence": calibration.final_confidence,
        "positive": [c.to_dict() for c in calibration.positive_contributors],
        "negative": [c.to_dict() for c in calibration.negative_contributors],
        "unknowns": list(calibration.unknowns),
        "penalties": [c.to_dict() for c in calibration.penalties],
        "bonuses": [c.to_dict() for c in calibration.bonuses],
        "components": {
            "evidence_quality": calibration.evidence_quality,
            "evidence_freshness": calibration.evidence_freshness,
            "evidence_coverage": calibration.evidence_coverage,
            "reasoning_strength": calibration.reasoning_strength,
            "rule_consistency": calibration.rule_consistency,
            "valuation_certainty": calibration.valuation_certainty,
            "forecast_stability": calibration.forecast_stability,
            "macro_stability": calibration.macro_stability,
            "unknown_penalty": calibration.unknown_penalty,
            "contradiction_penalty": calibration.contradiction_penalty,
        },
        "weighted_components": dict(calibration.weighted_components),
        "profile_version": calibration.profile_version,
        "formula_trace": list(calibration.formula_trace),
    }
