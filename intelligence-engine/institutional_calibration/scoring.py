"""IDS-02 scoring helpers — component scores from evidence + reasons + decision."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

from institutional_decision.models import InstitutionalDecision
from institutional_decision.recommendation_rules import business_quality_band_safe
from institutional_reporting.models import InstitutionalReportInput
from institutional_reporting.reasoning import Reason

from .schema import clamp_int


def evidence_quality_score(payload: InstitutionalReportInput) -> int:
    """Blend business-quality signal, evidence depth, and positive drivers."""
    bq = payload.business_quality
    try:
        bq_num = float(bq)
        if bq_num <= 10:
            bq_num *= 10.0
    except (TypeError, ValueError):
        band = business_quality_band_safe(bq)
        bq_num = {"Excellent": 95, "Strong": 88, "Adequate": 70, "Weak": 45}.get(band, 60)

    evidence_n = len(payload.evidence or ())
    evidence_depth = min(100.0, 55.0 + evidence_n * 10.0)
    driver_boost = min(12.0, len(payload.positive_drivers or ()) * 4.0)
    driver_drag = min(12.0, len(payload.negative_drivers or ()) * 3.0)
    blended = 0.55 * bq_num + 0.35 * evidence_depth + driver_boost - driver_drag
    return clamp_int(blended)


def evidence_freshness_score(payload: InstitutionalReportInput) -> int:
    """Prefer dated as_of; conference-call / quarterly sources score fresher."""
    base = 62
    if str(payload.as_of or "").strip():
        base += 18
    fresh_types = 0
    for e in payload.evidence or ():
        st = str(getattr(e, "source_type", "") or "").lower()
        if any(tok in st for tok in ("conference", "quarterly", "call", "results", "filing")):
            fresh_types += 1
    base += min(16, fresh_types * 4)
    return clamp_int(base)


def evidence_coverage_score(
    payload: InstitutionalReportInput,
    reasons: Sequence[Reason],
) -> int:
    """Coverage = section breadth on evidence + reasons with supporting material."""
    section_keys: set[str] = set()
    for e in payload.evidence or ():
        for sk in getattr(e, "section_keys", ()) or ():
            if sk:
                section_keys.add(str(sk))
    section_cov = min(len(section_keys), 12) / 12.0

    dims_total = max(len(reasons), 1)
    dims_with = 0
    for r in reasons:
        if (getattr(r, "supporting_evidence", None) or ()) or (getattr(r, "supporting_points", None) or ()):
            dims_with += 1
    reason_cov = dims_with / dims_total
    return clamp_int(48 + section_cov * 30 + reason_cov * 22)


def reasoning_strength_score(reasons: Sequence[Reason]) -> int:
    if not reasons:
        return 40
    confs = [float(r.confidence) for r in reasons if r.confidence is not None and float(r.confidence) >= 0]
    if not confs:
        return 50
    # Reason confidence may be 0–1 or 0–100
    normed = [c * 100.0 if c <= 1.0 else c for c in confs]
    base = sum(normed) / len(normed)
    # Template reasons often carry a single unknown/contra each — only penalize density of empties
    weak = sum(
        1
        for r in reasons
        if len(r.supporting_points or ()) == 0 or float(r.confidence or 0) < 0.5
    )
    base -= (weak / len(reasons)) * 15
    return clamp_int(base)


def rule_consistency_score(decision: InstitutionalDecision) -> int:
    path = str(getattr(decision, "rule_path", "") or "").strip()
    if not path:
        return 70
    if decision.decision_graph is None or not decision.decision_graph.nodes:
        return 80
    return 100


def valuation_certainty_score(
    payload: InstitutionalReportInput,
    decision: InstitutionalDecision,
) -> int:
    val = str(payload.valuation or "").strip().title()
    certainty = {
        "Cheap": 88,
        "Fair": 78,
        "Expensive": 72,
        "Unclear": 48,
    }.get(val, 55)
    if payload.valuation_reasons:
        certainty += min(8, len(payload.valuation_reasons) * 3)
    # Score magnitude from IDS rule score reinforces certainty of directional view
    magnitude = abs(int(decision.score or 0))
    certainty += min(8, magnitude)
    return clamp_int(certainty)


def forecast_stability_score(
    payload: InstitutionalReportInput,
    decision: InstitutionalDecision,
) -> int:
    fq = str(payload.financial_quality or "").strip().title()
    base = {
        "Excellent": 88,
        "Strong": 82,
        "Stable": 74,
        "Weak": 48,
        "Unclear": 55,
    }.get(fq, 60)
    unknowns = list(payload.unknowns or ()) + list(decision.unknowns or ())
    forecast_unknown = sum(
        1
        for u in unknowns
        if any(
            w in str(u).lower()
            for w in ("forecast", "guidance", "visibility", "outlook", "normalization", "timeline", "pace")
        )
    )
    base -= forecast_unknown * 7
    if payload.catalysts:
        base += min(6, len(payload.catalysts) * 2)
    return clamp_int(base)


def macro_stability_score(
    payload: InstitutionalReportInput,
    decision: InstitutionalDecision,
) -> int:
    # Macro node defaults to Neutral in IDS graph; sector banking → mild cyclicality
    base = 72
    sector = str(payload.sector or decision.sector or "").lower()
    if "bank" in sector:
        base -= 4
    risk = str(payload.overall_risk or "").strip().title()
    risk_adj = {"Low": 8, "Moderate": -2, "High": -12, "Severe": -18}.get(risk, 0)
    # Negative drivers that look macro/sector
    macro_neg = sum(
        1
        for d in (payload.negative_drivers or ())
        if any(w in str(d).lower() for w in ("macro", "sector", "regulatory", "cycle", "competitive"))
    )
    return clamp_int(base + risk_adj - macro_neg * 5)


def unknown_penalty_points(
    reasons: Sequence[Reason],
    decision: InstitutionalDecision,
    payload: InstitutionalReportInput,
) -> int:
    """Display penalty from unique input/decision unknowns (reason templates ignored)."""
    del reasons  # reasons carry repeated template unknowns — not additive
    texts: set[str] = set()
    for u in list(payload.unknowns or ()) + list(decision.unknowns or ()):
        t = str(u or "").strip().lower()
        if t:
            texts.add(t)
    n = len(texts)
    # Example band: 1 → -3, 3 → -9, 4+ → -12
    return int(-min(12, n * 3))


def contradiction_penalty_points(
    reasons: Sequence[Reason],
    decision: InstitutionalDecision,
    payload: InstitutionalReportInput,
) -> int:
    """Soft contradiction penalty from material risk / bear pressure — not every reason row."""
    del reasons
    pressure = 0
    pressure += min(2, len(payload.risks or ()))
    pressure += min(2, len(payload.negative_drivers or ()))
    pressure += min(1, len(payload.bear_points or ()))
    # Decision-level contradicting reasons beyond the first two are material
    contra_n = len(decision.contradicting_reasons or ())
    if contra_n >= 4:
        pressure += 1
    if str(payload.valuation or "").strip().title() == "Expensive":
        pressure += 1
    # 0 → 0, 1 → -3, 2 → -5, 3+ → -8 (cap -10)
    table = {0: 0, 1: -3, 2: -5, 3: -8}
    return int(table.get(pressure, -10))


def collect_component_scores(
    decision: InstitutionalDecision,
    reasons: Sequence[Reason],
    evidence: InstitutionalReportInput,
) -> Dict[str, int]:
    return {
        "evidence_quality": evidence_quality_score(evidence),
        "evidence_freshness": evidence_freshness_score(evidence),
        "evidence_coverage": evidence_coverage_score(evidence, reasons),
        "reasoning_strength": reasoning_strength_score(reasons),
        "rule_consistency": rule_consistency_score(decision),
        "valuation_certainty": valuation_certainty_score(evidence, decision),
        "forecast_stability": forecast_stability_score(evidence, decision),
        "macro_stability": macro_stability_score(evidence, decision),
        "unknown_penalty": unknown_penalty_points(reasons, decision, evidence),
        "contradiction_penalty": contradiction_penalty_points(reasons, decision, evidence),
    }


def _points_for_bq(payload: InstitutionalReportInput) -> int:
    try:
        n = float(payload.business_quality)
        if n >= 93:
            return 20
        if n >= 88:
            return 18
        if n >= 75:
            return 12
        if n >= 60:
            return 6
        return 0
    except (TypeError, ValueError):
        band = business_quality_band_safe(payload.business_quality)
        return {"Excellent": 20, "Strong": 18, "Adequate": 10, "Weak": 0}.get(band, 8)


def scorecard_lines(
    decision: InstitutionalDecision,
    evidence: InstitutionalReportInput,
    *,
    unknown_penalty: int,
) -> Tuple[List[Dict[str, Any]], int]:
    """Dimensional decision scorecard (display points, not the confidence formula)."""
    fq = str(evidence.financial_quality or "").strip().title()
    fq_pts = {"Excellent": 18, "Strong": 15, "Stable": 10, "Weak": -6, "Unclear": 0}.get(fq, 5)
    val = str(evidence.valuation or "").strip().title()
    val_pts = {"Cheap": 12, "Fair": 2, "Expensive": -8, "Unclear": -2}.get(val, 0)
    risk = str(evidence.overall_risk or "").strip().title()
    risk_pts = {"Low": 8, "Moderate": -4, "High": -10, "Severe": -14}.get(risk, -2)
    # Macro / management from decision graph defaults
    macro_pts = -4 if "bank" in str(evidence.sector or "").lower() else -2
    mgmt_pts = 7 if _points_for_bq(evidence) >= 18 else 5
    evidence_pts = min(8, max(2, len(evidence.evidence or ()) * 2 - 2))
    unk_pts = int(unknown_penalty) if unknown_penalty < 0 else -min(12, len(decision.unknowns or ()) * 3)

    lines = [
        {"dimension": "Business Quality", "points": _points_for_bq(evidence), "note": "supports" if _points_for_bq(evidence) > 0 else "neutral"},
        {"dimension": "Financial Quality", "points": fq_pts, "note": "supports" if fq_pts > 0 else "pressures"},
        {"dimension": "Valuation", "points": val_pts, "note": "supports" if val_pts > 0 else ("pressures" if val_pts < 0 else "neutral")},
        {"dimension": "Risk", "points": risk_pts, "note": "supports" if risk_pts > 0 else "pressures"},
        {"dimension": "Macro", "points": macro_pts, "note": "pressures" if macro_pts < 0 else "neutral"},
        {"dimension": "Management", "points": mgmt_pts, "note": "supports"},
        {"dimension": "Evidence", "points": evidence_pts, "note": "supports"},
        {"dimension": "Unknowns", "points": unk_pts, "note": "penalty" if unk_pts else "none"},
    ]
    total = sum(int(x["points"]) for x in lines)
    return lines, total
