"""Academy Validation Suite — demonstrate institutional knowledge."""

from __future__ import annotations

from academy.validation_suite.catalog import all_exams
from academy.validation_suite.memory import reset_memory
from academy.validation_suite.production import (
    dashboard,
    list_exams,
    quality_gates,
    reset_for_tests,
    run_exam,
    run_level,
    run_suite,
)
from academy.books.v3.production import reset_for_tests as reset_v3


def setup_function() -> None:
    reset_for_tests()
    reset_v3()
    reset_memory()


def test_catalog_has_all_eight_levels():
    exams = all_exams()
    levels = {e.level for e in exams}
    assert levels == {1, 2, 3, 4, 5, 6, 7, 8}
    assert len(exams) >= 30
    listed = list_exams()
    assert listed["count"] == len(exams)


def test_level1_concept_recall_roic():
    result = run_exam("l1_roic")
    assert result["passed"] is True
    assert result["level_name"] == "concept_recall"
    assert result["structure"]["definition"]
    assert result["structure"]["when_to_apply"]
    assert result["structure"]["when_not_to_apply"]
    assert result["provenance"]["verbatim_book_quotes"] is False


def test_level1_full():
    block = run_level(1)
    assert block["level_passed"] is True, block.get("results")


def test_level2_hdfc_porter_applies_five_forces():
    result = run_exam("l2_hdfc_porter")
    assert result["passed"] is True
    sections = result["structure"]["sections"]
    forces = {s.get("force") for s in sections}
    assert forces >= {"rivalry", "buyer_power", "supplier_power", "substitutes", "entrants"}
    assert result["structure"]["conclusion"]
    assert result["structure"]["company_specific_evidence"] is True


def test_level3_cross_book_synthesis_hdfc():
    result = run_exam("l3_hdfc_premium")
    assert result["passed"] is True
    authors = {a.lower() for a in result["structure"]["authors_used"]}
    assert {"damodaran", "graham", "fisher"} <= authors
    assert result["structure"]["single_book_only"] is False
    assert result["structure"]["unified_institutional_view"]


def test_level4_case_transfer_eternal():
    result = run_exam("l4_eternal_amazon_groupon")
    assert result["passed"] is True
    assert result["structure"]["analogue"]
    assert result["structure"]["lessons"]


def test_level5_high_roe_counter_examples():
    result = run_exam("l5_high_roe_misleading")
    assert result["passed"] is True
    ex = " ".join(result["structure"]["exceptions"]).lower()
    assert "leverage" in ex
    assert "buyback" in ex
    assert "one-off" in ex or "one off" in ex or "one-off" in ex
    assert "accounting" in ex


def test_level6_analyst_exams_sample():
    for eid in ("l6_ba_apple_moat", "l6_fa_cash_vs_earnings", "l6_va_mos"):
        result = run_exam(eid)
        assert result["passed"] is True, (eid, result.get("criteria"))


def test_level7_memory_hdfc():
    result = run_exam("l7_hdfc_what_changed")
    assert result["passed"] is True
    assert result["structure"]["previous_opinion"]
    assert result["structure"]["updated_opinion"]
    metrics = result["structure"]["metrics"]
    assert metrics.get("loan_growth")
    assert metrics.get("deposit_mix")
    assert metrics.get("nim")
    assert metrics.get("capital")


def test_level8_decision_chain_not_yes_no():
    result = run_exam("l8_invest_hdfc")
    assert result["passed"] is True
    stages = [c["stage"].lower() for c in result["structure"]["chain"]]
    assert "business" in stages[0]
    assert any("financial" in s for s in stages)
    assert any("valuation" in s for s in stages)
    assert any("risk" in s for s in stages)
    assert any("committee" in s for s in stages)
    assert result["structure"]["bare_yes_no"] is False
    answer = result["answer"].lower()
    assert "yes" not in answer[:10]  # not a bare yes opener without chain


def test_full_suite_and_quality_gates():
    suite = run_suite()
    assert suite["suite_passed"] is True, suite.get("failed_exam_ids")
    assert suite["total"] >= 30
    assert suite["pass_rate"] == 1.0
    gates = quality_gates()
    assert gates["passed"] is True, gates
    dash = dashboard()
    assert dash["programme"] == "AGI_ACADEMY_VALIDATION_SUITE"
    assert dash["suite_passed"] is True
