"""IRE-02 explanation engine — structured Reason objects only (no English templates)."""

from __future__ import annotations

from typing import Sequence

from institutional_reporting.evidence import evidence_ids_for_section
from institutional_reporting.models import InstitutionalReportInput
from institutional_reporting.recommendation import (
    business_quality_band,
    normalize_conviction,
    normalize_recommendation,
)
from institutional_reporting.reasoning import Reason


def _as_list(value: Sequence[str] | str | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    return [str(v).strip() for v in value if str(v).strip()]


def _evidence_labels(inp: InstitutionalReportInput, section_key: str) -> tuple[str, ...]:
    ids = evidence_ids_for_section(inp, section_key)
    by_id = {e.evidence_id: e for e in inp.evidence}
    labels: list[str] = []
    for eid in ids:
        item = by_id.get(eid)
        if item:
            # Prefer stable id + human label for traceability
            labels.append(item.evidence_id)
            if item.label and item.label not in labels:
                labels.append(item.label)
            if item.source_type and item.source_type not in labels:
                labels.append(item.source_type)
        else:
            labels.append(eid)
    if not labels:
        labels = [e.evidence_id for e in inp.evidence if e.evidence_id]
    # Deduplicate preserving order
    seen: set[str] = set()
    out: list[str] = []
    for row in labels:
        if row in seen:
            continue
        seen.add(row)
        out.append(row)
    return tuple(out)


def _confidence_unit(inp: InstitutionalReportInput, *, tilt: float = 0.0) -> float:
    base = max(0.0, min(1.0, float(inp.confidence) / 100.0))
    return round(max(0.0, min(1.0, base + tilt)), 4)


def _ensure_contradiction(points: list[str], fallback: str) -> list[str]:
    return points if points else [fallback]


def _ensure_unknowns(points: list[str], fallback: str) -> list[str]:
    return points if points else [fallback]


def explain_business_quality(inp: InstitutionalReportInput) -> Reason:
    band = business_quality_band(inp.business_quality)
    supporting = _as_list(inp.business_quality_reasons) or _as_list(inp.thesis)[:2]
    if isinstance(inp.business_quality, (int, float)):
        supporting = [f"business_quality_score={inp.business_quality}", *supporting]
    contradicting = _as_list(inp.risks)[:1] or _as_list(inp.negative_drivers)[:1]
    unknowns = _as_list(inp.unknowns)[:1]
    return Reason(
        title="Business Quality",
        conclusion=band,
        confidence=_confidence_unit(inp, tilt=0.02),
        supporting_evidence=_evidence_labels(inp, "business_quality"),
        supporting_points=tuple(supporting or ["franchise_quality_inputs_present"]),
        contradicting_points=tuple(
            _ensure_contradiction(contradicting, "competitive_or_cycle_pressure_not_fully_ruled_out")
        ),
        unknowns=tuple(_ensure_unknowns(unknowns, "forward_franchise_durability_unverified")),
        section_key="business_quality",
    )


def explain_financial_quality(inp: InstitutionalReportInput) -> Reason:
    label = str(inp.financial_quality or "").strip() or "Unclear"
    supporting = _as_list(inp.financial_quality_reasons) or [f"financial_quality={label}"]
    contradicting = _as_list(inp.risks)[:1]
    if str(inp.overall_risk).title() in {"High", "Severe"}:
        contradicting.append(f"overall_risk={inp.overall_risk}")
    unknowns = _as_list(inp.unknowns)[:1] or ["earnings_path_sensitivity_unverified"]
    return Reason(
        title="Financial Quality",
        conclusion=label,
        confidence=_confidence_unit(inp),
        supporting_evidence=_evidence_labels(inp, "financial_quality"),
        supporting_points=tuple(supporting),
        contradicting_points=tuple(
            _ensure_contradiction(contradicting, "credit_cost_or_margin_volatility_possible")
        ),
        unknowns=tuple(_ensure_unknowns(unknowns, "forward_earnings_quality_unverified")),
        section_key="financial_quality",
    )


def explain_valuation(inp: InstitutionalReportInput) -> Reason:
    label = str(inp.valuation or "").strip().title() or "Unclear"
    supporting = _as_list(inp.valuation_reasons) or [f"valuation={label}"]
    contradicting: list[str] = []
    if label == "Expensive":
        contradicting.append("limited_margin_of_safety")
    elif label == "Cheap":
        contradicting.append("cheapness_may_reflect_unresolved_risk")
    else:
        contradicting.extend(_as_list(inp.negative_drivers)[:1] or ["no_clear_valuation_edge"])
    unknowns = _as_list(inp.unknowns)[:1] or ["normalized_earnings_power_unverified"]
    return Reason(
        title="Valuation",
        conclusion=label,
        confidence=_confidence_unit(inp, tilt=-0.02),
        supporting_evidence=_evidence_labels(inp, "valuation"),
        supporting_points=tuple(supporting),
        contradicting_points=tuple(_ensure_contradiction(contradicting, "valuation_signal_incomplete")),
        unknowns=tuple(_ensure_unknowns(unknowns, "peer_multiple_normalization_unverified")),
        section_key="valuation",
    )


def explain_risk(inp: InstitutionalReportInput) -> Reason:
    label = str(inp.overall_risk or "").strip().title() or "Unclear"
    supporting = _as_list(inp.risk_reasons) or _as_list(inp.risks) or [f"overall_risk={label}"]
    # Contradicting risk view = factors that soften the risk call
    contradicting = _as_list(inp.positive_drivers)[:1] or _as_list(inp.thesis)[:1]
    unknowns = _as_list(inp.unknowns)[:1] or ["tail_risk_path_unverified"]
    return Reason(
        title="Risk Assessment",
        conclusion=label,
        confidence=_confidence_unit(inp, tilt=-0.01),
        supporting_evidence=_evidence_labels(inp, "risk_assessment"),
        supporting_points=tuple(supporting),
        contradicting_points=tuple(
            _ensure_contradiction(contradicting, "stabilizing_franchise_factors_present")
        ),
        unknowns=tuple(_ensure_unknowns(unknowns, "forward_risk_realization_unverified")),
        section_key="risk_assessment",
    )


def explain_recommendation(inp: InstitutionalReportInput) -> Reason:
    rec = normalize_recommendation(inp.recommendation)
    conv = normalize_conviction(inp.conviction)
    supporting = [
        f"recommendation={rec}",
        f"conviction={conv}",
        f"horizon={inp.horizon}",
        *(_as_list(inp.thesis)[:2]),
    ]
    contradicting = _as_list(inp.risks)[:2] or _as_list(inp.bear_points)[:1]
    unknowns = _as_list(inp.unknowns)[:2] or ["decision_path_depends_on_unresolved_inputs"]
    return Reason(
        title="Institutional View",
        conclusion=rec,
        confidence=_confidence_unit(inp),
        supporting_evidence=_evidence_labels(inp, "institutional_view"),
        supporting_points=tuple(supporting),
        contradicting_points=tuple(
            _ensure_contradiction(contradicting, "material_risks_remain_in_force")
        ),
        unknowns=tuple(_ensure_unknowns(unknowns, "catalyst_timing_unverified")),
        section_key="institutional_view",
    )


def explain_horizon(inp: InstitutionalReportInput) -> Reason:
    return Reason(
        title="Investment Horizon",
        conclusion=str(inp.horizon),
        confidence=_confidence_unit(inp),
        supporting_evidence=_evidence_labels(inp, "investment_horizon"),
        supporting_points=(f"horizon={inp.horizon}", f"conviction={normalize_conviction(inp.conviction)}"),
        contradicting_points=("near_term_noise_may_dominate_short_windows",),
        unknowns=("holding_period_realization_path_unverified",),
        section_key="investment_horizon",
    )


def explain_confidence_section(inp: InstitutionalReportInput) -> Reason:
    return Reason(
        title="Confidence",
        conclusion=str(int(inp.confidence)),
        confidence=_confidence_unit(inp),
        supporting_evidence=_evidence_labels(inp, "confidence"),
        supporting_points=tuple(_as_list(inp.positive_drivers) or _as_list(inp.thesis)[:2] or ["drivers_present"]),
        contradicting_points=tuple(
            _as_list(inp.negative_drivers) or _as_list(inp.risks)[:1] or ["offsetting_risks_present"]
        ),
        unknowns=tuple(_as_list(inp.unknowns) or ["confidence_inputs_partially_unverified"]),
        section_key="confidence",
    )


def explain_thesis(inp: InstitutionalReportInput) -> Reason:
    points = _as_list(inp.thesis) or ["thesis_inputs_present"]
    return Reason(
        title="Investment Thesis",
        conclusion="Active",
        confidence=_confidence_unit(inp),
        supporting_evidence=_evidence_labels(inp, "investment_thesis"),
        supporting_points=tuple(points),
        contradicting_points=tuple(_as_list(inp.risks)[:2] or ["thesis_faces_material_risks"]),
        unknowns=tuple(_as_list(inp.unknowns)[:1] or ["thesis_durability_unverified"]),
        section_key="investment_thesis",
    )


def explain_bull_case(inp: InstitutionalReportInput) -> Reason:
    points = _as_list(inp.bull_points) or _as_list(inp.catalysts) or _as_list(inp.thesis)[:2]
    return Reason(
        title="Bull Case",
        conclusion="Constructive path",
        confidence=_confidence_unit(inp, tilt=0.03),
        supporting_evidence=_evidence_labels(inp, "bull_case"),
        supporting_points=tuple(points or ["constructive_catalysts_present"]),
        contradicting_points=tuple(_as_list(inp.bear_points)[:2] or _as_list(inp.risks)[:1] or ["bear_risks_remain"]),
        unknowns=tuple(_as_list(inp.unknowns)[:1] or ["bull_path_timing_unverified"]),
        section_key="bull_case",
    )


def explain_bear_case(inp: InstitutionalReportInput) -> Reason:
    points = _as_list(inp.bear_points) or _as_list(inp.risks)[:3]
    return Reason(
        title="Bear Case",
        conclusion="Adverse path",
        confidence=_confidence_unit(inp, tilt=-0.03),
        supporting_evidence=_evidence_labels(inp, "bear_case"),
        supporting_points=tuple(points or ["adverse_risks_present"]),
        contradicting_points=tuple(
            _as_list(inp.bull_points)[:2] or _as_list(inp.positive_drivers)[:1] or ["stabilizers_present"]
        ),
        unknowns=tuple(_as_list(inp.unknowns)[:1] or ["bear_path_severity_unverified"]),
        section_key="bear_case",
    )


def explain_watch_items(inp: InstitutionalReportInput) -> Reason:
    points = _as_list(inp.watch_items) or ["monitor_core_operating_metrics"]
    return Reason(
        title="Watch Items",
        conclusion="Monitoring required",
        confidence=_confidence_unit(inp),
        supporting_evidence=_evidence_labels(inp, "watch_items"),
        supporting_points=tuple(points),
        contradicting_points=("not_all_watch_items_are_currently_breached",),
        unknowns=("watch_item_thresholds_may_evolve",),
        section_key="watch_items",
    )


def explain_evidence_section(inp: InstitutionalReportInput) -> Reason:
    labels = [e.evidence_id for e in inp.evidence if e.evidence_id]
    return Reason(
        title="Evidence",
        conclusion=f"{len(labels)} items",
        confidence=_confidence_unit(inp),
        supporting_evidence=tuple(labels),
        supporting_points=tuple(labels or ["evidence_catalog_present"]),
        contradicting_points=("evidence_coverage_may_be_incomplete_vs_full_universe",),
        unknowns=("unobserved_primary_sources_may_exist",),
        section_key="evidence",
    )


def explain_bottom_line(inp: InstitutionalReportInput) -> Reason:
    rec = normalize_recommendation(inp.recommendation)
    return Reason(
        title="Bottom Line",
        conclusion=rec,
        confidence=_confidence_unit(inp),
        supporting_evidence=_evidence_labels(inp, "bottom_line"),
        supporting_points=(
            f"recommendation={rec}",
            f"conviction={normalize_conviction(inp.conviction)}",
            f"confidence_pct={int(inp.confidence)}",
            f"horizon={inp.horizon}",
        ),
        contradicting_points=tuple(_as_list(inp.risks)[:1] or ["residual_risks_remain"]),
        unknowns=tuple(_as_list(inp.unknowns)[:1] or ["outcome_path_unverified"]),
        section_key="bottom_line",
    )
