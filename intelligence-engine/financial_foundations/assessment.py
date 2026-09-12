"""Assessment Suite — Module 12 (Examination).

100-200 scenario-based questions that verify CAUSAL understanding, not
memorised definitions. Every generated question's expected key-points
are computed from the same deterministic engines used everywhere else
in this package (accounting_rules, linkage_engine, chart_of_accounts) —
so the answer key can never drift from the engine's actual behaviour.

``grade_answer`` is a heuristic, deterministic, keyword-presence grader
(no LLM) — consistent with the rest of Phase 1 being free of invented
reasoning.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from financial_foundations.accounting_rules import TRANSACTION_CATALOG, build_journal_entry
from financial_foundations.chart_of_accounts import CHART_OF_ACCOUNTS
from financial_foundations.linkage_engine import FUTURE_RIPPLES, explain_transaction_linkage, why_pat_not_equal_cash_flow
from financial_foundations.schema import Side


@dataclass
class Scenario:
    id: str
    module: int
    category: str
    question: str
    expected_answer: str
    expected_keypoints: list[str] = field(default_factory=list)
    reference: dict[str, Any] = field(default_factory=dict)


_DEMO_AMOUNT = 100_000.0


def _fmt(n: float) -> str:
    return f"₹{n:,.0f}"


# ---------------------------------------------------------------------------
# Canonical Module 12 questions (asked verbatim in the brief)
# ---------------------------------------------------------------------------
def _canonical_scenarios() -> list[Scenario]:
    pat_cf = why_pat_not_equal_cash_flow()
    dep_linkage = explain_transaction_linkage("record_depreciation", amount=_DEMO_AMOUNT)
    inv_linkage = explain_transaction_linkage("purchase_inventory_cash", amount=_DEMO_AMOUNT)
    loan_linkage = explain_transaction_linkage("take_loan", amount=_DEMO_AMOUNT)
    credit_linkage = explain_transaction_linkage("credit_sale", amount=_DEMO_AMOUNT)

    return [
        Scenario(
            id="FF-CANON-01",
            module=9,
            category="canonical",
            question="Why does depreciation reduce PAT but not Cash Flow?",
            expected_answer=(
                "Depreciation is a non-cash expense: it reduces EBIT and therefore PAT, but "
                "no cash actually leaves the business when it is recorded — the cash outflow "
                "already happened when the asset was purchased. Because of this, Depreciation "
                "is added back to PAT when computing Operating Cash Flow."
            ),
            expected_keypoints=[
                "non-cash", "reduces pat", "added back", "cash flow", "ebit",
            ],
            reference=dep_linkage,
        ),
        Scenario(
            id="FF-CANON-02",
            module=9,
            category="canonical",
            question="How does buying inventory affect all three statements?",
            expected_answer=(
                "Buying inventory for cash has NO Income Statement effect — it exchanges one "
                "asset (Cash) for another (Inventory) on the Balance Sheet. On the Cash Flow "
                "Statement it is an Operating outflow. Only later, when the inventory is sold, "
                "does its cost move to COGS on the Income Statement, reducing Gross Profit and PAT."
            ),
            expected_keypoints=[
                "balance sheet", "cash decreases", "inventory increases", "no income statement",
                "cogs", "when sold",
            ],
            reference=inv_linkage,
        ),
        Scenario(
            id="FF-CANON-03",
            module=9,
            category="canonical",
            question="Why does raising debt increase cash without increasing revenue?",
            expected_answer=(
                "Borrowing creates an obligation to repay — it is a Financing cash inflow and "
                "a Liability (Bank Loan) increase, not value earned from operations. Revenue "
                "is only recognised when goods/services are delivered to a customer; a loan "
                "involves no such delivery, so it can never be Revenue."
            ),
            expected_keypoints=[
                "liability", "financing", "not revenue", "must be repaid", "no delivery",
            ],
            reference=loan_linkage,
        ),
        Scenario(
            id="FF-CANON-04",
            module=8,
            category="canonical",
            question="Why can PAT rise while Operating Cash Flow falls?",
            expected_answer=pat_cf["one_line"],
            expected_keypoints=[
                "working capital", "receivable", "inventory", "non-cash", "depreciation",
            ],
            reference=pat_cf,
        ),
        Scenario(
            id="FF-CANON-05",
            module=4,
            category="canonical",
            question="If a customer pays next year, when is revenue recognised?",
            expected_answer=(
                "Revenue is recognised when the goods/services are delivered — this period, "
                "via a credit sale that creates Accounts Receivable — NOT next year when cash "
                "is actually collected. Collecting the receivable next year has no further "
                "Income Statement effect."
            ),
            expected_keypoints=[
                "delivered", "this period", "accounts receivable", "not when cash",
            ],
            reference=credit_linkage,
        ),
    ]


# ---------------------------------------------------------------------------
# Generated: one classification question per chart-of-accounts entry
# ---------------------------------------------------------------------------
def _classification_scenarios() -> list[Scenario]:
    out: list[Scenario] = []
    for i, (code, acc) in enumerate(sorted(CHART_OF_ACCOUNTS.items()), start=1):
        out.append(
            Scenario(
                id=f"FF-COA-{i:03d}",
                module=3,
                category="chart_of_accounts",
                question=f"Which account category does '{acc.name}' belong to, and what is its normal balance?",
                expected_answer=(
                    f"{acc.name} is a{'n' if acc.type.value[0] in 'aeiou' else ''} {acc.type.value} "
                    f"account with a normal {acc.normal_balance.value} balance. {acc.description}"
                ),
                expected_keypoints=[acc.type.value, acc.normal_balance.value],
                reference={"code": code, "type": acc.type.value, "normal_balance": acc.normal_balance.value},
            )
        )
    return out


# ---------------------------------------------------------------------------
# Generated: transaction-level scenarios (journal entry / cash effect /
# statements affected / future ripple) — every keypoint is computed from
# the live engines, never hand-typed.
# ---------------------------------------------------------------------------
def _journal_entry_scenario(idx: int, ttype: str) -> Scenario:
    rule = TRANSACTION_CATALOG[ttype]
    entry = build_journal_entry(ttype, _DEMO_AMOUNT)
    debit_legs = [p for p in entry.postings if p.side == Side.DEBIT]
    credit_legs = [p for p in entry.postings if p.side == Side.CREDIT]
    debit_names = [CHART_OF_ACCOUNTS[p.account_code].name for p in debit_legs]
    credit_names = [CHART_OF_ACCOUNTS[p.account_code].name for p in credit_legs]
    answer = (
        f"Debit {', '.join(debit_names)}; Credit {', '.join(credit_names)} "
        f"for {_fmt(_DEMO_AMOUNT)}."
    )
    return Scenario(
        id=f"FF-JE-{idx:03d}",
        module=2,
        category="journal_entry",
        question=f"{rule.label} of {_fmt(_DEMO_AMOUNT)} — what is the journal entry?",
        expected_answer=answer,
        expected_keypoints=[n.lower() for n in debit_names] + [n.lower() for n in credit_names] + ["debit", "credit"],
        reference={"transaction_type": ttype, "debits": debit_names, "credits": credit_names},
    )


def _cash_effect_scenario(idx: int, ttype: str) -> Scenario:
    rule = TRANSACTION_CATALOG[ttype]
    keypoint = "cash" if rule.cash_effect_today else "no cash"
    answer = (
        f"Yes — Cash moves today: {rule.teaches}"
        if rule.cash_effect_today
        else f"No — Cash is not affected today: {rule.teaches}"
    )
    return Scenario(
        id=f"FF-CASH-{idx:03d}",
        module=2,
        category="cash_effect",
        question=f"Does '{rule.label}' affect Cash today? Explain why or why not.",
        expected_answer=answer,
        expected_keypoints=[keypoint, "cash"],
        reference={"transaction_type": ttype, "cash_effect_today": rule.cash_effect_today},
    )


def _statements_affected_scenario(idx: int, ttype: str) -> Scenario:
    rule = TRANSACTION_CATALOG[ttype]
    linkage = explain_transaction_linkage(ttype, amount=_DEMO_AMOUNT)
    statements: set[str] = set()
    for t in linkage["today"]:
        for s in t["statements_affected"]:
            statements.add(s.split(" (")[0])
    kps = [s.lower() for s in statements]
    if linkage["income_statement_affected_today"]:
        kps.append("income statement")
    else:
        kps.append("balance sheet")
    answer = (
        f"'{rule.label}' affects: {', '.join(sorted(statements))} today. "
        f"{'It also changes the Income Statement immediately.' if linkage['income_statement_affected_today'] else 'It does NOT touch the Income Statement today.'}"
    )
    return Scenario(
        id=f"FF-STMT-{idx:03d}",
        module=9,
        category="statements_affected",
        question=f"Which financial statements does '{rule.label}' affect today, and why?",
        expected_answer=answer,
        expected_keypoints=list(dict.fromkeys(kps)),
        reference=linkage,
    )


def _future_ripple_scenario(idx: int, ttype: str) -> Optional[Scenario]:
    ripple = FUTURE_RIPPLES.get(ttype)
    if not ripple:
        return None
    rule = TRANSACTION_CATALOG[ttype]
    return Scenario(
        id=f"FF-FUTURE-{idx:03d}",
        module=9,
        category="future_ripple",
        question=f"What happens in FUTURE periods after '{rule.label}'?",
        expected_answer=" ".join(ripple),
        expected_keypoints=_ripple_keypoints(ttype),
        reference={"transaction_type": ttype, "future_ripple": ripple},
    )


def _ripple_keypoints(ttype: str) -> list[str]:
    mapping = {
        "buy_asset_cash": ["depreciat", "ebit", "pat"],
        "buy_asset_credit": ["depreciat", "accounts payable"],
        "take_loan": ["interest", "repaid", "principal"],
        "deferred_revenue_received": ["unearned revenue", "revenue", "no"],
        "prepay_expense": ["expense", "no"],
        "salary_due": ["cash", "no"],
        "accrue_interest": ["cash", "no"],
        "accrue_tax": ["cash", "no"],
        "credit_sale": ["cash", "receivable"],
        "purchase_inventory_cash": ["cogs", "sold"],
        "purchase_inventory_credit": ["cogs", "payable"],
    }
    return mapping.get(ttype, [])


def _generated_transaction_scenarios() -> list[Scenario]:
    out: list[Scenario] = []
    ttypes = sorted(TRANSACTION_CATALOG.keys())
    for i, ttype in enumerate(ttypes, start=1):
        out.append(_journal_entry_scenario(i, ttype))
        out.append(_cash_effect_scenario(i, ttype))
        out.append(_statements_affected_scenario(i, ttype))
        ripple_scenario = _future_ripple_scenario(i, ttype)
        if ripple_scenario:
            out.append(ripple_scenario)
    return out


_SUITE_CACHE: list[Scenario] | None = None


def build_assessment_suite() -> list[Scenario]:
    global _SUITE_CACHE
    if _SUITE_CACHE is not None:
        return _SUITE_CACHE
    suite = _canonical_scenarios() + _classification_scenarios() + _generated_transaction_scenarios()
    _SUITE_CACHE = suite
    return suite


def get_scenario(scenario_id: str) -> Optional[Scenario]:
    for s in build_assessment_suite():
        if s.id == scenario_id:
            return s
    return None


def list_scenarios(*, category: Optional[str] = None, module: Optional[int] = None) -> list[dict[str, Any]]:
    out = []
    for s in build_assessment_suite():
        if category and s.category != category:
            continue
        if module is not None and s.module != module:
            continue
        out.append({"id": s.id, "module": s.module, "category": s.category, "question": s.question})
    return out


def grade_answer(scenario_id: str, candidate_answer: str) -> dict[str, Any]:
    """Heuristic causal-reasoning grader — keyword presence, no LLM."""
    scenario = get_scenario(scenario_id)
    if not scenario:
        return {"found": False, "scenario_id": scenario_id}
    low = (candidate_answer or "").lower()
    matched = [kp for kp in scenario.expected_keypoints if kp.lower() in low]
    missing = [kp for kp in scenario.expected_keypoints if kp.lower() not in low]
    total = max(1, len(scenario.expected_keypoints))
    score = round(len(matched) / total, 3)
    return {
        "found": True,
        "scenario_id": scenario_id,
        "question": scenario.question,
        "score": score,
        "passed": score >= 0.6,
        "matched_keypoints": matched,
        "missing_keypoints": missing,
        "model_answer": scenario.expected_answer,
    }
