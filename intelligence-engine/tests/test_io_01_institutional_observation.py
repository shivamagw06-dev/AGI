"""IO-01 — Institutional Observation Engine tests (proactive, hysteresis, no LLM)."""

from __future__ import annotations

from institutional_decision import history as decision_history
from institutional_observation.classifier import classify_change, classify_all
from institutional_observation.detector import (
    CompanySnapshot,
    DetectedChange,
    detect_changes,
)
from institutional_observation.diagnostics import quality_gates, validate_observation
from institutional_observation.evaluator import plan_actions
from institutional_observation.hysteresis import DEFAULT_HYSTERESIS, should_emit_observation
from institutional_observation.impact import assess_impact
from institutional_observation.observation import InstitutionalObservation
from institutional_observation.production import (
    get_company_observations,
    health,
    observe_company,
    reset_for_tests,
    soft_slice_mission_control,
)
from institutional_observation.schema import IO_WORKSTREAM_ID
from institutional_observation.significance import assess_significance


def setup_function(_fn=None):
    decision_history.reset_for_tests()
    reset_for_tests()


def test_health():
    h = health()
    assert h["workstream_id"] == IO_WORKSTREAM_ID
    assert h["llm"] is False
    assert h["proactive"] is True
    assert h["hysteresis"]["valuation_change_pct_min"] == 2.0
    assert h["hysteresis"]["confidence_change_min"] == 1


def test_detection_new_changed_removed():
    prev = CompanySnapshot(
        ticker="AXISBANK",
        evidence_ids=("E1", "E2"),
        valuation="Fair",
        confidence=70,
        recommendation="HOLD",
    )
    cur = CompanySnapshot(
        ticker="AXISBANK",
        evidence_ids=("E2", "E3"),
        valuation="Cheap",
        confidence=72,
        recommendation="HOLD",
    )
    changes = detect_changes(prev, cur)
    kinds = {c.kind for c in changes}
    keys = {c.key for c in changes}
    assert "new_evidence" in kinds
    assert "removed_evidence" in kinds
    assert "valuation" in kinds
    assert "E3" in keys
    assert "E1" in keys


def test_classification_rbi_and_earnings():
    rbi = classify_change(
        DetectedChange(kind="event", key="rbi_repo_cut", detail="RBI repo cut 25bps", magnitude=1.0)
    )
    assert rbi.category == "Macro"
    assert rbi.severity == "high"
    assert rbi.confidence >= 0.96

    earn = classify_change(
        DetectedChange(
            kind="event",
            key="quarterly_results",
            detail="Quarterly earnings miss",
            magnitude=1.0,
        )
    )
    assert earn.category == "Quarterly Results"
    assert earn.severity == "critical"


def test_significance_hysteresis_confidence():
    prev = CompanySnapshot(ticker="KOTAKBANK", confidence=80, recommendation="HOLD")
    cur = CompanySnapshot(ticker="KOTAKBANK", confidence=80, recommendation="HOLD")
    # Zero delta — ignore
    classified = classify_all(
        [
            DetectedChange(
                kind="factor",
                key="confidence",
                detail="Confidence 80 → 80",
                before=80,
                after=80,
                magnitude=0,
            )
        ]
    )
    sig = assess_significance(classified, previous=prev, current=cur)
    assert sig.emit_observation is False
    assert sig.silent_graph_update is True

    # Sub-threshold forecast revision
    fc_prev = CompanySnapshot(
        ticker="KOTAKBANK", confidence=80, recommendation="HOLD", extras={"forecast_revision": 0.01}
    )
    fc_cur = CompanySnapshot(
        ticker="KOTAKBANK", confidence=80, recommendation="HOLD", extras={"forecast_revision": 0.03}
    )
    fc_changes = detect_changes(fc_prev, fc_cur)
    fc_class = classify_all(fc_changes)
    fc_sig = assess_significance(fc_class, previous=fc_prev, current=fc_cur)
    assert fc_sig.emit_observation is False
    assert fc_sig.silent_graph_update is True


def test_significance_critical_earnings_triggers_recompute():
    prev = CompanySnapshot(ticker="ICICIBANK", confidence=75, recommendation="HOLD")
    cur = CompanySnapshot(ticker="ICICIBANK", confidence=75, recommendation="HOLD")
    classified = classify_all(
        [
            DetectedChange(
                kind="event",
                key="earnings_miss",
                detail="Quarterly earnings miss",
                magnitude=1.0,
            )
        ]
    )
    sig = assess_significance(classified, previous=prev, current=cur)
    assert sig.emit_observation is True
    assert sig.recompute_decision is True
    assert sig.severity == "critical"
    plan = plan_actions(sig, category="Quarterly Results")
    assert plan.recommended_action == "Analyst review"
    assert plan.recompute_decision is True


def test_share_split_no_decision_recompute():
    prev = CompanySnapshot(ticker="HDFCBANK", confidence=78, recommendation="BUY")
    cur = CompanySnapshot(ticker="HDFCBANK", confidence=78, recommendation="BUY")
    classified = classify_all(
        [DetectedChange(kind="event", key="share_split", detail="2:1 share split", magnitude=1.0)]
    )
    sig = assess_significance(classified, previous=prev, current=cur)
    assert sig.recompute_decision is False


def test_impact_and_quality_gates():
    cur = CompanySnapshot(
        ticker="AXISBANK",
        company_name="Axis Bank",
        decision_id="dec-1",
        evidence_snapshot_id="snap-1",
        recommendation="HOLD",
        confidence=70,
    )
    classified = classify_all(
        [
            DetectedChange(
                kind="event",
                key="ceo_resignation",
                detail="CEO resignation",
                magnitude=1.0,
            )
        ]
    )
    impact = assess_impact(classified, current=cur, decision_id="dec-1")
    assert "AXISBANK" in impact.affected_companies
    assert impact.affected_entities
    assert "business_quality" in impact.affected_reasons

    obs = InstitutionalObservation(
        observation_id="io-test",
        company="Axis Bank",
        ticker="AXISBANK",
        timestamp="2026-07-30T00:00:00Z",
        category="Governance",
        severity="critical",
        confidence=0.95,
        summary="CEO resignation",
        evidence_snapshot_id="snap-1",
        affected_entities=impact.affected_entities,
        affected_reasons=impact.affected_reasons,
        affected_decisions=impact.affected_decisions,
        recommended_action="Analyst review",
        diagnostics={"ok": True},
    )
    gates, errors = quality_gates(obs)
    assert all(gates.values())
    assert errors == []
    assert validate_observation(obs) == []


def test_should_emit_hysteresis_helpers():
    assert should_emit_observation("ignore") is False
    assert should_emit_observation("low") is False
    assert should_emit_observation("medium") is True
    assert should_emit_observation("critical") is True
    assert DEFAULT_HYSTERESIS.valuation_change_pct_min == 2.0


def test_observe_axis_quarterly_results():
    baseline = observe_company("AXISBANK")
    assert baseline["ok"] is True
    assert baseline.get("silent_update") is True or not baseline.get("observations")

    result = observe_company(
        "AXISBANK",
        force_events=[
            {
                "key": "quarterly_results",
                "detail": "Quarterly results miss vs consensus",
                "magnitude": 1.0,
            }
        ],
    )
    assert result["ok"] is True
    assert result["observations"]
    obs = result["observations"][0]
    assert obs["category"] == "Quarterly Results"
    assert obs["severity"] == "critical"
    assert obs["recommended_action"]
    assert obs["lineage"]
    assert obs["diagnostics"]
    assert result["plan"]["recompute_decision"] is True


def test_observe_kotak_repo_rate():
    observe_company("KOTAKBANK")
    result = observe_company(
        "KOTAKBANK",
        force_events=[{"key": "rbi_repo_cut", "detail": "RBI repo cut 25bps", "magnitude": 1.0}],
    )
    assert result["ok"] is True
    obs = result["observations"][0]
    assert obs["category"] == "Macro"
    assert obs["severity"] == "high"
    assert obs["confidence"] >= 0.96


def test_observe_icici_management_change():
    observe_company("ICICIBANK")
    result = observe_company(
        "ICICIBANK",
        force_events=[
            {"key": "management_change", "detail": "CEO resignation announced", "magnitude": 1.0}
        ],
    )
    assert result["ok"] is True
    obs = result["observations"][0]
    assert obs["category"] == "Governance"
    assert obs["severity"] == "critical"
    assert obs["requires_review"] is True


def test_observe_hdfc_corporate_action_and_forecast():
    observe_company("HDFCBANK")
    split = observe_company(
        "HDFCBANK",
        force_events=[{"key": "share_split", "detail": "2:1 share split", "magnitude": 1.0}],
    )
    # Low-severity corporate action: silent or no recompute
    assert split["ok"] is True
    assert (split.get("plan") or {}).get("recompute_decision") is False

    # Material forecast revision above hysteresis
    prev = CompanySnapshot(
        ticker="HDFCBANK",
        confidence=78,
        recommendation="BUY",
        evidence_ids=("E1",),
        extras={"forecast_revision": 0.0},
    )
    cur = CompanySnapshot(
        ticker="HDFCBANK",
        confidence=78,
        recommendation="BUY",
        evidence_ids=("E1",),
        extras={"forecast_revision": 0.12},
    )
    changes = detect_changes(prev, cur)
    classified = classify_all(changes)
    sig = assess_significance(classified, previous=prev, current=cur)
    assert sig.emit_observation is True
    assert sig.severity in {"medium", "high", "critical"}


def test_observation_chain_and_mission_control():
    observe_company("AXISBANK")
    observe_company(
        "AXISBANK",
        force_events=[{"key": "earnings_miss", "detail": "Earnings miss", "magnitude": 1.0}],
    )
    pack = get_company_observations("AXISBANK", observe=False)
    assert pack["observations"]
    obs = pack["observations"][-1]
    assert obs["lineage"][0] == "Evidence"
    assert "Observation" in obs["lineage"]
    assert "Decision" in obs["lineage"]
    assert "Report" in obs["lineage"]

    board = soft_slice_mission_control()
    assert board["observation_center"] is True
    assert board["workstream_id"] == IO_WORKSTREAM_ID
    assert board["critical_observations"] >= 1
    assert board["observation_throughput"] >= 1


def test_decision_trigger_deterministic():
    observe_company("AXISBANK")
    a = observe_company(
        "AXISBANK",
        force_events=[{"key": "quarterly_results", "detail": "QR miss", "magnitude": 1.0}],
    )
    reset_for_tests()
    decision_history.reset_for_tests()
    observe_company("AXISBANK")
    b = observe_company(
        "AXISBANK",
        force_events=[{"key": "quarterly_results", "detail": "QR miss", "magnitude": 1.0}],
    )
    assert a["plan"]["recompute_decision"] == b["plan"]["recompute_decision"]
    assert a["observations"][0]["category"] == b["observations"][0]["category"]
    assert a["observations"][0]["severity"] == b["observations"][0]["severity"]
