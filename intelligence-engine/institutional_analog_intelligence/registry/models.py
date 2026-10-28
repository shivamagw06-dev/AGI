"""Memory object constructor — validated historical analogues only."""

from __future__ import annotations

from typing import Any

from institutional_analog_intelligence.schema import IMAI_VERSION


def memory(
    memory_id: str,
    *,
    memory_type: str,
    title: str,
    entities: list[str],
    time_period: str,
    available_from: str,
    market_regime: str | None = None,
    industry: str | None = None,
    macro_regime: list[str] | None = None,
    policy_context: str | None = None,
    evidence_ids: list[str] | None = None,
    replay_ids: list[str] | None = None,
    confidence: float = 0.75,
    outcome_summary: str,
    lessons_learned: list[str],
    limitations: list[str] | None = None,
    source: str = "validated_historical_seed",
    cues: list[str] | None = None,
    tags: list[str] | None = None,
    commodity_exposure: list[str] | None = None,
    corporate_event_type: str | None = None,
    risk_profile: str | None = None,
    financial_profile: str | None = None,
    valuation_profile: str | None = None,
    known_outcome_as_of: str | None = None,
) -> dict[str, Any]:
    """Build one Institutional Memory object. Never invents outcomes beyond seeds."""
    return {
        "memory_id": memory_id,
        "type": memory_type,
        "title": title,
        "entities": [str(e).upper() if e.isalpha() or e.replace("_", "").isalnum() else e for e in entities],
        "time_period": time_period,
        "available_from": available_from,
        "known_outcome_as_of": known_outcome_as_of or available_from,
        "market_regime": market_regime,
        "industry": industry,
        "macro_regime": list(macro_regime or ([] if not market_regime else [market_regime])),
        "policy_context": policy_context,
        "evidence_ids": list(evidence_ids or [f"seed:{memory_id}"]),
        "replay_ids": list(replay_ids or []),
        "confidence": float(confidence),
        "similarity_score": None,  # filled at retrieval
        "outcome_summary": outcome_summary,
        "lessons_learned": list(lessons_learned),
        "limitations": list(
            limitations
            or [
                "Curated historical seed — not a live forecast",
                "Compare carefully; regimes never repeat exactly",
            ]
        ),
        "source": source,
        "version": IMAI_VERSION,
        "cues": [c.lower() for c in (cues or [])],
        "tags": list(tags or []),
        "commodity_exposure": list(commodity_exposure or []),
        "corporate_event_type": corporate_event_type,
        "risk_profile": risk_profile,
        "financial_profile": financial_profile,
        "valuation_profile": valuation_profile,
        "fabricated": False,
        "llm_used": False,
        "validated_historical": True,
    }
