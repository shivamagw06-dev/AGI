"""Financial Foundations — production facade.

Soft-wire only. This package does not touch retrieval, Ask, or
valuation — it is a standalone accounting-intelligence engine that later
capabilities (financial analysis, valuation, forecasting) will build on.
"""

from __future__ import annotations

from typing import Any, Optional

from financial_foundations import education
from financial_foundations.accounting_rules import explain_rule, list_transaction_types
from financial_foundations.assessment import (
    build_assessment_suite,
    get_scenario,
    grade_answer,
    list_scenarios,
)
from financial_foundations.chart_of_accounts import classify, list_chart
from financial_foundations.journal import Ledger
from financial_foundations.linkage_engine import explain_transaction_linkage, why_pat_not_equal_cash_flow
from financial_foundations.schema import FF_VERSION, FREEZE_LOCKS, PROGRAMME, RELEASE_STATUS
from financial_foundations.simulation import run_simulation
from financial_foundations.statement_builder import build_all_statements


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "ff_version": FF_VERSION,
        "freeze_locks": FREEZE_LOCKS,
        "release_status": RELEASE_STATUS,
        "api_prefix": "/v1/financial-foundations",
        "modules": [
            "1 Birth of a Company", "2 Double Entry Accounting", "3 Chart of Accounts",
            "4 Revenue Recognition", "5 Expense Recognition", "6 Income Statement",
            "7 Balance Sheet", "8 Cash Flow Statement", "9 Three Statement Linkage",
            "10 Financial Closing", "11 Business Simulation", "12 Examination",
        ],
        "fabricated": False,
    }


def dashboard() -> dict[str, Any]:
    suite = build_assessment_suite()
    return {
        "ff_version": FF_VERSION,
        "chart_of_accounts_size": len(list_chart()),
        "transaction_types": len(list_transaction_types()),
        "concepts": len(education.list_all_concepts()),
        "assessment_suite_size": len(suite),
        "assessment_categories": sorted({s.category for s in suite}),
        "fabricated": False,
    }


def curriculum() -> dict[str, Any]:
    return education.curriculum_index()


def explain(topic: str, *, amount: float = 100_000.0) -> dict[str, Any]:
    return education.explain(topic, amount=amount)


def chart_of_accounts() -> dict[str, Any]:
    return {"n": len(list_chart()), "accounts": list_chart(), "fabricated": False}


def classify_account(code: str) -> dict[str, Any]:
    return classify(code)


def transaction_rule(transaction_type: str) -> dict[str, Any]:
    return explain_rule(transaction_type)


def transaction_linkage(transaction_type: str, *, amount: float = 100_000.0) -> dict[str, Any]:
    return explain_transaction_linkage(transaction_type, amount=amount)


def pat_vs_cash_flow_lesson() -> dict[str, Any]:
    return why_pat_not_equal_cash_flow()


def simulate(*, period: int = 1) -> dict[str, Any]:
    return run_simulation(period=period)


def build_statements_for_ledger(ledger: Ledger, period: int) -> dict[str, Any]:
    """Escape hatch for callers who build their own transaction sequence."""
    return build_all_statements(ledger, period)


def assessment_list(*, category: Optional[str] = None, module: Optional[int] = None) -> dict[str, Any]:
    rows = list_scenarios(category=category, module=module)
    return {"n": len(rows), "scenarios": rows, "fabricated": False}


def assessment_get(scenario_id: str) -> dict[str, Any]:
    scenario = get_scenario(scenario_id)
    if not scenario:
        return {"found": False, "scenario_id": scenario_id}
    return {
        "found": True,
        "id": scenario.id,
        "module": scenario.module,
        "category": scenario.category,
        "question": scenario.question,
    }


def assessment_grade(scenario_id: str, candidate_answer: str) -> dict[str, Any]:
    return grade_answer(scenario_id, candidate_answer)


def soft_slice_for_ask_agi(question: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Non-invasive Ask soft-wire: surface a concept/transaction explanation
    when the question matches Phase 1 vocabulary. Never overrides Ask's
    executive — purely additive context, consumed only if a caller opts in.
    """
    result = education.explain(question)
    if not result.get("found"):
        return {"enabled": False}
    return {"enabled": True, "financial_foundations": result}
