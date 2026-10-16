from dataclasses import replace

from causal_research_engine import (
    CausalRelationship, ContradictionGroup, EvidenceReference, FinancialImpact,
    from_cig_edge, from_ieri_relationship, transition_status,
    validate_financial_impact, validate_relationship,
)
from causal_research_engine.validation import validate_contradiction


def evidence(**changes):
    base = dict(evidence_id="ev-1", source_type="company_filing", source_id="filing-1", available_at="2026-05-01", quality="VALIDATED", authority_rank=2)
    base.update(changes)
    return EvidenceReference(**base)


def relationship(**changes):
    base = dict(relationship_id="rel-1", cause="tariff_increase", effect="arpu", direction="POSITIVE", relationship_type="CONDITIONAL", epistemic_label="CAUSAL_INTERPRETATION", industry="telecom", strength="HIGH", confidence=.78, time_lag="1_QUARTER", conditions=("retention remains adequate",), mechanism="Higher realized price lifts revenue per user", evidence=(evidence(),), source_count=1, source_quality="VALIDATED", status="PROPOSED")
    base.update(changes)
    return CausalRelationship(**base)


def test_relationship_contract_and_pit_pass():
    out = validate_relationship(relationship(), analysis_as_of="2026-08-15")
    assert out["ok"] is True


def test_future_evidence_is_rejected():
    row = relationship(evidence=(evidence(available_at="2026-09-01"),))
    assert "POINT_IN_TIME_VIOLATION" in validate_relationship(row, analysis_as_of="2026-08-15")["errors"]


def test_unsupported_relationship_without_evidence_is_only_hypothesis():
    invalid = relationship(evidence=(), source_count=0)
    assert "EVIDENCE_REQUIRED" in validate_relationship(invalid)["errors"]
    hypothesis = relationship(evidence=(), source_count=0, relationship_type="CAUSAL_HYPOTHESIS", epistemic_label="HYPOTHESIS", mechanism="")
    out = validate_relationship(hypothesis)
    assert out["ok"] is True
    assert "HYPOTHESIS_WITHOUT_EVIDENCE" in out["warnings"]


def test_model_cannot_validate_or_trust_its_own_candidate():
    out = transition_status(relationship(), "VALIDATED", actor_type="model", actor_id="openai")
    assert out["status"] == "MODEL_APPROVAL_FORBIDDEN"


def test_authorized_validation_creates_version_not_mutation():
    original = relationship()
    out = transition_status(original, "VALIDATED", actor_type="validator", actor_id="cre-validator")
    assert out["ok"] is True
    assert original.status == "PROPOSED"
    assert out["relationship"].status == "VALIDATED"
    assert out["relationship"].parent_relationship_id == original.relationship_id


def test_trusted_requires_validated_sources():
    row = replace(relationship(status="VALIDATED"), evidence=(evidence(quality="UNVALIDATED"),), source_quality="UNVALIDATED")
    out = transition_status(row, "TRUSTED", actor_type="human", actor_id="research-head")
    assert out["status"] == "VALIDATION_FAILED"


def test_contradiction_requires_two_relationships_and_resolution_text():
    bad = ContradictionGroup("cg-1", ("r1",), ("e1",))
    assert validate_contradiction(bad)["ok"] is False
    unresolved = ContradictionGroup("cg-2", ("r1", "r2"), ("e1", "e2"))
    assert validate_contradiction(unresolved)["ok"] is True


def test_financial_scenario_is_not_fact_and_requires_assumptions():
    bad = FinancialImpact("i1", "BHARTIARTL", "evt1", "revenue", "POSITIVE", "SCENARIO", estimated_change=7.2, unit="percent", period="FY2027", scenario="BASE")
    assert "ASSUMPTIONS_REQUIRED" in validate_financial_impact(bad)["errors"]
    good = replace(bad, assumptions=("tariff realization is 8%",))
    assert validate_financial_impact(good)["ok"] is True


def test_calculation_requires_afe_trace():
    impact = FinancialImpact("i2", "HDFCBANK", "evt2", "roe", "POSITIVE", "CALCULATION", calculation_id="ROE")
    assert "AFE_RESULT_REQUIRED" in validate_financial_impact(impact)["errors"]


def test_existing_cig_edge_adapts_with_provenance():
    edge = {"source": "tariff", "target": "arpu", "relation": "sector_transmission", "direction_sign": 1, "strength": .8, "confidence": .85, "validated": True, "evidence": [{"kind": "sector_model", "source": "industry_intelligence", "note": "Tariff realization can lift ARPU"}]}
    row = from_cig_edge(edge, industry="telecom")
    assert row.status == "VALIDATED"
    assert validate_relationship(row)["ok"] is True


def test_ieri_adapter_preserves_pit_and_stays_proposed_when_pending():
    raw = {"relationship_id": "REL-1", "source_entity": "repo_rate", "target_entity": "funding_cost", "relationship_type": "macro", "direction": "outbound", "strength": "moderate", "confidence": .7, "evidence": ["RBI transmission observation"], "source": "rbi", "available_from": "2025-04-01", "effective_date": "2025-03-31", "semantics": "rate increase raises funding cost", "validation": {"status": "pending"}}
    row = from_ieri_relationship(raw)
    assert row.status == "PROPOSED"
    assert row.valid_from == "2025-04-01"
