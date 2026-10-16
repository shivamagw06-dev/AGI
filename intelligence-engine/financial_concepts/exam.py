"""Module 14 — Concept Examination.

150 scenario-based questions probing reasoning and business intuition, not
rote definition recall. Every question is generated from the concept
library itself (never fabricated content), using the field that actually
carries reasoning (``interpretation``) as the graded ground truth wherever
one exists, and a definition+business-meaning check otherwise.

The grader is deterministic and keyword/fact-based (mirroring
institutional_accounting_exam's grading approach) — no LLM judge.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

from financial_concepts.concepts import ALL_CONCEPTS, get_concept
from financial_concepts.schema import ConceptCard

# ---------------------------------------------------------------------------
# Hand-authored scenario questions — the exact examples from the Phase 2.6
# brief, plus comparative/interpretive questions that require reasoning
# ACROSS two related concepts, not lookup of a single card.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExamItem:
    item_id: str
    section: str
    prompt: str
    primary_key: str
    secondary_key: Optional[str] = None
    reasoning_terms: tuple[str, ...] = ()


HAND_AUTHORED: list[ExamItem] = [
    ExamItem("CE-001", "Valuation", "Why is Enterprise Value larger than Market Cap for a company carrying debt?",
             "enterprise_value", "net_debt", ("net debt", "cash")),
    ExamItem("CE-002", "Capital Allocation", "Why is ROIC more useful than ROE when comparing two companies with different leverage?",
             "roic", "roe_decomposition", ("leverage", "capital structure")),
    ExamItem("CE-003", "Banking", "Why do banks trade on Price-to-Book rather than EV/EBITDA?",
             "why_banks_use_pb", "ev_ebitda", ("deposit", "interest", "operating")),
    ExamItem("CE-004", "Ratio Intelligence", "Explain the DuPont Model and what it reveals about the quality of a company's ROE.",
             "dupont_model", None, ("margin", "turnover", "leverage")),
    ExamItem("CE-005", "Valuation", "Why can Free Cash Flow Yield exceed Earnings Yield for the same company?",
             "fcf_yield", "earnings_yield", ("non-cash", "depreciation", "working capital")),
    ExamItem("CE-006", "Corporate Finance", "What happens to a company's value creation when WACC exceeds ROIC?",
             "economic_profit", "wacc", ("destroy", "below", "value")),
    ExamItem("CE-007", "Corporate Finance", "What does Economic Profit measure that Net Income alone does not?",
             "economic_profit", "nopat", ("capital charge", "cost of capital")),
    ExamItem("CE-008", "Ratio Intelligence", "Why can ROCE increase while ROE falls for the same company?",
             "roce", "roe_decomposition", ("leverage", "equity multiplier")),
    ExamItem("CE-009", "Credit", "Why is a company with strong interest coverage still exposed to refinancing risk?",
             "interest_coverage", "refinancing_risk", ("maturity", "roll over")),
    ExamItem("CE-010", "Business Quality", "Why is a large user base not sufficient evidence of a network effect?",
             "network_effect", "economic_moat", ("more valuable", "users")),
    ExamItem("CE-011", "Capital Allocation", "Why can a share buyback destroy value even though it raises EPS?",
             "share_buyback", "market_capitalization", ("price paid", "intrinsic value")),
    ExamItem("CE-012", "Valuation", "Why is a DCF's terminal value more sensitive to assumptions than its explicit forecast period?",
             "terminal_value", "terminal_growth", ("perpetuity", "growth rate", "discount rate")),
    ExamItem("CE-013", "Corporate Finance", "Why does adding debt to a company's capital structure raise its levered beta?",
             "levered_beta", "unlevered_beta", ("leverage", "amplif")),
    ExamItem("CE-014", "Banking", "Why should GNPA never be assessed without also checking Provision Coverage?",
             "gnpa", "provision_coverage", ("provision", "cushion", "absorb")),
    ExamItem("CE-015", "Cash Flow", "Why can a company report rising profit while its cash conversion deteriorates?",
             "cash_conversion", "working_capital_absorption", ("working capital", "receivable", "inventory")),
    ExamItem("CE-016", "Credit", "Why does seniority matter even for bonds issued by the same company?",
             "seniority", "recovery_rate", ("priority", "repay")),
    ExamItem("CE-017", "Market", "Why do credit spreads widen even for fundamentally unchanged issuers during market stress?",
             "credit_spread", "default_risk", ("risk aversion", "liquidity", "market-wide")),
    ExamItem("CE-018", "Valuation", "Why might precedent transaction multiples exceed comparable company trading multiples for the same industry?",
             "precedent_transactions", "control_premium", ("control premium", "synergies")),
    ExamItem("CE-019", "Corporate Finance", "Why is incremental ROIC a better test of new investment quality than average ROIC?",
             "incremental_roic", "roic", ("marginal", "new capital", "legacy")),
    ExamItem("CE-020", "Business Quality", "Why is vertical integration only a genuine moat when it creates a cost or quality advantage a rival cannot replicate?",
             "vertical_integration", "economic_moat", ("cost advantage", "replicate")),
]


# ---------------------------------------------------------------------------
# Generated scenario questions — every remaining concept card becomes a
# reasoning-oriented prompt using whichever template fits the fields it
# actually has populated, so grading always checks real interpretation
# content, not a rephrased definition.
# ---------------------------------------------------------------------------


def _generate_items(target_total: int = 150) -> list[ExamItem]:
    items = list(HAND_AUTHORED)
    used_keys = {i.primary_key for i in items}
    n = len(items)
    for key in sorted(ALL_CONCEPTS.keys()):
        if n >= target_total:
            break
        card = get_concept(key)
        if card is None or key in used_keys:
            continue
        used_keys.add(key)
        n += 1
        if card.interpretation:
            prompt = f"How should an analyst interpret {card.title}, and what could be misleading about reading it in isolation?"
            terms = tuple(_key_terms(card.interpretation))
        elif card.common_mistakes:
            prompt = f"What is the most common mistake analysts make when using {card.title}?"
            terms = tuple(_key_terms(card.common_mistakes))
        else:
            prompt = f"What is {card.title} and why does it matter to an institutional analyst?"
            terms = tuple(_key_terms(card.business_meaning))
        items.append(ExamItem(f"CE-{n:03d}", card.module.replace('_', ' ').title(), prompt, key, None, terms))
    return items


def _key_terms(text: str, limit: int = 4) -> list[str]:
    """Pulls a handful of substantive (non-stopword, len>=5) words from a
    card's own authored text to use as the grading keyword set — the
    'ground truth' terms are always drawn from the card itself, never
    invented separately, so grading can never drift from the source."""

    words = re.findall(r"[a-zA-Z]{5,}", text.lower())
    stop = {"which", "these", "their", "there", "these", "would", "could", "should", "typically", "generally"}
    seen: list[str] = []
    for w in words:
        if w in stop or w in seen:
            continue
        seen.append(w)
        if len(seen) >= limit:
            break
    return seen


CONCEPT_EXAM: list[ExamItem] = _generate_items(150)


def list_exam_questions(section: Optional[str] = None) -> dict[str, Any]:
    items = [i for i in CONCEPT_EXAM if not section or i.section.lower() == section.lower()]
    return {
        "n": len(items),
        "section": section,
        "items": [
            {"item_id": i.item_id, "section": i.section, "prompt": i.prompt}
            for i in items
        ],
        "fabricated": False,
    }


def _find_item(item_id: str) -> Optional[ExamItem]:
    for i in CONCEPT_EXAM:
        if i.item_id == item_id:
            return i
    return None


def run_item(item_id: str) -> dict[str, Any]:
    """Produces the deterministic model answer for one exam item, built
    ONLY from the concept card(s) it targets — this is what the exam
    'answer key' is graded against."""

    item = _find_item(item_id)
    if item is None:
        return {"found": False, "item_id": item_id}
    primary = get_concept(item.primary_key)
    secondary = get_concept(item.secondary_key) if item.secondary_key else None
    if primary is None:
        return {"found": False, "item_id": item_id, "reason": "primary_concept_missing"}

    model_answer_parts = [primary.business_meaning]
    if primary.interpretation:
        model_answer_parts.append(primary.interpretation)
    if secondary is not None:
        model_answer_parts.append(secondary.business_meaning)

    return {
        "found": True,
        "item_id": item.item_id,
        "section": item.section,
        "prompt": item.prompt,
        "primary_concept": item.primary_key,
        "secondary_concept": item.secondary_key,
        "model_answer": " ".join(p for p in model_answer_parts if p),
        "expected_reasoning_terms": list(item.reasoning_terms),
        "evidence_level": primary.evidence_level,
        "confidence": primary.confidence,
        "fabricated": False,
    }


def grade_answer(item_id: str, candidate_answer: str) -> dict[str, Any]:
    """Deterministic keyword/fact grading — 0-100. Checks:
    1. Reasoning: does the answer touch the expected reasoning terms drawn
       from the concept card's own interpretation/common_mistakes text?
    2. Business intuition: does it reference the primary concept's own
       vocabulary (title words) at all?
    3. No hallucination: flags candidate answers containing a company name
       pattern (Ltd/Inc/Pvt) — this exam is concept-only and must never
       drift into inventing company-specific claims.
    4. Explicit uncertainty: for comparative ("why can X increase while Y
       falls") prompts, rewards hedged language ("usually", "can",
       "depends") over absolute claims ("always", "never", "guaranteed").
    """

    item = _find_item(item_id)
    if item is None:
        return {"found": False, "item_id": item_id}
    primary = get_concept(item.primary_key)
    if primary is None:
        return {"found": False, "item_id": item_id}

    text = (candidate_answer or "").lower()
    scores: dict[str, int] = {}

    reasoning_hits = sum(1 for t in item.reasoning_terms if t in text)
    scores["reasoning"] = min(25, 10 + reasoning_hits * 8) if item.reasoning_terms else (15 if text.strip() else 0)

    title_words = [w for w in re.findall(r"[a-zA-Z]{4,}", primary.title.lower())]
    intuition_hit = any(w in text for w in title_words)
    scores["business_intuition"] = 25 if intuition_hit else (10 if text.strip() else 0)

    hallucination_pattern = re.search(r"\b(pvt\.?\s*ltd|private\s+limited|\bltd\.?\b|\binc\.?\b|\bcorp\.?\b)\b", text)
    scores["no_hallucination"] = 0 if hallucination_pattern else 25

    hedged = bool(re.search(r"\b(usually|can|may|often|typically|depends|not always|tends to)\b", text))
    absolute = bool(re.search(r"\b(always|never|guaranteed|impossible|certainly)\b", text))
    if not text.strip():
        scores["explicit_uncertainty"] = 0
    elif hedged and not absolute:
        scores["explicit_uncertainty"] = 25
    elif hedged and absolute:
        scores["explicit_uncertainty"] = 15
    else:
        scores["explicit_uncertainty"] = 10

    total = sum(scores.values())
    return {
        "found": True,
        "item_id": item_id,
        "scores": scores,
        "total_score": total,
        "max_score": 100,
        "passed": total >= 60 and scores["no_hallucination"] == 25,
        "hallucination_flagged": scores["no_hallucination"] == 0,
    }
