"""Phase-2 reasoning families + novelty + held-out generalisation."""

from __future__ import annotations

from institutional_reasoning.engine import package_reasoning_answer
from institutional_reasoning.families import FAMILIES
from institutional_reasoning.family_classifier import classify_family
from institutional_reasoning.novelty import score_novelty
from institutional_reasoning.production import health, package_for_ask_agi, quality_gates


PHASE2_GENERALISATION = [
    (
        "contradiction",
        "Deposits increased 18%, but CASA ratio declined. Which signal is more important?",
        ["casa", "funding"],
    ),
    (
        "accounting",
        "Loan growth accelerated, but provisions doubled. What does this suggest?",
        ["provision", "credit"],
    ),
    (
        "accounting",
        "Production increased 25%, but inventory increased 40%. What could explain this?",
        ["inventory"],
    ),
    (
        "accounting",
        "Sales increased, but receivables increased twice as fast. What questions should an analyst ask?",
        ["receivables"],
    ),
    (
        "contradiction",
        "Revenue grew 30%, but customer growth slowed. Can both be true?",
        ["yes"],
    ),
    (
        "causality",
        "Inflation falls but bond yields rise. Explain three possible reasons.",
        ["yield"],
    ),
    (
        "valuation",
        "Earnings increased 20%, but the P/E ratio fell. Explain how both can happen.",
        ["p/e", "price"],
    ),
]


def test_families_catalog_complete():
    assert len(FAMILIES) >= 8
    assert "contradiction" in FAMILIES
    assert "dual_hypothesis" in FAMILIES


def test_health_exposes_families_and_novelty():
    h = health()
    assert h["reasoning_families"] is True
    assert h["novelty_score"] is True
    g = quality_gates()
    assert g["checks"]["never_force_closest_template_on_novel"] is True


def test_phase2_generalisation_uses_family_not_forced_gold_id():
    for family, question, needles in PHASE2_GENERALISATION:
        out = package_reasoning_answer(question)
        assert out["owns_executive"] is True, question
        assert out["source"] == "reasoning_family", question
        assert out["family_id"] == family, f"{question} -> {out.get('family_id')}"
        assert out["novelty"]["band"] in {"same_family_new_facts", "first_principles", "hard_unseen"}
        assert out["novelty"]["force_closest_template"] is False
        text = (out["executive"] or "").lower()
        for n in needles:
            assert n.lower() in text, f"{question} missing {n}"


def test_gold_exact_still_works_with_low_novelty():
    q = (
        "HDFC Bank's net profit increased 12%, but Return on Equity (ROE) declined. "
        "Which metric deserves more attention, and why?"
    )
    out = package_reasoning_answer(q)
    assert out["source"] == "gold_pattern"
    assert out["novelty"]["band"] == "seen_exact"
    assert out["novelty"]["novelty_score"] <= 0.25
    assert "ROE" in (out["executive"] or "")


def test_hardest_dual_hypothesis_benchmark():
    q = (
        "A company's revenue, profit, free cash flow, inventory, debt and share price all "
        "moved in different directions. Produce two equally plausible explanations, explain "
        "what evidence supports each, what evidence contradicts each, and what additional "
        "information would allow you to distinguish between them. Do not decide which "
        "explanation is correct."
    )
    out = package_reasoning_answer(q)
    assert out["family_id"] == "dual_hypothesis"
    assert out["owns_executive"] is True
    assert out["decides_winner"] is False
    assert out["novelty"]["novelty_score"] >= 0.9
    text = (out["executive"] or "").lower()
    assert "explanation 1" in text and "explanation 2" in text
    assert "supports" in text
    assert "distinguish" in text
    assert "do not decide" in text or "hold both" in text
    assert "the correct explanation is" not in text


def test_ask_agi_package_attaches_novelty_and_family():
    out = package_for_ask_agi(
        query="Deposits increased 18%, but CASA ratio declined. Which signal is more important?"
    )
    assert out["owns_executive"] is True
    assert out["family_id"] == "contradiction"
    assert out["novelty"]["guidance"] in {
        "use_reasoning_family",
        "reason_from_first_principles",
    }
    assert out["answer_policy"] == "reasoning_family_first_principles"


def test_answer_construction_soft_wire_family_owns_executive():
    from answer_construction.production import package_for_ask_agi as ac_package

    q = "Earnings increased 20%, but the P/E ratio fell. Explain how both can happen."
    out = ac_package(query=q)
    assert out.get("answer_policy") == "reasoning_family_first_principles"
    assert out.get("reasoning_family", {}).get("family_id") == "valuation"
    assert out.get("novelty", {}).get("force_closest_template") is False
    assert "p/e" in (out.get("executive") or "").lower()
    assert out.get("editorial", {}).get("bypassed") is True


def test_held_out_bank_never_imported_by_matchers():
    import institutional_reasoning.gold_patterns as gp
    import institutional_reasoning.family_composers as fc
    import institutional_reasoning.family_classifier as cl

    for mod in (gp, fc, cl):
        src = open(mod.__file__, encoding="utf-8").read()
        assert "reasoning_phase2_held_out" not in src
        assert "EVAL_BANK" not in src


def test_phase2_scorecard_core_examples_pass():
    """Score the hand-authored core held-out set (not the full 100 in unit CI time)."""
    from evals.phase2_scorecard import score_item
    from evals.reasoning_phase2_held_out import HELD_OUT

    failures = []
    for item in HELD_OUT:
        packaged = package_reasoning_answer(item["question"])
        row = score_item(item, packaged)
        if not row["passed"]:
            failures.append(row)
    assert not failures, failures


def test_novelty_unclassified_does_not_force_template():
    n = score_novelty(
        gold_exact=False,
        family_id=None,
        family_confidence=0.0,
        first_principles=False,
    )
    assert n["force_closest_template"] is False
    assert n["novelty_score"] == 1.0


def test_classifier_maps_phase2_prompts():
    assert classify_family(PHASE2_GENERALISATION[0][1])["family_id"] == "contradiction"
    assert classify_family(PHASE2_GENERALISATION[1][1])["family_id"] == "accounting"
    assert classify_family(PHASE2_GENERALISATION[5][1])["family_id"] == "causality"
