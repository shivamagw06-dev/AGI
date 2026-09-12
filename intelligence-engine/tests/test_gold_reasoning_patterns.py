"""Gold reasoning patterns — train on habits, not rote answers."""

from __future__ import annotations

from institutional_reasoning.gold_patterns import match_pattern, package_pattern_answer
from institutional_reasoning.production import package_for_ask_agi


GOLD_CASES = [
    (
        "t1_profit_vs_roe",
        "HDFC Bank's net profit increased 12%, but Return on Equity (ROE) declined. "
        "Which metric deserves more attention, and why?",
        "ROE deserves closer attention",
    ),
    (
        "t2_revenue_vs_operating_margin",
        "Revenue increased 25%, but operating margin declined. Is this positive or negative?",
        "It depends on what caused the lower margin",
    ),
    (
        "t3_conflicting_pe",
        "Three data providers show different P/E ratios for the same company: 18.4, 21.7 and 25.1. "
        "Which value should AIG trust?",
        "should not automatically choose one value",
    ),
    (
        "t4_news_without_filing",
        "A news article says Infosys won a large contract, but there is no NSE filing yet. "
        "How should AIG treat this?",
        "treated as unverified",
    ),
    (
        "t5_rbi_rate_cut_differential",
        "RBI cuts interest rates. How does this affect HDFC Bank, Bajaj Finance, Infosys and UltraTech?",
        "impact differs across industries",
    ),
    (
        "t6_oil_shock_sectors",
        "Oil rises 40%. Which sectors benefit and which are hurt?",
        "do not affect every sector in the same way",
    ),
    (
        "t7_missing_quarterly_results",
        "The company has not yet published quarterly results. What cannot be concluded?",
        "not sufficient to assess",
    ),
    (
        "t8_ceo_demand_without_results",
        "The CEO says demand remains strong, but no financial results have been released. "
        "How much weight should this carry?",
        "should not be treated as confirmed evidence",
    ),
    (
        "t9_revenue_profit_vs_ocf",
        "Revenue increased, profit increased, but operating cash flow declined. What could explain this?",
        "do not always lead to higher cash generation",
    ),
    (
        "t10_earnings_vs_negative_fcf",
        "A company reports record earnings but negative free cash flow. What should an analyst investigate?",
        "investigate why cash generation is weak",
    ),
    (
        "t11_same_growth_different_roe",
        "Two companies have identical revenue growth. One has ROE of 24% and the other 9%. Which is stronger?",
        "Revenue growth alone is not enough",
    ),
    (
        "t12_price_fall_after_record_profit",
        "A company reports record profit, but the share price falls. Why might that happen?",
        "do not always lead to a higher share price",
    ),
    (
        "t13_challenge_own_conclusion",
        "Argue the strongest possible case that your previous conclusion — that the outlook was improving — "
        "could be wrong.",
        "could be wrong if key assumptions prove incorrect",
    ),
    (
        "t14_list_assumptions",
        "List every assumption in your assessment and describe what future evidence would prove it wrong.",
        "current business trends continue",
    ),
    (
        "t15_five_facts_three_narratives",
        "Given these facts — Revenue +20%, Profit +15%, FCF -30%, Debt +40%, Share Price +35% — "
        "invent three completely different explanations.",
        "Growth Investment",
    ),
]


def test_all_fifteen_gold_patterns_match_and_compose():
    for pattern_id, question, needle in GOLD_CASES:
        matched = match_pattern(question)
        assert matched is not None, f"no match for {pattern_id}"
        assert matched["id"] == pattern_id, f"{pattern_id} got {matched['id']}"
        packaged = package_pattern_answer(question)
        assert packaged["enabled"] is True
        assert packaged["pattern_id"] == pattern_id
        assert packaged["reasoning_habit"].startswith("direct_answer")
        exec_text = packaged["executive"]
        assert needle.lower() in exec_text.lower(), f"{pattern_id} missing needle: {needle}"
        # Golden sequence pieces present when provided
        assert packaged["direct_answer"]
        assert packaged["why"]
        assert packaged["conclusion"]


def test_t15_includes_three_named_narratives():
    q = GOLD_CASES[-1][1]
    text = package_pattern_answer(q)["executive"]
    assert "Growth Investment" in text
    assert "Working Capital Pressure" in text
    assert "Market Expectations" in text


def test_package_owns_executive_for_gold_match():
    q = GOLD_CASES[0][1]
    out = package_for_ask_agi(query=q, ticker="HDFCBANK", company="HDFC Bank")
    assert out["owns_executive"] is True
    assert out["answer_policy"] == "gold_reasoning_pattern"
    assert out["pattern_id"] == "t1_profit_vs_roe"
    assert "ROE" in (out["executive"] or "")


def test_answer_construction_prefers_gold_over_editorial():
    from answer_construction.production import package_for_ask_agi as ac_package

    q = GOLD_CASES[3][1]  # news without filing
    out = ac_package(query=q, ticker="INFY")
    assert out.get("answer_policy") == "gold_reasoning_pattern"
    assert out.get("reasoning_pattern", {}).get("pattern_id") == "t4_news_without_filing"
    assert "unverified" in (out.get("executive") or "").lower()
    # Editorial must not overwrite gold executive
    assert out.get("editorial", {}).get("bypassed") is True


def test_nim_contradiction_uses_gold_pattern_first():
    from answer_construction.production import package_for_ask_agi as ac_package

    q = (
        "HDFC Bank reported higher profits this quarter, but its Net Interest Margin (NIM) "
        "declined. Which signal matters more and why?"
    )
    out = ac_package(query=q, ticker="HDFCBANK")
    assert out.get("answer_policy") == "gold_reasoning_pattern"
    assert out.get("reasoning_pattern", {}).get("pattern_id") == "profit_vs_nim"
    assert "NIM" in (out.get("executive") or "") or "Net Interest Margin" in (out.get("executive") or "")
