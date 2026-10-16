"""Intent Resolution Layer — Question → … → Evidence Requirements (before IERE)."""

from __future__ import annotations

from typing import Any

from ask_pipeline.intent_resolution.classifier import classify_intent
from ask_pipeline.intent_resolution.entities import detect_entities
from ask_pipeline.intent_resolution.language import analyse_language
from ask_pipeline.intent_resolution.requirements import evidence_requirements
from ask_pipeline.intent_resolution.schema import (
    FREEZE_LOCKS,
    INTENT_TO_LEGACY,
    INTENT_TO_QUESTION_TYPE_V2,
    IRL_VERSION,
    MODULE_CODE,
    PROGRAMME,
)
from ask_pipeline.intent_resolution.temporal import detect_temporal


def resolve_intent(
    question: str,
    *,
    ticker_hint: str | None = None,
) -> dict[str, Any]:
    """Full Track A resolution. Soft-wire only — does not mutate KF / governance modules."""
    language = analyse_language(question)
    temporal = detect_temporal(question)
    entities = detect_entities(
        question,
        ticker_hint=ticker_hint,
        language_cues=language.get("cues"),
    )
    classified = classify_intent(language=language, temporal=temporal, entities=entities)

    # Strengthen HistoricalReplay when temporal point-in-time + replay/describe evidence
    cues = language.get("cues") or {}
    if temporal.get("is_historical") and (
        cues.get("historical_replay") or "replay" in (language.get("normalized") or "")
    ):
        classified = {
            **classified,
            "intent": "HistoricalReplay",
            "confidence": max(float(classified.get("confidence") or 0), 0.95),
            "reasons": list(classified.get("reasons") or []) + ["forced_historical_replay"],
        }

    intent = classified["intent"]
    concept_mode = bool(entities.get("concept_mode"))
    # Concept / explain intents must not bind stray entities
    if intent in {"Education", "Explain", "Industry", "Macro", "Government"} and not (
        entities.get("raw_mentions")
    ):
        concept_mode = True
        entities = {
            **entities,
            "concept_mode": True,
            "entities": [],
            "primary": None,
            "count": 0,
        }

    requirements = evidence_requirements(intent, concept_mode=concept_mode, temporal=temporal)
    question_type = INTENT_TO_QUESTION_TYPE_V2.get(intent, "education")
    legacy_intent = INTENT_TO_LEGACY.get(intent, "Unknown")

    return {
        "irl_version": IRL_VERSION,
        "module": MODULE_CODE,
        "programme": PROGRAMME,
        "question": language.get("question"),
        "language": language,
        "intent": intent,
        "primary_intent": intent,
        "secondary_intent": classified.get("secondary_intent"),
        "rejected_intents": classified.get("rejected_intents") or [],
        "legacy_intent": legacy_intent,
        "intent_confidence": classified.get("confidence"),
        "intent_scores": classified.get("scores"),
        "intent_reasons": classified.get("reasons"),
        "intent_why_won": classified.get("why_won") or [],
        "intent_why_lost": classified.get("why_lost") or [],
        "question_type": question_type,
        "question_type_source": "intent_resolution_layer",
        "entities": entities.get("entities") or [],
        "primary": None if concept_mode else entities.get("primary"),
        "soft_tags": entities.get("soft_tags") or [],
        "concept_mode": concept_mode,
        "entity_pollution_blocked": bool(entities.get("entity_pollution_blocked")),
        "ignored_ticker_hint": entities.get("ignored_ticker_hint"),
        "temporal": temporal,
        "as_of": temporal.get("as_of"),
        "evidence_requirements": requirements,
        "investment_recommendation": bool(cues.get("portfolio")),
        "freeze_locks": FREEZE_LOCKS,
        "overrides_classify_question": True,
        "fabricated": False,
    }
