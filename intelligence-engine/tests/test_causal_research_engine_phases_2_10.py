from dataclasses import replace

import pytest

from app.tools.executor import ToolExecutionContext, build_core_read_executor
from app.tools.registry import plan_tools
from causal_research_engine.event_analysis import event_candidates, normalize_event
from causal_research_engine.financial_transmission import calculate_impact
from causal_research_engine.learning import propose_from_document
from causal_research_engine.outcomes import record_outcome
from causal_research_engine.reasoning import detect_contradictions, temporal_slice
from causal_research_engine.retrieval import relevant_subgraph
from causal_research_engine.scenarios import build_scenarios
from causal_research_engine.schema import CausalRelationship, EvidenceReference
from causal_research_engine.service import ask_context
from causal_research_engine.thesis_bridge import propose_thesis_update


def evidence(eid="E1", available="2026-08-10"):
    return EvidenceReference(eid, "exchange_filing", "NSE:1", available_at=available, quality="VALIDATED")


def relationship(rid="R1", direction="POSITIVE", valid_from="2026-01-01", valid_to=None):
    return CausalRelationship(rid, "tariff increase", "ARPU", direction, "DIRECT", "OBSERVATION",
        industry="telecom", company_id="BHARTIARTL", strength="HIGH", confidence=.8,
        time_lag="1_QUARTER", mechanism="Price realization changes ARPU", evidence=(evidence(rid + "E"),),
        source_count=1, source_quality="VALIDATED", valid_from=valid_from, valid_to=valid_to, status="VALIDATED")


def test_phase2_bounded_existing_graph_retrieval():
    out = relevant_subgraph(["HDFCBANK"], depth=2, analysis_as_of="2026-08-15")
    assert out["source_graph"] == "AGI_CIG"
    assert out["relationship_count"] > 0
    assert all(row.created_by == "causal_graph_adapter" for row in out["relationships"])


def test_phase3_event_normalization_and_candidate_mapping():
    event = normalize_event({"event_id": "EV1", "title": "Airtel tariff increase", "event_type": "tariff",
        "event_date": "2026-08-10", "available_at": "2026-08-10", "source_id": "NSE:EV1",
        "company_id": "BHARTIARTL", "industry": "telecom"}, analysis_as_of="2026-08-15")
    assert event_candidates(event, [relationship()])
    with pytest.raises(ValueError, match="POINT_IN_TIME"):
        normalize_event({"title": "future", "available_at": "2026-09-01", "source_id": "x"}, analysis_as_of="2026-08-15")


def test_phase4_afe_bridge_preserves_trace_and_quarantines_bad_math():
    ok = calculate_impact(company_id="BHARTIARTL", event_id="EV1", metric="revenue", calculation_id="TELECOM_REVENUE_IMPACT",
        inputs={"arpu": 200, "tariff_change": .1, "subscribers": 10, "realization": .8}, evidence_ids=("E1",),
        analysis_as_of="2026-08-15", scenario="BASE", assumptions=("80% realization",))
    assert ok.afe_result["deterministic"] is True and ok.epistemic_label == "SCENARIO"
    bad = calculate_impact(company_id="X", event_id="E", metric="x", calculation_id="NOPE", inputs={},
        evidence_ids=("E",), analysis_as_of="2026-08-15")
    assert bad.status == "QUARANTINED"


def test_phase5_scenarios_are_explicit_and_probabilities_governed():
    impact = calculate_impact(company_id="BHARTIARTL", event_id="EV1", metric="revenue", calculation_id="PERCENT_CHANGE",
        inputs={"beginning": 100, "end": 110}, evidence_ids=("E1",), analysis_as_of="2026-08-15",
        scenario="BASE", assumptions=("Illustrative",))
    out = build_scenarios([relationship()], [impact])
    assert sum(x.probability for x in out) == 1 and all(x.epistemic_label == "SCENARIO" for x in out)
    with pytest.raises(ValueError): build_scenarios([], [], probabilities={"BASE": .8})


def test_phase6_thesis_bridge_only_proposes():
    proposal = propose_thesis_update(thesis_id="T1", relationships=[relationship()], impacts=[])
    assert proposal.status == "PROPOSED" and proposal.monitoring_indicators == ("ARPU",)


def test_phase7_contradiction_and_temporal_reasoning():
    rows = [relationship("R1", "POSITIVE"), relationship("R2", "NEGATIVE"), relationship("OLD", valid_to="2025-12-31")]
    assert len(detect_contradictions(rows)) == 1
    assert {x.relationship_id for x in temporal_slice(rows, as_of="2026-08-15")} == {"R1", "R2"}


def test_phase8_learning_is_candidate_only_and_quarantines_invalid():
    doc = {"event_id": "EV1", "title": "Tariff", "event_type": "tariff", "event_date": "2026-08-10",
           "available_at": "2026-08-10", "source_id": "NSE:EV1"}
    invalid = replace(relationship("BAD"), mechanism="")
    out = propose_from_document(doc, analysis_as_of="2026-08-15", candidates=[relationship(), invalid])
    assert len(out["proposed"]) == 1 and len(out["quarantined"]) == 1
    assert out["promotion_allowed"] is False


def test_phase9_ask_tool_and_context_are_read_only():
    plan = plan_tools("Why would rates affect HDFC Bank?", ticker_hint="HDFCBANK")
    assert "GET_CAUSAL_RESEARCH" in {x["name"] for x in plan["tools"]}
    result = build_core_read_executor().execute_sync("GET_CAUSAL_RESEARCH",
        {"entity": "HDFCBANK", "question": "why", "analysis_as_of": "2026-08-15"}, ToolExecutionContext())
    assert result["causal_research"]["execution_eligible"] is False
    assert ask_context(entity="HDFCBANK", analysis_as_of="2026-08-15")["causal_research"]["chains"]


def test_phase10_outcome_learning_requires_evidence_and_does_not_promote():
    out = record_outcome(relationship(), observed_direction="POSITIVE", observation_date="2026-12-31", evidence_ids=("RESULTS:1",))
    assert out.matched and out.confidence_delta > 0 and out.status == "PROPOSED"
    with pytest.raises(ValueError, match="EVIDENCE_REQUIRED"):
        record_outcome(relationship(), observed_direction="POSITIVE", observation_date="2026-12-31", evidence_ids=())
