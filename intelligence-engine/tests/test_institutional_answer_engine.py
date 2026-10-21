from dataclasses import replace

from causal_research_engine.institutional_answer import compose_cre_sections
from causal_research_engine.reasoning import temporal_slice
from causal_research_engine.retrieval import relevant_subgraph
from causal_research_engine.schema import CausalRelationship, EvidenceReference
from causal_research_engine.service import ask_context


def _row(rid, cause, effect, direction="POSITIVE", confidence=.8, valid_from="2025-01-01", valid_to=None):
    evidence = EvidenceReference(rid + "E", "filing", rid + "S", available_at=valid_from, quality="VALIDATED")
    return CausalRelationship(rid, cause, effect, direction, "DIRECT", "OBSERVATION",
        strength="HIGH", confidence=confidence, time_lag="1_QUARTER",
        mechanism=f"{cause} transmits into {effect}", evidence=(evidence,), source_count=1,
        source_quality="VALIDATED", valid_from=valid_from, valid_to=valid_to, status="VALIDATED")


def test_cfa_answer_has_decision_useful_sections():
    chains = [_row("R1", "deposit growth", "funding mix").to_dict(),
              _row("R2", "funding mix", "NIM").to_dict(),
              _row("R3", "NIM", "ROE").to_dict()]
    out = compose_cre_sections(question="Why is HDFC Bank attractive?", causal_pack={"chains": chains})
    assert out["direct_conclusion"] and len(out["financial_transmission"]) == 3
    assert out["monitoring"] == ["funding mix", "NIM", "ROE"]
    assert out["execution_eligible"] is False
    assert set(out["epistemic_layers"]) == {"evidence", "interpretation", "scenario", "thesis"}
    assert out["decision_relevance"] == "NO_MATERIAL_CHANGE"
    assert all(item["why"] and item["trigger"] for item in out["dynamic_monitoring"])


def test_false_numeric_premise_is_challenged():
    out = compose_cre_sections(question="Market share rose from 12% to 18%. Why?",
        causal_pack={"chains": [_row("R", "market share", "revenue").to_dict()]}, evidence_text="")
    assert out["premise_challenge"] == ["12%", "18%"]
    assert "unverified numeric premise" in out["direct_conclusion"][0]

def test_numeric_what_if_is_a_scenario_not_a_false_premise():
    out = compose_cre_sections(question="What happens if crude rises 20%?",
        causal_pack={"chains": [_row("R", "crude", "inflation").to_dict()]}, evidence_text="")
    assert out["premise_challenge"] == []


def test_insufficient_evidence_fails_closed():
    out = compose_cre_sections(question="Why?", causal_pack={"chains": []})
    assert "Insufficient governed causal evidence" in out["direct_conclusion"][0]
    assert out["confidence"] == "LOW"
    assert out["decision_relevance"] == "INSUFFICIENT_EVIDENCE"


def test_temporal_reasoning_does_not_leak_future_relationships():
    old = _row("OLD", "A", "B", valid_from="2025-01-01", valid_to="2025-06-30")
    future = _row("NEW", "A", "C", valid_from="2025-12-01")
    assert temporal_slice([old, future], as_of="2025-03-31") == [old]
    assert temporal_slice([old, future], as_of="2025-09-30") == []
    assert temporal_slice([old, future], as_of="2025-12-31") == [future]


def test_cross_industry_crude_retrieval_uses_existing_graph():
    graph = relevant_subgraph(["oil"], depth=3)
    paths = {(r.cause, r.effect) for r in graph["relationships"]}
    assert paths and graph["source_graph"] == "AGI_CIG"
    assert len({node.get("type") for node in graph["nodes"]}) >= 2


def test_live_hdfc_context_is_bounded_and_evidenced():
    out = ask_context(entity="HDFCBANK", question="What would improve the thesis?", analysis_as_of="2026-08-15")
    pack = out["causal_research"]
    assert pack["chains"] and len(pack["chains"]) <= 12
    assert all(row["evidence"] for row in pack["chains"])
    assert pack["execution_eligible"] is False
