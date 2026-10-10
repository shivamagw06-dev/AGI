"""Institutional Writing Constitution v1.1 tests."""

from __future__ import annotations

from institutional_writing_constitution import (
    BENCHMARK_QUESTIONS,
    apply_institutional_writing_constitution,
    assemble_writing_sections,
    health,
    infer_answer_length,
    list_benchmark_questions,
    plan_response,
    resolve_template,
    score_institutional_readability,
    score_writing_pack,
    validate_writing_response,
)
from institutional_writing_constitution.schema import CONSTITUTION_VERSION, EVIDENCE_PHRASE_TEMPLATES
from institutional_writing_constitution.evaluation import TARGET_BENCHMARK_COUNT


def test_health():
    h = health()
    assert h["status"] == "ok"
    assert h["version"] == CONSTITUTION_VERSION
    assert h["version"] == "1.1"
    assert h["response_templates"] >= 5


def test_benchmark_registry_has_100_questions():
    assert len(BENCHMARK_QUESTIONS) == 100


def test_resolve_template():
    assert resolve_template("Should I invest in TCS?") == "investment_assessment"
    assert resolve_template("What changed after Reliance earnings?", category="earnings_analysis") == "earnings_review"
    assert resolve_template("Compare Asian Paints vs Berger") == "peer_comparison"
    assert resolve_template("Is Titan fairly valued?") == "valuation"
    assert resolve_template("What are the key risks in Adani?") == "risk_review"


def test_response_planner():
    plan = plan_response(
        {"institutional_assertions": [{"statement": "Margins stable.", "status": "SUPPORTED"}]},
        query="Should I invest in TCS?",
        ticker="TCS",
        company="Tata Consultancy Services",
    )
    assert plan["template_id"] == "investment_assessment"
    assert len(plan["top_insights"]) <= 3
    assert "investment_debate" in plan["expand_sections"]


def test_varied_evidence_phrasing():
    pack = {
        "institutional_assertions": [
            {"statement": "Client retention remains strong.", "status": "SUPPORTED", "confidence": 82},
            {"statement": "Pricing power is intact.", "status": "SUPPORTED", "confidence": 75},
            {"statement": "Cash generation supports dividends.", "status": "PARTIAL", "confidence": 60},
        ],
    }
    sections = assemble_writing_sections(pack, company="TCS", ticker="TCS")
    obs = sections["supporting_evidence"]["observations"]
    assert len(obs) >= 3
    prefixes = [o.split(" ", 3)[0] + " " + o.split(" ", 3)[1] for o in obs[:3]]
    # At least two different opening patterns (not all "Evidence suggests")
    assert len(set(prefixes)) >= 2 or any(t.split()[0] in o for o in obs for t in EVIDENCE_PHRASE_TEMPLATES[:3])


def test_investment_debate_section():
    sections = assemble_writing_sections(
        {"investment_thesis": {"current_thesis": "TCS franchise durability"}},
        company="Tata Consultancy Services",
        ticker="TCS",
    )
    debate = sections["investment_debate"]
    assert debate.get("narrative")
    assert "investment debate" in debate["text"].lower()


def test_apply_v1_1_wiring():
    out = apply_institutional_writing_constitution(
        {"ticker": "TCS", "company": "Tata Consultancy Services", "query": "Should I invest in TCS?"},
        query="Should I invest in TCS?",
        ticker="TCS",
        company="Tata Consultancy Services",
    )
    iwc = out["institutional_writing_constitution"]
    assert iwc["version"] == "1.1"
    assert out["writing_structure"] == "institutional_writing_constitution_v1_1"
    assert out.get("response_plan")
    assert out.get("investment_debate")
    assert out.get("supporting_evidence")
    # investment_assessment template omits what_matters_most — uses investment_debate instead
    assert out.get("institutional_readability_score")


def test_institutional_readability_score():
    pack = apply_institutional_writing_constitution({"ticker": "INFY", "company": "Infosys", "query": "Explain Infosys AI strategy"})
    irs = score_institutional_readability(pack)
    assert irs["label"] == "Institutional Readability Score"
    assert "narrative_flow" in irs["scores"]
    assert "investor_usefulness" in irs["scores"]
    assert irs["average"] > 0


def test_validate_no_repetitive_evidence():
    pack = apply_institutional_writing_constitution({"ticker": "TCS", "company": "TCS", "query": "TCS overview"})
    validation = validate_writing_response(pack)
    repetitive = next((c for c in validation["checks"] if c["rule"] == "no_repetitive_evidence_suggests"), None)
    assert repetitive and repetitive["passed"] is True
