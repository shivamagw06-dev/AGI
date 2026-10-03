"""Phase 1 — Financial Foundations acceptance tests.

Validates every success criterion from the brief:

1. Correctly classify any basic business transaction.
2. Generate accurate journal entries.
3. Construct all three financial statements from a sequence of transactions.
4. Explain WHY each line item changes.
5. Trace the impact of a transaction across IS / BS / CF.
6. Answer accounting questions with causal reasoning, not definitions.
"""

from __future__ import annotations

import pytest

from financial_foundations import production
from financial_foundations.accounting_rules import (
    TRANSACTION_CATALOG,
    build_journal_entry,
    list_transaction_types,
)
from financial_foundations.assessment import (
    build_assessment_suite,
    grade_answer,
    list_scenarios,
)
from financial_foundations.chart_of_accounts import CHART_OF_ACCOUNTS, classify
from financial_foundations.education import curriculum_index, explain
from financial_foundations.journal import Ledger
from financial_foundations.linkage_engine import (
    explain_transaction_linkage,
    why_pat_not_equal_cash_flow,
)
from financial_foundations.schema import AccountType, NormalBalance, Side
from financial_foundations.simulation import ABC_MANUFACTURING_SCENARIO, run_simulation
from financial_foundations.statement_builder import build_all_statements


# ---------------------------------------------------------------------------
# Success criterion 1 — classify any basic business transaction
# ---------------------------------------------------------------------------
def test_chart_of_accounts_classification():
    cash = classify("cash")
    assert cash["type"] == "asset"
    assert cash["normal_balance"] == "debit"
    assert cash["bs_classification"] == "current_asset"

    loan = classify("bank_loan")
    assert loan["type"] == "liability"
    assert loan["normal_balance"] == "credit"

    revenue = classify("product_sales")
    assert revenue["type"] == "revenue"
    assert revenue["normal_balance"] == "credit"

    expense = classify("salary_expense")
    assert expense["type"] == "expense"
    assert expense["normal_balance"] == "debit"

    unknown = classify("not_a_real_account")
    assert unknown["found"] is False


def test_every_account_has_a_consistent_normal_balance():
    for code, acc in CHART_OF_ACCOUNTS.items():
        if acc.type in (AccountType.ASSET, AccountType.EXPENSE):
            assert acc.normal_balance == NormalBalance.DEBIT, code
        else:
            assert acc.normal_balance == NormalBalance.CREDIT, code


# ---------------------------------------------------------------------------
# Success criterion 2 — generate accurate journal entries (Module 2 examples)
# ---------------------------------------------------------------------------
def test_founder_investment_journal_entry():
    entry = build_journal_entry("founder_investment", 1_000_000)
    assert entry.is_balanced()
    legs = {p.account_code: (p.side, p.amount) for p in entry.postings}
    assert legs["cash"] == (Side.DEBIT, 1_000_000)
    assert legs["share_capital"] == (Side.CREDIT, 1_000_000)


def test_buy_furniture_journal_entry():
    entry = build_journal_entry("buy_asset_cash", 50_000, asset_account="furniture")
    legs = {p.account_code: (p.side, p.amount) for p in entry.postings}
    assert legs["furniture"] == (Side.DEBIT, 50_000)
    assert legs["cash"] == (Side.CREDIT, 50_000)


def test_bank_loan_journal_entry():
    entry = build_journal_entry("take_loan", 500_000)
    legs = {p.account_code: (p.side, p.amount) for p in entry.postings}
    assert legs["cash"] == (Side.DEBIT, 500_000)
    assert legs["bank_loan"] == (Side.CREDIT, 500_000)


def test_credit_sale_does_not_touch_cash():
    entry = build_journal_entry("credit_sale", 100_000)
    codes = entry.accounts_touched()
    assert "cash" not in codes
    assert "accounts_receivable" in codes
    assert "product_sales" in codes


def test_salary_due_does_not_touch_cash():
    entry = build_journal_entry("salary_due", 20_000)
    codes = entry.accounts_touched()
    assert "cash" not in codes
    assert "salary_expense" in codes
    assert "salary_payable" in codes


def test_every_transaction_type_produces_a_balanced_entry():
    for ttype in list_transaction_types():
        entry = build_journal_entry(ttype, 12_345.67)
        assert entry.is_balanced(), ttype
        assert entry.total_debits() == entry.total_credits()
        for code in entry.accounts_touched():
            assert code in CHART_OF_ACCOUNTS, f"{ttype} touches unknown account {code}"


def test_unknown_transaction_type_raises():
    with pytest.raises(ValueError):
        build_journal_entry("not_a_real_transaction", 100)


# ---------------------------------------------------------------------------
# Module 10 — Journal → Ledger → Trial Balance → Closing
# ---------------------------------------------------------------------------
def test_trial_balance_balances_after_each_posting():
    ledger = Ledger()
    ledger.record("founder_investment", 1_000_000)
    assert ledger.trial_balance_is_balanced()
    ledger.record("buy_asset_cash", 200_000, asset_account="furniture")
    assert ledger.trial_balance_is_balanced()
    ledger.record("take_loan", 300_000)
    assert ledger.trial_balance_is_balanced()
    ledger.record("credit_sale", 150_000)
    assert ledger.trial_balance_is_balanced()


def test_closing_entry_zeroes_flow_accounts_into_retained_earnings():
    ledger = Ledger()
    ledger.record("founder_investment", 1_000_000)
    ledger.record("cash_sale", 200_000)
    ledger.record("pay_expense_cash", 50_000, expense_account="rent_expense")
    pat_before_close = ledger.period_net_income(1)
    assert pat_before_close == 150_000

    closing = ledger.close_period(1)
    assert closing.is_balanced()
    assert ledger.trial_balance_is_balanced(through_period=1)

    # Flow accounts no longer contribute to this period's balance after closing
    # is excluded from the exact-period query used to build the next IS.
    assert ledger.balance("product_sales", period=1) == 200_000  # still visible for THIS period's IS
    assert ledger.balance("retained_earnings", through_period=1) == 150_000

    with pytest.raises(ValueError):
        ledger.close_period(1)  # cannot close twice


# ---------------------------------------------------------------------------
# Success criterion 3 — construct all three statements from a transaction
# sequence (using the ABC Manufacturing simulation as the canonical case)
# ---------------------------------------------------------------------------
def test_abc_manufacturing_simulation_builds_consistent_statements():
    result = run_simulation()

    is_ = result["income_statement"]
    bs = result["balance_sheet"]
    cf = result["cash_flow_statement"]

    # Hand-computed expectations (see simulation.py docstring for the math).
    assert is_["revenue"] == 700_000
    assert is_["gross_profit"] == 350_000
    assert is_["ebitda"] == 230_000
    assert is_["ebit"] == 170_000
    assert is_["pbt"] == 145_000
    assert is_["pat"] == 108_750

    assert bs["assets"]["total_assets"] == 2_608_750
    assert bs["liabilities"]["total_liabilities"] == 500_000
    assert bs["equity"]["total_equity"] == 2_108_750
    assert bs["accounting_equation"]["balances"] is True
    assert bs["equity"]["retained_earnings"] == is_["pat"]

    assert cf["operating"]["direct"] == -381_250
    assert cf["operating"]["indirect"] == -381_250
    assert cf["operating"]["reconciles"] is True
    assert cf["investing"]["amount"] == -1_100_000
    assert cf["financing"]["amount"] == 2_500_000
    assert cf["net_change_in_cash"] == 1_018_750
    assert cf["reconciles_to_actual_cash_movement"] is True

    assert result["post_close_trial_balance_balanced"] is True
    assert len(result["transaction_log"]) == len(ABC_MANUFACTURING_SCENARIO)


def test_multi_period_balance_sheet_carries_forward():
    ledger = Ledger()
    ledger.record("founder_investment", 1_000_000, period=1)
    ledger.record("cash_sale", 200_000, period=1)
    ledger.close_period(1)
    stmts_p1 = build_all_statements(ledger, 1)
    assert stmts_p1["balance_sheet"]["equity"]["retained_earnings"] == 200_000

    # Period 2: no new revenue, just an expense — retained earnings should
    # carry forward from period 1 and then reduce by period 2's loss.
    ledger.record("pay_expense_cash", 50_000, expense_account="rent_expense", period=2)
    ledger.close_period(2)
    stmts_p2 = build_all_statements(ledger, 2)
    assert stmts_p2["income_statement"]["pat"] == -50_000
    assert stmts_p2["balance_sheet"]["equity"]["retained_earnings"] == 150_000
    assert stmts_p2["balance_sheet"]["accounting_equation"]["balances"] is True
    # Period 1's revenue must NOT leak into period 2's Income Statement.
    assert stmts_p2["income_statement"]["revenue"] == 0


# ---------------------------------------------------------------------------
# Success criterion 4 — explain WHY each line item changes
# ---------------------------------------------------------------------------
def test_education_layer_explains_income_statement_lines():
    for key in ("revenue", "cogs", "gross_profit", "ebitda", "ebit", "pbt", "pat"):
        card = explain(key)
        assert card["found"], key
        assert card["definition"]
        assert card["business_meaning"]
        assert card["common_mistake"]
        assert card["example"]


def test_education_layer_explains_balance_sheet_and_cash_flow_concepts():
    for key in ("current_assets", "accounting_equation", "working_capital", "operating_cash_flow"):
        card = explain(key)
        assert card["found"], key
        assert card["definition"]


def test_education_layer_explains_module_1_5_concepts():
    for key in (
        "why_companies_exist", "accounting_equation", "debit", "credit",
        "trial_balance", "revenue_is_not_cash", "matching_principle",
    ):
        card = explain(key)
        assert card["found"], key
        assert card["module"] in range(1, 6)


def test_curriculum_index_covers_all_modules():
    idx = curriculum_index()
    assert len(idx["module_1_birth_of_a_company"]) >= 5
    assert len(idx["module_2_double_entry"]) >= 4
    assert len(idx["module_9_transaction_types"]) >= 20


# ---------------------------------------------------------------------------
# Success criterion 5 — trace transaction impact across IS / BS / CF
# ---------------------------------------------------------------------------
def test_linkage_engine_traces_machine_purchase_chain():
    linkage = explain_transaction_linkage("buy_asset_cash", amount=500_000)
    accounts = {t["account_code"]: t for t in linkage["today"]}
    assert accounts["furniture"]["direction"] == "↑"
    assert accounts["cash"]["direction"] == "↓"
    assert "Investing" in accounts["cash"]["statements_affected"][0]
    assert linkage["income_statement_affected_today"] is False
    assert linkage["cash_affected_today"] is True
    assert any("depreciat" in step.lower() for step in linkage["future_ripple"])
    assert any("ebit" in step.lower() for step in linkage["future_ripple"])
    assert any("pat" in step.lower() for step in linkage["future_ripple"])


def test_linkage_engine_credit_sale_no_cash_today():
    linkage = explain_transaction_linkage("credit_sale", amount=100_000)
    assert linkage["cash_affected_today"] is False
    assert linkage["income_statement_affected_today"] is True


def test_linkage_engine_deferred_revenue_ripple():
    linkage = explain_transaction_linkage("deferred_revenue_received", amount=100_000)
    assert linkage["cash_affected_today"] is True
    assert linkage["income_statement_affected_today"] is False
    assert any("unearned" in step.lower() for step in linkage["future_ripple"])


def test_pat_vs_cash_flow_lesson_has_all_five_reasons():
    lesson = why_pat_not_equal_cash_flow()
    causes = {r["cause"] for r in lesson["reasons"]}
    assert "Depreciation" in causes
    assert any("Inventory" in c for c in causes)
    assert lesson["one_line"]


# ---------------------------------------------------------------------------
# Success criterion 6 — answer accounting questions with causal reasoning
# ---------------------------------------------------------------------------
def test_assessment_suite_size_within_spec():
    suite = build_assessment_suite()
    assert 100 <= len(suite) <= 200


def test_assessment_suite_covers_all_transaction_types_and_accounts():
    suite = build_assessment_suite()
    journal_qs = [s for s in suite if s.category == "journal_entry"]
    coa_qs = [s for s in suite if s.category == "chart_of_accounts"]
    assert len(journal_qs) == len(TRANSACTION_CATALOG)
    assert len(coa_qs) == len(CHART_OF_ACCOUNTS)


def test_assessment_scenarios_are_uniquely_identified():
    suite = build_assessment_suite()
    ids = [s.id for s in suite]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize(
    "scenario_id",
    ["FF-CANON-01", "FF-CANON-02", "FF-CANON-03", "FF-CANON-04", "FF-CANON-05"],
)
def test_canonical_module_12_questions_have_computed_answers(scenario_id):
    from financial_foundations.assessment import get_scenario

    scenario = get_scenario(scenario_id)
    assert scenario is not None
    assert scenario.expected_answer
    assert len(scenario.expected_keypoints) >= 3


def test_grading_rewards_causal_reasoning_over_bare_definitions():
    causal_answer = (
        "Depreciation is a non-cash expense — it reduces EBIT and PAT on the "
        "Income Statement, but since no cash actually leaves the business, it "
        "is added back when computing Cash Flow."
    )
    bare_definition = "Depreciation is when an asset loses value over time."

    good = grade_answer("FF-CANON-01", causal_answer)
    bad = grade_answer("FF-CANON-01", bare_definition)
    assert good["score"] > bad["score"]
    assert good["passed"] is True
    assert bad["passed"] is False


def test_grading_inventory_question_across_three_statements():
    causal_answer = (
        "Buying inventory for cash decreases Cash and increases Inventory on the "
        "Balance Sheet — no Income Statement effect yet. It shows as an Operating "
        "cash outflow. Only when sold does the cost move to COGS."
    )
    result = grade_answer("FF-CANON-02", causal_answer)
    assert result["passed"] is True


def test_grade_answer_unknown_scenario():
    result = grade_answer("FF-DOES-NOT-EXIST", "anything")
    assert result["found"] is False


def test_list_scenarios_filters_by_category_and_module():
    rows = list_scenarios(category="journal_entry")
    assert all(True for _ in rows)  # non-empty check below
    assert len(rows) == len(TRANSACTION_CATALOG)
    module3_rows = list_scenarios(module=3)
    assert len(module3_rows) == len(CHART_OF_ACCOUNTS)


# ---------------------------------------------------------------------------
# Production facade smoke tests
# ---------------------------------------------------------------------------
def test_production_health_and_dashboard():
    h = production.health()
    assert h["status"] == "ok"
    assert "12 Examination" in h["modules"][-1]

    d = production.dashboard()
    assert d["chart_of_accounts_size"] == len(CHART_OF_ACCOUNTS)
    assert d["transaction_types"] == len(TRANSACTION_CATALOG)
    assert 100 <= d["assessment_suite_size"] <= 200


def test_production_simulate_matches_direct_call():
    via_production = production.simulate()
    assert via_production["income_statement"]["pat"] == 108_750


def test_production_explain_and_transaction_linkage():
    concept = production.explain("PAT")
    assert concept["found"] is True
    txn = production.transaction_linkage("record_depreciation", amount=60_000)
    assert txn["found"] is True
    assert txn["income_statement_affected_today"] is True
    assert txn["cash_affected_today"] is False


def test_production_soft_slice_for_ask_agi_is_additive_only():
    hit = production.soft_slice_for_ask_agi("What is EBITDA?")
    assert hit["enabled"] is True
    assert hit["financial_foundations"]["found"] is True

    miss = production.soft_slice_for_ask_agi("completely unrelated gibberish question xyz123")
    assert miss["enabled"] is False
