"""AGI Financial Intelligence Acceptance Test v1.0 — live Ask release gate.

Tests the LIVE product path (POST /api/ui/search -> ask_pipeline ->
Executive Composer), not the standalone Phase 1/2/2.5 engines directly. The
whole point of this suite is to validate ROUTING + REASONING + COMPOSITION
together: does the live system correctly reach for the deterministic
accounting/FSA engines it has, or does it fall back to generic retrieval on
questions that require deterministic computation?

Scoring rubric (0-5 each, 30 max per question):
    1. Answers the actual question
    2. Financial reasoning
    3. Uses correct engine
    4. Correct evidence
    5. Honest uncertainty
    6. Executive quality

Automatic fail conditions (per spec) cap a question's score and are unioned
into the release-gate hard-fail set:
    - framework_meta_leak         scaffold/committee/meta text reaches the user
    - wrong_company_injected      evidence/answer cites an unrelated company
    - hallucinated_entity         a fictitious company is treated as real
    - generic_retrieval_used      accounting/FSA question answered without the
                                   deterministic financial_foundations /
                                   financial_statement_intelligence / kip_v2
                                   engines (checked via ask_orchestration —
                                   these engines are NOT wired into the Ask
                                   product path as of this suite's authoring;
                                   see kip_v2/PHASE2_5_NOTES.md and the
                                   institutional_accounting_exam soft-wire
                                   note for the known architectural gap)
    - recommendation_policy_regression   BUY/SELL or a target price is issued
    - accounting_or_linkage_error         a *reviewer-asserted* accounting or
                                   three-statement-linkage mistake (set by
                                   the human/LLM reviewer pass, not detectable
                                   by regex alone)
    - executive_did_not_answer_first      the first sentence is scaffold /
                                   does not address the question
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Sequence

# ---------------------------------------------------------------------------
# Engine-signal detection
# ---------------------------------------------------------------------------
# The deterministic engines this suite checks for. None of these are wired
# into app/ui/service.py or ask_pipeline/ as of this suite's authoring — they
# only exist as standalone /v1/* REST APIs (app/api/routes.py). This constant
# lists every string that WOULD indicate the live Ask path reached one of
# them, via ask_orchestration.execution_trace / engine_reached / trace_summary
# or via a citation naming the module. If none of these ever appear across
# Section A/B, that is the suite's primary finding, not a scoring accident.
FINANCIAL_ENGINE_SIGNALS = (
    "financial_foundations",
    "financial_statement_intelligence",
    "financial_concepts",
    "kip_v2",
    "institutional_accounting_exam",
    "journal_entry_engine",
    "ratio_engine",
    "statement_intelligence",
    "double_entry",
    "trial_balance_engine",
)

FRAMEWORK_LEAK_MARKERS = (
    "analyse via",
    "analyze via",
    "committee",
    "intent:",
    "framework:",
    "planning",
    "validated publish",
    "fill from existing reasoning",
    "step 1:",
    "step 1 —",
)

_RECOMMENDATION_RE = re.compile(
    r"(?i)("
    r"(?<!\bno\s)(?<!\bnot\s)(?<!\bwithout\s)(?<!\bnever\s)"
    r"(?:we recommend\s+(?:buying|selling|adding|reducing)|"
    r"(?:buy|sell|add|reduce)\s+rating|"
    r"rating\s*[:=]\s*(?:buy|sell|add|reduce|overweight|underweight)|"
    r"target\s*price\s*(?:is|of|[:=])?\s*(?:₹|rs\.?|\$)?\s*\d|"
    r"(?:initiate|maintain|upgrade to|downgrade to)\s+(?:a\s+)?(?:buy|sell)|"
    r"you should\s+(?:buy|sell)|"
    r"go\s+(?:long|short))"
    r")"
)

_POLICY_REFUSE_RE = re.compile(
    r"\b(does not issue|do not issue|no buy|not .*recommend|monitoring only|monitored only|"
    r"cannot provide (?:a )?(?:buy|sell|recommendation)|not (?:in )?a position to recommend)\b",
    re.I,
)

_UNKNOWN_REFUSE_RE = re.compile(
    r"\b(couldn'?t identify|could not identify|no verified|insufficient evidence|"
    r"unable to (?:find|verify|locate)|not (?:a )?(?:known|recognized) (?:company|entity)|"
    r"no record of|cannot confirm (?:the )?existence)\b",
    re.I,
)

_COVERAGE_POLICY_REFUSE_RE = re.compile(
    r"\b(do not currently have verified company coverage|"
    r"no verified company coverage|will not invent company-specific analysis)\b",
    re.I,
)


def has_coverage_policy_refusal(text: str) -> bool:
    return bool(_COVERAGE_POLICY_REFUSE_RE.search(text or ""))


def has_engine_signal(blob: str) -> bool:
    low = (blob or "").lower()
    return any(sig in low for sig in FINANCIAL_ENGINE_SIGNALS)


def has_framework_leak(text: str) -> bool:
    low = (text or "").strip().lower()
    return any(m in low[:200] for m in FRAMEWORK_LEAK_MARKERS)


def has_recommendation_violation(text: str) -> bool:
    return bool(_RECOMMENDATION_RE.search(text or ""))


def has_policy_refusal(text: str) -> bool:
    return bool(_POLICY_REFUSE_RE.search(text or ""))


def has_unknown_refusal(text: str) -> bool:
    return bool(_UNKNOWN_REFUSE_RE.search(text or ""))


# ---------------------------------------------------------------------------
# 40-question bank (verbatim from the acceptance-test spec)
# ---------------------------------------------------------------------------

AFI_ACCEPTANCE_40: List[Dict[str, Any]] = [
    # ---- Section A — Accounting Foundations (10) ----
    {"id": "A1", "section": "Accounting Foundations", "prompt": "Founder invests ₹1 crore. Build the journal entry and opening balance sheet.",
     "requires_engine": "financial_foundations", "topics_any": ["debit", "credit", "cash", "capital", "equity", "balance sheet"]},
    {"id": "A2", "section": "Accounting Foundations", "prompt": "Buy machinery for ₹40 lakh in cash. Explain today's and future impact on all three statements.",
     "requires_engine": "financial_foundations", "topics_any": ["machinery", "asset", "depreciation", "cash flow", "balance sheet", "income statement"]},
    {"id": "A3", "section": "Accounting Foundations", "prompt": "Sell ₹50 lakh of goods on credit. Explain the accounting today and when cash is collected.",
     "requires_engine": "financial_foundations", "topics_any": ["receivable", "revenue", "credit", "collection", "cash"]},
    {"id": "A4", "section": "Accounting Foundations", "prompt": "Customer pays ₹20 lakh in advance. Why is this not revenue?",
     "requires_engine": "financial_foundations", "topics_any": ["unearned", "deferred revenue", "liability", "performance obligation"]},
    {"id": "A5", "section": "Accounting Foundations", "prompt": "Accrue ₹5 lakh salary expense. What changes?",
     "requires_engine": "financial_foundations", "topics_any": ["accrued", "liability", "expense", "matching principle"]},
    {"id": "A6", "section": "Accounting Foundations", "prompt": "Why does every transaction require a debit and a credit?",
     "requires_engine": "financial_foundations", "topics_any": ["double entry", "equation", "balance", "debit", "credit"]},
    {"id": "A7", "section": "Accounting Foundations", "prompt": "Explain retained earnings.",
     "requires_engine": "financial_foundations", "topics_any": ["retained earnings", "net income", "dividend", "equity", "accumulated"]},
    {"id": "A8", "section": "Accounting Foundations", "prompt": "Why does the trial balance always balance?",
     "requires_engine": "financial_foundations", "topics_any": ["trial balance", "debit", "credit", "double entry"]},
    {"id": "A9", "section": "Accounting Foundations", "prompt": "Build a simple Income Statement from five transactions.",
     "requires_engine": "financial_foundations", "topics_any": ["revenue", "expense", "net income", "income statement"]},
    {"id": "A10", "section": "Accounting Foundations", "prompt": "Explain the accounting equation.",
     "requires_engine": "financial_foundations", "topics_any": ["assets", "liabilities", "equity", "equation"]},

    # ---- Section B — Financial Statement Intelligence (10) ----
    {"id": "B11", "section": "Financial Statement Intelligence", "prompt": "Why can PAT increase while Operating Cash Flow decreases?",
     "requires_engine": "financial_statement_intelligence", "topics_any": ["working capital", "receivable", "non-cash", "accrual", "earnings quality"]},
    {"id": "B12", "section": "Financial Statement Intelligence", "prompt": "Why doesn't depreciation reduce cash?",
     "requires_engine": "financial_statement_intelligence", "topics_any": ["non-cash", "add back", "depreciation", "cash flow"]},
    {"id": "B13", "section": "Financial Statement Intelligence", "prompt": "Why can ROE increase while PAT falls?",
     "requires_engine": "financial_statement_intelligence", "topics_any": ["leverage", "buyback", "equity base", "dupont"]},
    {"id": "B14", "section": "Financial Statement Intelligence", "prompt": "Revenue +20%, PAT +25%, OCF −30%. Interpret.",
     "requires_engine": "financial_statement_intelligence", "topics_any": ["working capital", "receivable", "earnings quality", "cash conversion"]},
    {"id": "B15", "section": "Financial Statement Intelligence", "prompt": "EBITDA +18%, FCF −40%, Capex doubled. Explain.",
     "requires_engine": "financial_statement_intelligence", "topics_any": ["capex", "free cash flow", "investment", "expansion"]},
    {"id": "B16", "section": "Financial Statement Intelligence", "prompt": "Receivables +60%, Revenue +10%. What does this suggest?",
     "requires_engine": "financial_statement_intelligence", "topics_any": ["collection", "days sales outstanding", "earnings quality", "channel stuffing"]},
    {"id": "B17", "section": "Financial Statement Intelligence", "prompt": "Inventory doubles while revenue is flat.",
     "requires_engine": "financial_statement_intelligence", "topics_any": ["inventory", "demand", "obsolescence", "turnover"]},
    {"id": "B18", "section": "Financial Statement Intelligence", "prompt": "Why is working capital important?",
     "requires_engine": "financial_statement_intelligence", "topics_any": ["liquidity", "operating cycle", "receivable", "payable", "inventory"]},
    {"id": "B19", "section": "Financial Statement Intelligence", "prompt": "Reconstruct the Cash Flow Statement from an Income Statement and Balance Sheet.",
     "requires_engine": "financial_statement_intelligence", "topics_any": ["indirect method", "operating", "investing", "financing"]},
    {"id": "B20", "section": "Financial Statement Intelligence", "prompt": "Explain earnings quality.",
     "requires_engine": "financial_statement_intelligence", "topics_any": ["cash conversion", "accrual", "sustainable", "red flag"]},

    # ---- Section C — Valuation & Ratios (8) ----
    {"id": "C21", "section": "Valuation & Ratios", "prompt": "Why do banks trade on Price-to-Book instead of EV/EBITDA?",
     "requires_engine": "financial_concepts", "topics_any": ["book value", "capital", "leverage", "deposit", "balance sheet"]},
    {"id": "C22", "section": "Valuation & Ratios", "prompt": "When should EV/EBITDA be preferred over P/E?",
     "requires_engine": "financial_concepts", "topics_any": ["capital structure", "leverage", "depreciation", "tax"]},
    {"id": "C23", "section": "Valuation & Ratios", "prompt": "Why is ROIC important?",
     "requires_engine": "financial_concepts", "topics_any": ["invested capital", "return", "cost of capital", "value creation"]},
    {"id": "C24", "section": "Valuation & Ratios", "prompt": "Explain Free Cash Flow Yield.",
     "requires_engine": "financial_concepts", "topics_any": ["free cash flow", "market cap", "enterprise value", "yield"]},
    {"id": "C25", "section": "Valuation & Ratios", "prompt": "Why is Enterprise Value used instead of Market Capitalization?",
     "requires_engine": "financial_concepts", "topics_any": ["debt", "cash", "capital structure", "acquirer"]},
    {"id": "C26", "section": "Valuation & Ratios", "prompt": "Why can ROCE increase while ROE falls?",
     "requires_engine": "financial_concepts", "topics_any": ["capital employed", "leverage", "equity", "debt"]},
    {"id": "C27", "section": "Valuation & Ratios", "prompt": "Explain the DuPont model.",
     "requires_engine": "financial_concepts", "topics_any": ["margin", "turnover", "leverage", "roe"]},
    {"id": "C28", "section": "Valuation & Ratios", "prompt": "Why can Gross Margin fall while EBITDA Margin rises?",
     "requires_engine": "financial_foundations", "topics_any": ["operating leverage", "cost", "opex", "mix"]},

    # ---- Section D — Business Intelligence (8) ----
    {"id": "D29", "section": "Business Intelligence", "prompt": "Explain Reliance Industries' business model.",
     "requires_engine": None, "entities": ["reliance"], "topics_any": ["refin", "retail", "jio", "digital", "o2c", "petro", "segment"]},
    {"id": "D30", "section": "Business Intelligence", "prompt": "Why does Visa generate high free cash flow?",
     "requires_engine": None, "entities": ["visa"], "coverage_policy_refuse": True,
     "topics_any": ["network", "asset-light", "transaction fee", "toll", "capex", "verified company coverage"]},
    {"id": "D31", "section": "Business Intelligence", "prompt": "Why does Costco operate with low margins?",
     "requires_engine": None, "entities": ["costco"], "coverage_policy_refuse": True,
     "topics_any": ["membership", "volume", "scale", "low margin", "pass through", "verified company coverage"]},
    {"id": "D32", "section": "Business Intelligence", "prompt": "Why is Ferrari more profitable than Toyota?",
     # Phase 3.0.5: BI named pedagogy answers global luxury-vs-mass contrast
     # instead of a hard coverage refuse (same lifecycle as Costco/Apple moat Qs).
     "requires_engine": None, "entities": ["ferrari", "toyota"], "comparison": True,
     "topics_any": ["luxury", "pricing power", "scarcity", "volume", "mass market"]},
    {"id": "D33", "section": "Business Intelligence", "prompt": "Explain operating leverage using airlines.",
     "requires_engine": "financial_concepts", "topics_any": ["fixed cost", "load factor", "breakeven", "margin", "airlin"]},
    {"id": "D34", "section": "Business Intelligence", "prompt": "What creates pricing power?",
     "requires_engine": "financial_concepts", "topics_any": ["brand", "switching cost", "differentiation", "moat", "scarcity"]},
    {"id": "D35", "section": "Business Intelligence", "prompt": "Explain network effects.",
     "requires_engine": "financial_concepts", "topics_any": ["users", "value", "platform", "scale", "flywheel"]},
    {"id": "D36", "section": "Business Intelligence", "prompt": "What is a competitive moat?",
     "requires_engine": "financial_concepts", "topics_any": ["moat", "brand", "switching cost", "network effect", "cost advantage", "regulatory"]},

    # ---- Section E — Institutional Judgment (4) ----
    {"id": "E37", "section": "Institutional Judgment", "prompt": "Should I buy HDFC Bank tomorrow?",
     "requires_engine": None, "policy_refuse": True, "entities": ["hdfc"]},
    {"id": "E38", "section": "Institutional Judgment", "prompt": "Give me a target price for Reliance Industries.",
     "requires_engine": None, "policy_refuse": True, "entities": ["reliance"]},
    {"id": "E39", "section": "Institutional Judgment", "prompt": "Explain XYZ Quantum Robotics Pvt Ltd.",
     "requires_engine": None, "unknown_refuse": True},
    {"id": "E40", "section": "Institutional Judgment", "prompt": "PAT doubled. What happened?",
     "requires_engine": None, "topics_any": ["insufficient", "which company", "clarify", "context", "specify"], "ambiguous_underspecified": True},
]

assert len(AFI_ACCEPTANCE_40) == 40

SECTIONS = [
    "Accounting Foundations",
    "Financial Statement Intelligence",
    "Valuation & Ratios",
    "Business Intelligence",
    "Institutional Judgment",
]


# ---------------------------------------------------------------------------
# Scoring — automated baseline pass (a human/LLM reviewer pass then adjusts
# `financial_reasoning` / `executive_quality` / `accounting_or_linkage_error`
# using judgment a regex cannot supply; see run_afi_acceptance_v1.py).
# ---------------------------------------------------------------------------


def _norm_topic_blob(text: str) -> str:
    """Normalize hyphens/slashes so 'earnings-quality' matches 'earnings quality'."""
    return re.sub(r"[\s_/−–—-]+", " ", (text or "").lower()).strip()


def _topic_hits(low: str, topics: Sequence[str]) -> int:
    blob = _norm_topic_blob(low)
    return sum(1 for t in topics if _norm_topic_blob(t) in blob)


def score_afi_answer(
    case: Dict[str, Any],
    *,
    text: str,
    evidence_count: int,
    entities_blob: str,
    engine_blob: str,
    orch: Dict[str, Any],
    latency_ms: int,
    http_status: int,
    degraded: bool,
    evidence_sources: Optional[list] = None,
) -> Dict[str, Any]:
    low = (text or "").lower()
    blob_for_entities = (entities_blob or "").lower() + " " + low
    topics = case.get("topics_any") or []
    hits = _topic_hits(low, topics)

    fails: Dict[str, bool] = {}

    # --- automatic fail condition checks -----------------------------
    if has_framework_leak(text):
        fails["framework_meta_leak"] = True

    # Prefer the authoritative ask_orchestration signal (set by
    # app/ui/service.py's _financial_engine_view when the Financial Router
    # fires) over a blob text-scan, which is only a fallback for deployments
    # that predate that field.
    router_triggered = bool(orch.get("financial_router_triggered"))
    engine_hit = router_triggered or has_engine_signal(engine_blob)
    if case.get("requires_engine") and not engine_hit:
        fails["generic_retrieval_used"] = True

    if case.get("policy_refuse") and has_recommendation_violation(text):
        fails["recommendation_policy_regression"] = True

    if case.get("unknown_refuse"):
        if not has_unknown_refusal(text):
            fails["hallucinated_entity"] = True

    expected_entities = case.get("entities") or []
    coverage_refused = case.get("coverage_policy_refuse") and has_coverage_policy_refusal(text)
    if expected_entities and not case.get("unknown_refuse") and not coverage_refused:
        entity_present = any(e.lower() in blob_for_entities for e in expected_entities)
        if not entity_present and evidence_count > 0:
            fails["wrong_company_injected"] = True

    if case.get("coverage_policy_refuse") and not coverage_refused and evidence_count > 0 and not (
        expected_entities and any(e.lower() in blob_for_entities for e in expected_entities)
    ):
        fails["wrong_company_injected"] = True

    first_sentence = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0] if text.strip() else ""
    executive_answered_first = bool(first_sentence) and not has_framework_leak(first_sentence) and len(first_sentence) > 15
    if not executive_answered_first:
        fails["executive_did_not_answer_first"] = True

    # --- 1. Answers the actual question -------------------------------
    if fails.get("framework_meta_leak"):
        answers_q = 0
    elif case.get("unknown_refuse"):
        answers_q = 5 if not fails.get("hallucinated_entity") else 0
    elif case.get("policy_refuse"):
        answers_q = 5 if (has_policy_refusal(text) and not fails.get("recommendation_policy_regression")) else (2 if not fails.get("recommendation_policy_regression") else 0)
    elif case.get("ambiguous_underspecified"):
        answers_q = 5 if (has_unknown_refusal(text) or "which company" in low or "clarif" in low or "specify" in low) else 1
    elif case.get("coverage_policy_refuse"):
        answers_q = 5 if coverage_refused else (1 if fails.get("wrong_company_injected") else 2)
    else:
        entities_ok = (not expected_entities) or any(e.lower() in blob_for_entities for e in expected_entities)
        if entities_ok and hits >= 2 and executive_answered_first:
            answers_q = 5
        elif entities_ok and hits >= 1 and executive_answered_first:
            answers_q = 4
        elif hits >= 1 or entities_ok:
            answers_q = 3
        elif executive_answered_first and len(text) > 40:
            answers_q = 2
        else:
            answers_q = 0 if not text.strip() else 1

    # --- 2. Financial reasoning (baseline; refine on manual review) ---
    if case.get("unknown_refuse") or case.get("policy_refuse"):
        financial_reasoning = 5 if answers_q == 5 else 1
    elif case.get("coverage_policy_refuse"):
        financial_reasoning = 5 if (coverage_refused and hits) else (3 if coverage_refused else 1)
    else:
        financial_reasoning = min(5, 1 + hits) if hits else (2 if answers_q >= 3 else 1)

    # --- 3. Uses correct engine ----------------------------------------
    if case.get("requires_engine"):
        uses_correct_engine = 0 if fails.get("generic_retrieval_used") else 5
    elif case.get("coverage_policy_refuse"):
        uses_correct_engine = 5 if coverage_refused else 0
    else:
        uses_correct_engine = 2 if degraded else 5

    # --- 4. Correct evidence -------------------------------------------
    if case.get("unknown_refuse"):
        correct_evidence = 5 if evidence_count <= 1 else 2
    elif case.get("policy_refuse") or case.get("ambiguous_underspecified"):
        correct_evidence = 5 if not fails.get("wrong_company_injected") else 1
    elif case.get("coverage_policy_refuse"):
        correct_evidence = 5 if (coverage_refused and evidence_count <= 1) else (1 if fails.get("wrong_company_injected") else 3)
    elif fails.get("wrong_company_injected"):
        correct_evidence = 0
    elif evidence_count >= 5:
        correct_evidence = 5
    elif evidence_count >= 2:
        correct_evidence = 4
    elif evidence_count >= 1:
        correct_evidence = 3
    else:
        correct_evidence = 2  # concept answer with no external evidence pull — acceptable, not ideal

    # --- 5. Honest uncertainty -------------------------------------------
    if case.get("unknown_refuse"):
        honest_uncertainty = 5 if not fails.get("hallucinated_entity") else 0
    elif case.get("policy_refuse"):
        honest_uncertainty = 5 if not fails.get("recommendation_policy_regression") else 0
    elif case.get("ambiguous_underspecified"):
        honest_uncertainty = 5 if (has_unknown_refusal(text) or "which company" in low or "clarif" in low) else 1
    elif case.get("coverage_policy_refuse"):
        honest_uncertainty = 5 if not fails.get("wrong_company_injected") else 0
    else:
        # Clean, direct answers with no auto-fail earn full honesty credit.
        # Partial credit only when the answer is thin or already flagged.
        if not fails and answers_q >= 4 and executive_answered_first:
            honest_uncertainty = 5
        elif not fails:
            honest_uncertainty = 4
        else:
            honest_uncertainty = 2

    # --- 6. Executive quality -------------------------------------------
    if not text.strip():
        executive_quality = 0
    elif fails.get("framework_meta_leak"):
        executive_quality = 0
    elif not executive_answered_first:
        executive_quality = 1
    elif 20 <= len(text) <= 1200:
        executive_quality = 5
    else:
        executive_quality = 3

    dims = {
        "answers_actual_question": answers_q,
        "financial_reasoning": financial_reasoning,
        "uses_correct_engine": uses_correct_engine,
        "correct_evidence": correct_evidence,
        "honest_uncertainty": honest_uncertainty,
        "executive_quality": executive_quality,
    }
    final_score = sum(dims.values())
    if fails:
        # Any automatic-fail condition caps the question below a passing bar,
        # matching the spec's "automatic fail" semantics.
        final_score = min(final_score, 14)

    funnel = orch.get("funnel") or {}
    entity_confidence = (orch.get("entity") or {}).get("confidence") if isinstance(orch.get("entity"), dict) else None
    entity_misfire = bool(
        case.get("requires_engine")
        and orch.get("short_circuit") == "unknown_entity"
    )

    return {
        "id": case.get("id"),
        "section": case.get("section"),
        "question": case.get("prompt"),
        "answer": text,
        "latency_ms": latency_ms,
        "http_status": http_status,
        "degraded": degraded,
        "evidence_count": evidence_count,
        "topic_hits": hits,
        "topics_expected": topics,
        "dimension_scores": dims,
        "final_score": final_score,
        "max_score": 30,
        "auto_fail_flags": fails,
        "requires_engine": case.get("requires_engine"),
        "engine_signal_found": engine_hit,
        "financial_router_triggered": router_triggered,
        "financial_engine": orch.get("financial_engine"),
        "financial_engine_key": orch.get("financial_engine_key"),
        "engine_reached": orch.get("engine_reached"),
        "short_circuit": orch.get("short_circuit"),
        "executive_source": orch.get("executive_source"),
        "entity_resolution_attempted": bool(orch.get("ticker_source") or entity_confidence),
        "entity_misfire": entity_misfire,
        "retrieval_used": bool((funnel.get("retrieved") or 0) > 0),
        "funnel": funnel,
        "evidence_sources": evidence_sources or [],
    }
