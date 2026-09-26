"""IDS-02 — Decision Calibration & Explainability tests (no LLM)."""

from __future__ import annotations

from institutional_calibration.calibration_engine import calibrate_decision
from institutional_calibration.confidence import compute_calibration
from institutional_calibration.drift import detect_drift
from institutional_calibration.profile import CalibrationProfile, DEFAULT_PROFILE
from institutional_calibration.production import health as cal_health
from institutional_calibration.schema import CAL_WORKSTREAM_ID
from institutional_calibration.scoring import collect_component_scores
from institutional_decision import history as decision_history
from institutional_decision.decision_engine import generate_decision
from institutional_decision.production import decide_company, get_company_decision
from institutional_reporting.composer import compose_report
from institutional_reporting.fixtures import get_fixture
from institutional_reporting.reason_composer import compose_reasons


def setup_function(_fn=None):
    decision_history.reset_for_tests()


def test_calibration_health():
    h = cal_health()
    assert h["workstream_id"] == CAL_WORKSTREAM_ID
    assert h["confidence_computed"] is True
    assert h["llm"] is False
    assert h["default_profile"]["evidence_quality_weight"] == DEFAULT_PROFILE.evidence_quality_weight


def test_confidence_is_computed_not_assigned():
    fixture = get_fixture("AXISBANK")
    assert fixture is not None
    graph = compose_reasons(fixture)
    decision = generate_decision(
        reasons=graph.reasons,
        valuation=fixture.valuation,
        risks=list(fixture.risks),
        confidence=999,  # opaque input — must be overwritten
        business_quality=fixture.business_quality,
        financial_quality=fixture.financial_quality,
        overall_risk=fixture.overall_risk,
        ticker=fixture.ticker,
        unknowns=list(fixture.unknowns),
        evidence_ids=[e.evidence_id for e in fixture.evidence],
        company_name=fixture.company_name,
        sector=fixture.sector,
    )
    assert decision.confidence == 100  # clamped from 999 before calibration
    updated, bundle = calibrate_decision(decision, reasons=graph.reasons, evidence=fixture)
    assert updated.calibrated is True
    assert updated.confidence == bundle.calibration.final_confidence
    assert updated.confidence != 999
    assert 0 <= updated.confidence <= 100
    assert updated.calibration_profile_version == DEFAULT_PROFILE.profile_version
    assert bundle.calibration.formula_trace
    assert bundle.calibration.positive_contributors or bundle.calibration.negative_contributors


def test_profile_weights_change_confidence():
    fixture = get_fixture("AXISBANK")
    graph = compose_reasons(fixture)
    decision = generate_decision(
        reasons=graph.reasons,
        valuation=fixture.valuation,
        risks=list(fixture.risks),
        confidence=67,
        business_quality=fixture.business_quality,
        financial_quality=fixture.financial_quality,
        overall_risk=fixture.overall_risk,
        ticker=fixture.ticker,
        unknowns=list(fixture.unknowns),
        evidence_ids=[e.evidence_id for e in fixture.evidence],
    )
    components = collect_component_scores(decision, graph.reasons, fixture)
    # Stress macro — heavier macro weight must pull confidence down vs default
    stressed = {**components, "macro_stability": 40}
    base = compute_calibration(stressed, profile=DEFAULT_PROFILE)
    heavy_macro = CalibrationProfile(
        evidence_quality_weight=0.10,
        reasoning_strength_weight=0.10,
        valuation_certainty_weight=0.10,
        forecast_stability_weight=0.10,
        macro_stability_weight=0.50,
        unknown_penalty_weight=0.05,
        contradiction_penalty_weight=0.05,
        profile_version="ids-02-profile-test-heavy-macro",
        profile_id="heavy_macro",
    )
    alt = compute_calibration(stressed, profile=heavy_macro)
    assert alt.final_confidence < base.final_confidence
    assert alt.profile_version == "ids-02-profile-test-heavy-macro"
    # Profile version is recorded for reproducibility
    _, bundle = calibrate_decision(
        decision, reasons=graph.reasons, evidence=fixture, profile=heavy_macro
    )
    assert bundle.calibration.profile_version == "ids-02-profile-test-heavy-macro"


def test_scorecard_and_explainability():
    fixture = get_fixture("KOTAKBANK")
    graph = compose_reasons(fixture)
    decision = generate_decision(
        reasons=graph.reasons,
        valuation=fixture.valuation,
        risks=list(fixture.risks),
        confidence=fixture.confidence,
        business_quality=fixture.business_quality,
        financial_quality=fixture.financial_quality,
        overall_risk=fixture.overall_risk,
        ticker=fixture.ticker,
        unknowns=list(fixture.unknowns),
        evidence_ids=[e.evidence_id for e in fixture.evidence],
    )
    updated, bundle = calibrate_decision(decision, reasons=graph.reasons, evidence=fixture)
    assert bundle.scorecard.lines
    dims = {line.dimension for line in bundle.scorecard.lines}
    assert "Business Quality" in dims
    assert "Valuation" in dims
    assert "Unknowns" in dims
    exp = bundle.explainability
    assert exp.why_hold or exp.why_buy or exp.why_sell
    assert exp.why_not_buy or exp.why_not_sell
    assert exp.what_reduced_confidence or exp.what_increased_confidence
    assert exp.what_would_change
    assert updated.recommendation == bundle.scorecard.recommendation


def test_decision_drift():
    fixture = get_fixture("AXISBANK")
    graph = compose_reasons(fixture)
    d1 = generate_decision(
        reasons=graph.reasons,
        valuation="Cheap",
        risks=list(fixture.risks),
        confidence=80,
        business_quality=92,
        financial_quality="Strong",
        overall_risk="Low",
        ticker="AXISBANK",
        unknowns=list(fixture.unknowns),
        evidence_ids=[e.evidence_id for e in fixture.evidence],
    )
    d1, b1 = calibrate_decision(d1, reasons=graph.reasons, evidence=fixture)
    d2 = generate_decision(
        reasons=graph.reasons,
        valuation="Fair",
        risks=list(fixture.risks),
        confidence=67,
        business_quality=91,
        financial_quality="Stable",
        overall_risk="Moderate",
        ticker="AXISBANK",
        unknowns=list(fixture.unknowns),
        evidence_ids=[e.evidence_id for e in fixture.evidence],
        previous_version=d1.decision_version,
    )
    d2, b2 = calibrate_decision(d2, reasons=graph.reasons, evidence=fixture, previous=d1)
    assert b2.drift.has_previous is True
    assert b2.drift.previous_recommendation == d1.recommendation
    assert b2.drift.current_recommendation == d2.recommendation
    assert b2.drift.explanation_chain
    # Unit drift helper
    drift = detect_drift(d2, d1)
    assert drift.confidence_delta == d2.confidence - d1.confidence


def test_lineage_complete():
    fixture = get_fixture("HDFCBANK")
    graph = compose_reasons(fixture)
    decision = generate_decision(
        reasons=graph.reasons,
        valuation=fixture.valuation,
        risks=list(fixture.risks),
        confidence=fixture.confidence,
        business_quality=fixture.business_quality,
        financial_quality=fixture.financial_quality,
        overall_risk=fixture.overall_risk,
        ticker=fixture.ticker,
        unknowns=list(fixture.unknowns),
        evidence_ids=[e.evidence_id for e in fixture.evidence],
    )
    _, bundle = calibrate_decision(decision, reasons=graph.reasons, evidence=fixture)
    assert bundle.lineage.chain == [
        "Evidence",
        "Reason Objects",
        "Decision",
        "Calibration",
        "Report",
    ]
    assert bundle.lineage.evidence_snapshot_id
    assert bundle.lineage.decision_id


def test_integration_four_banks_different_calibration():
    confidences = {}
    penalties = {}
    for ticker in ("AXISBANK", "KOTAKBANK", "ICICIBANK", "HDFCBANK"):
        decision_history.reset_for_tests()
        out = decide_company(
            {"ticker": ticker, "include_calibration": True, "include_drift": True}
        )
        assert out["ok"] is True, out.get("validation_errors")
        d = out["decision"]
        assert d["calibrated"] is True
        assert d["calibration"] is not None
        assert out.get("calibration") is not None
        assert out.get("scorecard") is not None
        confidences[ticker] = d["confidence"]
        penalties[ticker] = (
            d["calibration"]["unknown_penalty"],
            d["calibration"]["contradiction_penalty"],
        )
        # Deterministic re-run
        out2 = decide_company(
            {"ticker": ticker, "include_calibration": True, "include_drift": True}
        )
        assert out2["decision"]["confidence"] == d["confidence"]

    # Not all identical opaque scores — calibration differentiates stacks
    assert len(set(confidences.values())) >= 2 or len(set(penalties.values())) >= 2


def test_report_consumes_calibrated_decision():
    decision_history.reset_for_tests()
    fixture = get_fixture("ICICIBANK")
    report = compose_report(fixture)
    assert report.ok is True
    assert report.decision is not None
    assert getattr(report.decision, "calibrated", False) is True
    assert report.confidence == report.decision.confidence
    assert report.diagnostics.get("calibrated") is True
    assert report.diagnostics.get("calibration_version")


def test_api_get_includes_calibration_and_drift():
    decision_history.reset_for_tests()
    out = get_company_decision(
        "AXISBANK", include_calibration=True, include_drift=True
    )
    assert out["ok"] is True
    assert out.get("calibration")
    assert out.get("scorecard")
    assert out.get("drift") is not None
    assert out.get("lineage")


def test_cli_main():
    from institutional_calibration.__main__ import main

    assert main(["--health"]) == 0
    assert main(["--ticker", "AXISBANK"]) == 0
