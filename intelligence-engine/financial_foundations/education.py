"""Financial Education Layer — plain-language facade over the knowledge
base, statement concepts, accounting rules, and linkage engine.

A single lookup function (`explain`) that answers "what is X?" whether X
is a Module 1-5 concept, a Module 6-8 statement line, or a transaction
type — always returning definition + business meaning + example, never
a bare dictionary definition.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from financial_foundations import knowledge_base as kb
from financial_foundations import statement_concepts as sc
from financial_foundations.accounting_rules import explain_rule, list_transaction_types
from financial_foundations.linkage_engine import explain_transaction_linkage, why_pat_not_equal_cash_flow


def explain_concept(key: str) -> dict[str, Any]:
    """Module 1-8 concept lookup (accounting equation, debit/credit, EBITDA, ...)."""
    card = kb.get_concept(key) or sc.get_concept(key)
    if not card:
        return {"found": False, "key": key}
    out = {
        "found": True,
        "key": card.key,
        "title": card.title,
        "definition": card.definition,
        "business_meaning": card.business_meaning,
        "common_mistake": card.common_mistake,
        "example": card.example,
    }
    if hasattr(card, "formula"):
        out["formula"] = card.formula  # statement_concepts.ConceptCard has a formula field
    if hasattr(card, "module"):
        out["module"] = card.module
    return out


def explain_transaction(transaction_type: str, *, amount: float = 100_000.0) -> dict[str, Any]:
    """Module 2/4/5/9 lookup: what does this transaction do, today and over time?"""
    rule_info = explain_rule(transaction_type)
    if not rule_info.get("found"):
        return {"found": False, "transaction_type": transaction_type}
    linkage = explain_transaction_linkage(transaction_type, amount=amount)
    return {**rule_info, **linkage}


def list_all_concepts() -> list[str]:
    return sorted(set(kb.all_concepts().keys()) | set(sc.all_concepts().keys()))


def list_all_transaction_types() -> list[str]:
    return list_transaction_types()


def _normalize(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", text.strip().lower())
    return re.sub(r"\s+", " ", cleaned).strip()


def explain(topic: str, *, amount: float = 100_000.0) -> dict[str, Any]:
    """Single entry point: exact key match, then natural-language fallback.

    Accepts both a bare key ("ebitda") and a full question
    ("What is EBITDA?") — a learner or Ask should not have to know the
    internal slug.
    """
    raw = topic or ""
    cleaned = _normalize(raw)
    topic_key = cleaned.replace(" ", "_")

    concept = explain_concept(topic_key)
    if concept.get("found"):
        return {"topic_type": "concept", **concept}
    transaction = explain_transaction(topic_key, amount=amount)
    if transaction.get("found"):
        return {"topic_type": "transaction", **transaction}
    if topic_key in {"pat_vs_cash_flow", "why_pat_not_equal_cash_flow", "pat_ne_cash_flow"}:
        return {"topic_type": "lesson", "found": True, **why_pat_not_equal_cash_flow()}

    # Natural-language fallback: does any known concept/transaction key
    # appear as a whole word/phrase, or do ALL of its component words
    # appear somewhere in the question (order-independent)?
    words = set(cleaned.split())
    STOPWORDS = {"a", "an", "the", "to", "for", "of", "in", "on"}

    def _all_words_present(key: str) -> bool:
        parts = [w for w in key.split("_") if w and w not in STOPWORDS]
        return bool(parts) and all(w in words for w in parts)

    for key in sorted(list_all_concepts(), key=len, reverse=True):
        key_phrase = key.replace("_", " ")
        if key in words or key_phrase in cleaned or _all_words_present(key):
            hit = explain_concept(key)
            if hit.get("found"):
                return {"topic_type": "concept", **hit}
    for ttype in sorted(list_all_transaction_types(), key=len, reverse=True):
        phrase = ttype.replace("_", " ")
        if ttype in words or phrase in cleaned or _all_words_present(ttype):
            hit = explain_transaction(ttype, amount=amount)
            if hit.get("found"):
                return {"topic_type": "transaction", **hit}
    if "cash flow" in cleaned and "pat" in words:
        return {"topic_type": "lesson", "found": True, **why_pat_not_equal_cash_flow()}

    return {"topic_type": None, "found": False, "topic": topic}


def curriculum_index() -> dict[str, Any]:
    """A study-guide view of Phase 1 — every module, its concepts, its transactions."""
    return {
        "module_1_birth_of_a_company": sorted(kb.MODULE_1_BIRTH_OF_A_COMPANY.keys()),
        "module_2_double_entry": sorted(kb.MODULE_2_DOUBLE_ENTRY.keys()),
        "module_3_chart_of_accounts": sorted(kb.MODULE_3_CHART_OF_ACCOUNTS.keys()),
        "module_4_revenue_recognition": sorted(kb.MODULE_4_REVENUE_RECOGNITION.keys()),
        "module_5_expense_recognition": sorted(kb.MODULE_5_EXPENSE_RECOGNITION.keys()),
        "module_6_income_statement": sorted(sc.INCOME_STATEMENT_CONCEPTS.keys()),
        "module_7_balance_sheet": sorted(sc.BALANCE_SHEET_CONCEPTS.keys()),
        "module_8_cash_flow_statement": sorted(sc.CASH_FLOW_CONCEPTS.keys()),
        "module_9_transaction_types": list_transaction_types(),
    }
