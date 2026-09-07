"""Institutional Reasoning Soft Policy — think-before-answer tests."""

from __future__ import annotations

from institutional_reasoning.planner import build_reasoning_plan, classify_question_type
from institutional_reasoning.production import health, package_for_ask_agi, quality_gates, system_prompt
from institutional_reasoning.prompt import TOP_RULE


def test_health_and_gates():
    h = health()
    assert h["not_a_top_level_engine"] is True
    assert "evidence" in (h.get("top_rule") or "").lower()
    g = quality_gates()
    assert g["checks"]["evidence_before_conclusions"] is True
    assert g["checks"]["nine_step_reasoning_chain"] is True


def test_top_rule_in_system_prompt():
    prompt = system_prompt()
    assert TOP_RULE in prompt
    assert "What evidence would I need to justify every sentence" in prompt
    assert "Never reverse this order" in prompt
    assert "STEP 1 — UNDERSTAND THE QUESTION" in prompt
    assert "STEP 9 — ANSWER THE USER" in prompt


def test_classify_contradiction_and_company():
    assert classify_question_type(
        "HDFC Bank reported higher profits, but NIM declined. Which signal matters more?"
    ) == "Contradiction"
    assert classify_question_type("Should I buy HDFC Bank?") == "Company Analysis"
    assert classify_question_type("What is free cash flow?") in {"Education", "Financial Analysis", "Economic Concept"}


def test_reasoning_plan_for_hdfc_buy_question():
    plan = build_reasoning_plan("Should I buy HDFC Bank?", ticker="HDFCBANK", company="HDFC Bank")
    assert plan["enabled"] is True
    assert plan["top_rule"] == TOP_RULE
    u = plan["question_understanding"]
    assert u["company"] == "HDFC Bank"
    assert u["ticker"] == "HDFCBANK"
    assert u["question_type"] == "Company Analysis"
    assert "assessment" in (plan["main_question"] or "").lower()
    assert plan["internal_assessment"]["remains_internal"] is True
    assert plan["answer_structure"][0] == "direct_answer"
    assert plan["answer_policy"] == "evidence_then_reason_then_communicate"
    assert len(plan["reasoning_steps"]) == 9


def test_contradiction_plan_flags_protocol():
    plan = build_reasoning_plan(
        "Revenue increased 20%, but free cash flow declined 35%. Explain the contradiction."
    )
    assert plan["question_understanding"]["question_type"] == "Contradiction"
    assert plan["contradiction_protocol_required"] is True


def test_package_for_ask_agi_includes_system_prompt():
    out = package_for_ask_agi(query="Should I buy HDFC Bank?", ticker="HDFCBANK")
    assert out["enabled"] is True
    assert out["system_prompt_chars"] > 500
    assert "Buy, Sell, Hold" in out["system_prompt"] or "Never give Buy" in out["system_prompt"]


def test_soft_wire_into_answer_construction():
    from answer_construction.production import package_for_ask_agi as ac_package

    out = ac_package(query="Should I buy HDFC Bank?", ticker="HDFCBANK")
    assert out.get("institutional_reasoning", {}).get("enabled") is True
    assert out.get("reasoning_plan", {}).get("top_rule")
    assert out.get("reasoning_plan", {}).get("question_type") == "Company Analysis"


def test_gold_reasoning_pattern_owns_executive_with_reasoning_plan():
    from answer_construction.production import package_for_ask_agi as ac_package

    q = (
        "HDFC Bank reported higher profits this quarter, but its Net Interest Margin (NIM) "
        "declined. Which signal matters more and why?"
    )
    out = ac_package(query=q, ticker="HDFCBANK")
    assert out.get("institutional_reasoning", {}).get("enabled") is True
    assert out.get("answer_policy") == "gold_reasoning_pattern"
    assert out.get("reasoning_pattern", {}).get("pattern_id") == "profit_vs_nim"
    assert "NIM" in (out.get("executive") or "") or "Net Interest Margin" in (out.get("executive") or "")
    assert out.get("editorial", {}).get("bypassed") is True