"""Deterministic intent classifier — Track A taxonomy."""

from __future__ import annotations

from typing import Any

from ask_pipeline.intent_resolution.schema import INTENTS_V2


def classify_intent(
    *,
    language: dict[str, Any],
    temporal: dict[str, Any],
    entities: dict[str, Any],
) -> dict[str, Any]:
    cues = language.get("cues") or {}
    scores: dict[str, float] = {i: 0.0 for i in INTENTS_V2}
    reasons: list[str] = []

    def bump(intent: str, amount: float, reason: str) -> None:
        scores[intent] = scores.get(intent, 0.0) + amount
        reasons.append(f"{intent}:{reason}")

    # Historical replay highest priority when temporal/replay cues present
    if temporal.get("is_historical") and (
        cues.get("historical_replay") or temporal.get("mode") == "point_in_time" or "replay" in reasons
    ):
        bump("HistoricalReplay", 3.5, "temporal_replay")
    if cues.get("historical_replay"):
        bump("HistoricalReplay", 2.5, "replay_lexicon")

    if cues.get("cross_domain"):
        bump("CrossDomain", 3.0, "cross_domain_cue")
    # Multiple domain cues → cross-domain
    domain_hits = sum(
        1
        for k in ("macro", "government", "industry", "accounting", "documents", "valuation_lexicon")
        if cues.get(k)
    )
    if domain_hits >= 3 and (cues.get("analyse") or cues.get("cross_domain") or cues.get("list_request")):
        bump("CrossDomain", 2.2, "multi_domain")

    if cues.get("documents"):
        bump("Documents", 2.8, "documents_lexicon")
    if cues.get("compare"):
        bump("Compare", 3.0, "compare_lexicon")
    if cues.get("education") and not entities.get("primary"):
        bump("Education", 3.2, "definition_shape")
    if cues.get("portfolio"):
        bump("Portfolio", 3.0, "portfolio_lexicon")
    if cues.get("portfolio_strong"):
        bump("Portfolio", 2.2, "portfolio_strong_cue")
        # Portfolio construction must not collapse into Compare on "vs" / pair trade.
        if cues.get("compare"):
            scores["Compare"] -= 2.0
            reasons.append("Compare:penalty_portfolio_construction")
    if cues.get("government") and not cues.get("valuation_lexicon"):
        bump("Government", 2.4, "government_lexicon")
    if cues.get("macro") and not cues.get("valuation_lexicon"):
        bump("Macro", 2.4, "macro_lexicon")
    # FX / transmission into named companies → Macro / CrossDomain over generic Explain
    if cues.get("macro") and entities.get("primary") and (cues.get("how_would_you") or cues.get("explain")):
        bump("Macro", 2.2, "macro_transmission_to_companies")
        bump("CrossDomain", 1.8, "macro_cross_companies")
        scores["Explain"] -= 1.2
        reasons.append("Explain:penalty_macro_transmission")
    if cues.get("industry") and not entities.get("primary"):
        bump("Industry", 2.3, "industry_lexicon")
    if cues.get("industry") and entities.get("primary"):
        bump("Industry", 1.2, "industry_with_entity")
    if cues.get("corporate_events") and not cues.get("historical_replay"):
        bump("CorporateEvents", 2.0, "events_lexicon")
    if cues.get("investment_view"):
        bump("Analyse", 3.1, "investment_view_shape")
        if cues.get("corporate_events"):
            bump("CorporateEvents", 1.8, "event_driven_view")
    if cues.get("accounting"):
        bump("Accounting", 2.0, "accounting_lexicon")
    if cues.get("risk") and not cues.get("explain"):
        bump("Risk", 2.0, "risk_lexicon")
    # Portfolio risk review stays Portfolio when sizing / allocation context present.
    if cues.get("risk") and cues.get("portfolio_strong"):
        bump("Portfolio", 1.5, "portfolio_risk_review")
        scores["Risk"] -= 0.5
        reasons.append("Risk:secondary_to_portfolio_review")

    # Explain / why / how-would-you — do NOT force Valuation even if lexicon present
    if cues.get("why_question") or cues.get("explain") or cues.get("how_would_you"):
        bump("Explain", 3.4, "explain_shape")
        if cues.get("valuation_lexicon"):
            bump("Explain", 1.0, "valuation_lexicon_as_explain")
            scores["Valuation"] -= 1.5
            reasons.append("Valuation:penalty_explain_shape")
        # Domain-coloured explain (no company) → prefer domain intent
        if not entities.get("primary"):
            if cues.get("industry"):
                bump("Industry", 2.0, "why_industry_concept")
            if cues.get("macro") and not cues.get("government"):
                bump("Macro", 2.0, "why_macro_concept")
            if cues.get("government"):
                bump("Government", 2.0, "why_government_concept")
            if cues.get("documents"):
                bump("Documents", 2.0, "why_documents_concept")

    # Investigation / evaluation shapes: Analyse (or Accounting) over generic Explain
    if cues.get("how_would_you") and cues.get("analyse") and not cues.get("why_question"):
        bump("Analyse", 1.8, "investigation_shape")
        scores["Explain"] -= 1.5
        reasons.append("Explain:penalty_investigation_shape")
    # Accounting investigation — but document-primary asks stay Documents
    if cues.get("accounting") and (cues.get("how_would_you") or cues.get("analyse")):
        if cues.get("documents_primary"):
            bump("Documents", 2.6, "document_primary_over_accounting")
            scores["Accounting"] -= 1.5
            scores["Compare"] -= 1.5
            reasons.append("Accounting:secondary_to_documents_primary")
        else:
            bump("Accounting", 2.4, "accounting_investigation")
            if cues.get("documents"):
                bump("Documents", 0.8, "statements_notes")
            scores["Explain"] -= 2.0
            reasons.append("Explain:penalty_accounting_investigation")
    elif cues.get("documents_primary") and cues.get("how_would_you"):
        bump("Documents", 2.2, "documents_primary_investigation")
        scores["Compare"] -= 1.2
        scores["Explain"] -= 1.0
        reasons.append("Explain:penalty_documents_primary")
    # Compare questions must not lose to Explain via "how should"
    if cues.get("compare") and cues.get("how_would_you") and not cues.get("portfolio_strong"):
        if not cues.get("documents_primary"):
            bump("Compare", 1.6, "compare_investigation")
            scores["Explain"] -= 1.4
            reasons.append("Explain:penalty_compare_shape")
    # Industry explain / cycle questions
    if cues.get("industry") and cues.get("explain") and not entities.get("primary"):
        bump("Industry", 1.4, "industry_explain_priority")
        scores["Explain"] -= 0.8
        reasons.append("Explain:penalty_industry_explain")
    # Explicit risk review / checklist
    if cues.get("risk_review"):
        bump("Risk", 3.2, "risk_review_shape")
        scores["Accounting"] -= 1.5
        scores["Explain"] -= 1.0
        reasons.append("Accounting:penalty_risk_review")

    if cues.get("analyse") or cues.get("list_request"):
        bump("Analyse", 2.6, "analyse_shape")
        if cues.get("valuation_lexicon") and not cues.get("why_question"):
            # "assess whether undervalued" stays Analyse/Compare, not Valuation conclusion path
            bump("Analyse", 0.8, "analyse_with_valuation_words")
            scores["Valuation"] -= 1.0
            reasons.append("Valuation:penalty_analyse_shape")

    # Pure valuation asks (is it cheap / fair value of X)
    if cues.get("valuation_lexicon") and not (
        cues.get("why_question")
        or cues.get("explain")
        or cues.get("how_would_you")
        or cues.get("list_request")
        or cues.get("framework_explain")
    ):
        bump("Valuation", 2.8, "valuation_ask")
    # Framework-appropriateness questions are Explain, not Valuation/Compare conclusions
    if cues.get("framework_explain"):
        bump("Explain", 2.5, "framework_appropriateness")
        scores["Valuation"] -= 2.5
        scores["Compare"] -= 2.0
        reasons.append("Valuation:penalty_framework_explain")
        reasons.append("Compare:penalty_framework_explain")

    if cues.get("education") and cues.get("valuation_lexicon") and not entities.get("primary"):
        bump("Education", 1.5, "concept_metric")
        scores["Valuation"] -= 2.0
        reasons.append("Valuation:penalty_education_concept")

    # Evidence-package / IC prep without valuing
    if cues.get("list_request") and cues.get("cross_domain"):
        bump("CrossDomain", 1.5, "ic_evidence_package")
        scores["Valuation"] -= 2.0
        reasons.append("Valuation:penalty_evidence_package")
    # IC requests without portfolio-construction cues stay CrossDomain / Analyse
    if cues.get("investment_committee") and not cues.get("portfolio_strong"):
        bump("CrossDomain", 1.2, "investment_committee")
        scores["Portfolio"] -= 0.5
        reasons.append("Portfolio:secondary_to_ic_package")

    # Analog / memory questions must not collapse into CorporateEvents on "earnings"
    if cues.get("historical_replay") and cues.get("corporate_events"):
        scores["CorporateEvents"] -= 2.5
        bump("HistoricalReplay", 1.5, "analog_over_events")
        reasons.append("CorporateEvents:penalty_analog_memory")

    # Pick winner
    ranked = sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
    intent, score = ranked[0]
    if score <= 0.5:
        intent, score = "Unknown", 0.4
        reasons.append("fallback_unknown")

    # Confidence calibrated
    second = ranked[1][1] if len(ranked) > 1 else 0.0
    second_intent = ranked[1][0] if len(ranked) > 1 else None
    margin = score - second
    confidence = min(0.99, 0.55 + 0.1 * score + 0.05 * max(margin, 0))

    positive = [(k, v) for k, v in ranked if v > 0]
    rejected = [k for k, v in positive[2:8]]
    why_won = [r for r in reasons if r.startswith(f"{intent}:")][:6]
    why_lost = []
    if second_intent:
        why_lost = [r for r in reasons if r.startswith(f"{second_intent}:") or f"penalty" in r and second_intent in r][
            :6
        ]
        if margin > 0:
            why_lost.append(f"{second_intent}:lower_score_margin_{round(margin, 2)}")

    return {
        "intent": intent if intent in INTENTS_V2 else "Unknown",
        "secondary_intent": second_intent if second > 0 else None,
        "rejected_intents": rejected,
        "confidence": round(confidence, 4),
        "scores": {k: round(v, 3) for k, v in ranked if v > 0},
        "reasons": reasons[:24],
        "why_won": why_won,
        "why_lost": why_lost,
        "fabricated": False,
    }
