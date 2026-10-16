"""Contradiction Reasoning soft layer — step-by-step conflict answer tests."""

from __future__ import annotations

from contradiction_reasoning.detector import is_contradiction_query
from contradiction_reasoning.production import health, package_for_ask_agi, quality_gates


T1 = (
    "HDFC Bank reported higher profits this quarter, but its Net Interest Margin (NIM) "
    "declined. Which signal matters more and why?"
)
T2 = "Revenue increased 20%, but free cash flow declined 35%. Explain the contradiction."
T3 = "Management says demand is strong, but sales declined. How should this be interpreted?"


def test_health_soft_wire_not_top_level():
    h = health()
    assert h["not_a_top_level_engine"] is True
    assert h["not_continuous_research_evaluation"] is True
    g = quality_gates()
    assert g["checks"]["step_by_step_reasoning"] is True
    assert g["checks"]["never_jumps_to_certainty"] is True


def test_detector_flags_conflict_queries():
    assert is_contradiction_query(T1) is True
    assert is_contradiction_query(T2) is True
    assert is_contradiction_query(T3) is True
    assert is_contradiction_query("Should I buy HDFC Bank?") is False
    assert is_contradiction_query("How is Infosys performing?") is False


def test_t1_nim_over_profit_institutional_shape():
    out = package_for_ask_agi(query=T1, ticker="HDFCBANK", company="HDFC Bank")
    assert out["enabled"] is True
    assert out["archetype"] == "profit_vs_nim"
    text = out["executive"]
    assert "Net Interest Margin" in text or "NIM" in text
    assert "more important" in text.lower()
    assert "one-time" in text.lower() or "one-off" in text.lower() or "expenses" in text.lower()
    assert "both metrics" in text.lower() or "together" in text.lower()
    assert len(out["possible_explanations"]) >= 2
    assert len(out["missing_evidence"]) >= 2
    assert out["confidence"] in {"medium", "low_to_medium", "low"}
    # Must not jump to buy/sell certainty
    low = text.lower()
    assert "buy" not in low.split()
    assert "sell" not in low.split()


def test_t2_revenue_vs_fcf_avoids_guessing():
    out = package_for_ask_agi(query=T2)
    assert out["enabled"] is True
    assert out["archetype"] == "revenue_vs_fcf"
    text = out["executive"].lower()
    assert "do not always mean more cash" in text or "not always mean more cash" in text
    assert "more evidence" in text or "additional evidence" in text
    assert any("inventory" in e.lower() or "capital" in e.lower() for e in out["possible_explanations"])
    assert "risks outweigh" not in text


def test_t3_management_vs_sales_balanced():
    out = package_for_ask_agi(query=T3, company="HDFC Bank")
    assert out["enabled"] is True
    assert out["archetype"] == "management_vs_sales"
    text = out["executive"].lower()
    assert "financial results" in text or "actual performance" in text
    assert "do not automatically" in text or "additional evidence" in text
    # Does not accuse management of lying
    assert "lying" not in text
    assert "dishonest" not in text
    assert len(out["possible_explanations"]) >= 2


def test_answer_structure_five_parts():
    out = package_for_ask_agi(query=T1)
    struct = out["answer_structure"]
    assert struct["direct_answer"]
    assert struct["why_this_happened"]
    assert len(struct["other_possible_explanations"]) >= 2
    assert len(struct["what_evidence_is_missing"]) >= 2
    assert struct["current_conclusion"]


def test_soft_wire_into_answer_construction():
    from answer_construction.production import package_for_ask_agi as ac_package

    # Gold reasoning patterns take priority over contradiction fallback for known habits.
    out = ac_package(query=T1, ticker="HDFCBANK")
    assert out.get("answer_policy") == "gold_reasoning_pattern"
    assert out.get("reasoning_pattern", {}).get("pattern_id") == "profit_vs_nim"
    assert "NIM" in (out.get("executive") or "") or "Net Interest Margin" in (out.get("executive") or "")
    assert out.get("editorial", {}).get("bypassed") is True

    # Family or contradiction soft layer owns executive when no gold pattern matches.
    generic_q = (
        "Reported assets rose sharply, but liabilities also rose even faster. "
        "How should this be interpreted?"
    )
    out2 = ac_package(query=generic_q, ticker="HDFCBANK")
    assert out2.get("answer_policy") in {
        "contradiction_reasoning_step_by_step",
        "reasoning_family_first_principles",
    }
    assert out2.get("editorial", {}).get("bypassed") is True
    assert out2.get("executive")