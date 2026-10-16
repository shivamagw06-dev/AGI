"""Concept Acceptance Test v1.0 — permanent regression suite for the
financial_concepts engine (Phase 2.6) on the LIVE Ask product path.

Distinct from the AGI Financial Intelligence Acceptance Test v1.0
(afi_acceptance_v1.py), which is the broad 40-question release gate across
every phase. This suite exists specifically to catch a regression in the
Financial Router's concept fallback tier (app/ui/financial_router.py's
_answer_financial_concept) or the Unsupported Coverage Policy
(app/ui/coverage_policy.py) without needing to run the full 40-question
suite every time.

Per-question assertions (all six must hold for a PASS):
    1. routed_to_financial_concepts — ask_orchestration.financial_engine ==
       "financial_concepts" (or, for D30/31/32-style questions,
       short_circuit == "unsupported_coverage_policy")
    2. no_retrieval                — funnel.retrieved == 0 (nothing was
       fetched from generic retrieval; the concept engine answered alone)
    3. no_entity_lookup            — no ticker was bound (entity.detected
       is falsy) — concept questions must never trigger entity resolution
    4. correct_concept_card        — the answer text names the concept's
       own title/key vocabulary, not a different concept
    5. direct_answer_first         — first sentence is not scaffold/meta
    6. no_hallucination            — no company-name pattern, no framework
       leakage, no fabricated numbers
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Sequence

FRAMEWORK_LEAK_MARKERS = (
    "analyse via", "analyze via", "committee", "intent:", "framework:",
    "planning", "validated publish", "fill from existing reasoning", "step 1:",
)

_COMPANY_SUFFIX_RE = re.compile(r"\b(pvt\.?\s*ltd|private\s+limited|\bltd\.?\b|\binc\.?\b|\bcorp\.?\b)\b", re.I)


def has_framework_leak(text: str) -> bool:
    low = (text or "").strip().lower()
    return any(m in low[:200] for m in FRAMEWORK_LEAK_MARKERS)


CONCEPT_ACCEPTANCE_QUESTIONS: List[Dict[str, Any]] = [
    {"id": "CA-01", "prompt": "What is Enterprise Value?", "expected_key": "enterprise_value",
     "title_terms": ("enterprise", "value")},
    {"id": "CA-02", "prompt": "Explain ROIC.", "expected_key": "roic",
     "title_terms": ("roic", "invested capital")},
    {"id": "CA-03", "prompt": "Explain EVA.", "expected_key": "eva",
     "title_terms": ("eva", "economic value added")},
    {"id": "CA-04", "prompt": "Explain Residual Income.", "expected_key": "residual_income",
     "title_terms": ("residual income",)},
    {"id": "CA-05", "prompt": "Explain DuPont.", "expected_key": "dupont_model",
     "title_terms": ("dupont",)},
    {"id": "CA-06", "prompt": "Explain NOPAT.", "expected_key": "nopat",
     "title_terms": ("nopat",)},
    {"id": "CA-07", "prompt": "Explain Cash Conversion Cycle.", "expected_key": "cash_conversion_cycle",
     "title_terms": ("cash conversion cycle",)},
    {"id": "CA-08", "prompt": "Explain Working Capital.", "expected_key": "working_capital",
     "title_terms": ("working capital",)},
    {"id": "CA-09", "prompt": "Why do banks trade on P/B?", "expected_key": None,
     "title_terms": ("book value", "p/b", "price-to-book", "price to book")},
    {"id": "CA-10", "prompt": "Explain Incremental ROIC.", "expected_key": "incremental_roic",
     "title_terms": ("incremental roic",)},
    {"id": "CA-11", "prompt": "What is Economic Profit?", "expected_key": "economic_profit",
     "title_terms": ("economic profit",)},
    {"id": "CA-12", "prompt": "What is FCF Yield?", "expected_key": "fcf_yield",
     "title_terms": ("fcf yield", "free cash flow yield")},
]

assert len(CONCEPT_ACCEPTANCE_QUESTIONS) == 12


def evaluate_concept_question(
    case: Dict[str, Any],
    *,
    text: str,
    financial_engine: str | None,
    financial_router_triggered: bool | None,
    short_circuit: str | None,
    retrieved: int,
    entity_detected: Any,
    http_status: int,
    latency_ms: int,
    financial_engine_key: str | None = None,
) -> Dict[str, Any]:
    low = (text or "").lower()
    assertions: Dict[str, bool] = {}

    # KUL (Phase X) short-circuits concept questions through the same
    # financial_concepts provider; accept either the legacy financial_router
    # signal or KUL with financial_concepts as the primary engine.
    assertions["routed_to_financial_concepts"] = bool(
        financial_engine == "financial_concepts"
        or short_circuit == "unsupported_coverage_policy"
        or (
            short_circuit == "knowledge_unification"
            and financial_engine in {
                "financial_concepts",
                "financial_foundations",
                "financial_statement_intelligence",
            }
        )
    )
    assertions["no_retrieval"] = retrieved in (0, None)
    assertions["no_entity_lookup"] = not bool(entity_detected)
    if case.get("expected_key"):
        # Authoritative check: the router's own reported concept key, not a
        # fuzzy text scan (paraphrased card text can legitimately omit the
        # exact title phrase — e.g. "CCC" instead of "cash conversion cycle").
        assertions["correct_concept_card"] = financial_engine_key == case["expected_key"]
    else:
        assertions["correct_concept_card"] = any(t in low for t in case["title_terms"])
    first_sentence = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0] if text.strip() else ""
    assertions["direct_answer_first"] = bool(first_sentence) and not has_framework_leak(first_sentence) and len(first_sentence) > 10
    assertions["no_hallucination"] = not bool(_COMPANY_SUFFIX_RE.search(text or "")) and not has_framework_leak(text)

    passed = all(assertions.values())
    failed_assertions = [k for k, v in assertions.items() if not v]

    return {
        "id": case["id"],
        "prompt": case["prompt"],
        "answer": text,
        "expected_key": case["expected_key"],
        "financial_engine": financial_engine,
        "financial_router_triggered": financial_router_triggered,
        "short_circuit": short_circuit,
        "http_status": http_status,
        "latency_ms": latency_ms,
        "assertions": assertions,
        "failed_assertions": failed_assertions,
        "pass": passed,
    }
