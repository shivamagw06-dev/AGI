"""Phase 3–8 adversarial / unknown reasoning + three-tier benchmarks."""

from __future__ import annotations

from institutional_reasoning.adversarial import detect_adversarial_mode
from institutional_reasoning.engine import package_reasoning_answer
from institutional_reasoning.production import health, package_for_ask_agi


CORE_CASES = [
    (
        "unknown_time_horizons",
        "A company's revenue has grown every year for five years, but it has declined "
        "for the last two quarters. Which trend deserves more weight and why?",
        ["horizons", "temporary"],
    ),
    (
        "unknown_business_vs_valuation",
        "The business continues to improve, but the share price has doubled while earnings "
        "have grown only 15%. How should the business and valuation be assessed separately?",
        ["separate", "valuation"],
    ),
    (
        "unknown_missing_cashflow",
        "The company has not yet released its cash flow statement, but revenue and profit "
        "have both increased. What conclusions can and cannot be drawn?",
        ["cannot", "cash"],
    ),
    (
        "cross_family_macro_sector",
        "Inflation is rising, the RBI increases interest rates, oil prices fall, and the "
        "rupee strengthens. How could these developments affect an airline, a private bank "
        "and an IT exporter differently?",
        ["airline", "bank", "decompos"],
    ),
    (
        "cross_family_dual_hypothesis",
        "Revenue increased, profit declined, debt fell, free cash flow improved and the "
        "share price rose. Construct two competing explanations and identify the evidence "
        "needed to distinguish between them.",
        ["explanation 1", "explanation 2", "distinguish"],
    ),
    (
        "self_critique_assumptions",
        "After reaching your conclusion, list the three assumptions that have the greatest "
        "influence on it. For each assumption, explain what future evidence would invalidate it.",
        ["assumption 1", "assumption 2", "assumption 3"],
    ),
    (
        "self_critique_steelman",
        "If another analyst disagreed with your conclusion, what is the strongest evidence "
        "they could use to support the opposite view?",
        ["opposite", "evidence"],
    ),
    (
        "evidence_hierarchy_sources",
        "You have a company press release, an NSE filing, a Reuters article, a social media "
        "post and an investor presentation. One source claims a major acquisition, the others "
        "do not. How should AIG evaluate the evidence before updating its assessment?",
        ["nse", "filing", "authoritative"],
    ),
    (
        "unknown_company_accounting",
        "ABC Manufacturing reported: Revenue +18%, Profit +5%, Inventory +42%, "
        "Receivables +38%, Debt unchanged, Share price +12%. No prior knowledge should be "
        "needed. What does this imply about earnings quality and cash conversion?",
        ["inventory", "receivables"],
    ),
]


def test_health_exposes_adversarial_layer():
    assert health()["adversarial_unknown_reasoning"] is True


def test_phase3_to_7_core_modes():
    for mode, question, needles in CORE_CASES:
        detected = detect_adversarial_mode(question)
        assert detected is not None, question
        assert detected["mode"] == mode, f"{mode} got {detected}"
        out = package_reasoning_answer(question)
        assert out["owns_executive"] is True
        assert out["source"] == "adversarial_unknown_reasoning"
        assert out["mode"] == mode
        assert out["novelty"]["force_closest_template"] is False
        assert float(out["novelty"]["novelty_score"]) >= 0.5
        text = (out["executive"] or "").lower()
        for n in needles:
            assert n.lower() in text, f"{mode} missing {n}: {text[:180]}"


def test_dual_hypothesis_does_not_decide():
    q = CORE_CASES[4][1]
    out = package_reasoning_answer(q)
    assert out["decides_winner"] is False
    assert "do not decide" in (out["executive"] or "").lower()


def test_macro_sector_decomposes():
    out = package_reasoning_answer(CORE_CASES[3][1])
    dec = out.get("structured", {}).get("decomposed") or out.get("decomposed")
    assert dec
    assert "airline" in (dec.get("sectors") or [])
    text = (out["executive"] or "").lower()
    assert "airline" in text and "bank" in text and "exporter" in text


def test_phase8_consistency_across_paraphrases():
    paraphrases = [
        "Why did free cash flow fall despite higher revenue?",
        "Explain why cash generation weakened even though sales improved.",
        "Revenue rose but cash fell. Why?",
    ]
    packs = [package_reasoning_answer(q) for q in paraphrases]
    assert all(p["mode"] == "consistency_cash_vs_revenue" for p in packs)
    fingerprints = {p["consistency_fingerprint"] for p in packs}
    habits = {p["habit_id"] for p in packs}
    assert len(fingerprints) == 1
    assert habits == {"habit_revenue_up_cash_down"}
    # Core claim stable
    claims = {(p.get("structured") or {}).get("core_claim") for p in packs}
    assert claims == {"revenue_up_does_not_imply_cash_up"}


def test_ask_agi_package_surfaces_adversarial_mode():
    out = package_for_ask_agi(query=CORE_CASES[1][1])
    assert out["owns_executive"] is True
    assert out["adversarial_mode"] == "unknown_business_vs_valuation"
    assert out["habit_id"] == "habit_business_vs_valuation"


def test_answer_construction_soft_wire_adversarial():
    from answer_construction.production import package_for_ask_agi as ac_package

    out = ac_package(query=CORE_CASES[7][1])
    assert str(out.get("answer_policy", "")).startswith("adversarial_")
    assert out.get("editorial", {}).get("bypassed") is True
    assert "filing" in (out.get("executive") or "").lower()


def test_adversarial_bank_never_train_and_isolated():
    from evals.adversarial_chaos_held_out import ADVERSARIAL_BANK, EVALUATION_ONLY, NEVER_TRAIN
    import institutional_reasoning.adversarial as adv
    import institutional_reasoning.gold_patterns as gp

    assert NEVER_TRAIN is True
    assert EVALUATION_ONLY is True
    assert len(ADVERSARIAL_BANK) >= 12
    for mod in (adv, gp):
        src = open(mod.__file__, encoding="utf-8").read()
        assert "adversarial_chaos_held_out" not in src
        assert "A01" not in src


def test_three_tier_scorecard_runs():
    from evals.three_tier_scorecard import run_three_tier_scorecard

    report = run_three_tier_scorecard()
    assert "claim_discipline" in report
    assert report["benchmarks"]["gold_patterns"]["score_per_100"] == 100.0
    adv = report["benchmarks"]["adversarial_chaos"]
    assert adv["never_train"] is True
    assert adv["score_per_100"] >= 85.0
    assert "perfect_on_this_adversarial_set" in adv["interpretation"] or "strong_on_this_adversarial_set" in adv[
        "interpretation"
    ]
    # Softened Phase-2 language — no unbounded genuine_reasoning claim.
    hidden = report["benchmarks"]["hidden_generalisation"]
    assert "genuine_reasoning" not in hidden["interpretation"]
    assert "held_out" in hidden["interpretation"]


def test_adversarial_core_scorecard_all_pass():
    from evals.three_tier_scorecard import score_adversarial_tier

    result = score_adversarial_tier(core_only=True)
    assert result["failures"] == [], result["failures"]
    assert result["consistency_group_ok"] is True
