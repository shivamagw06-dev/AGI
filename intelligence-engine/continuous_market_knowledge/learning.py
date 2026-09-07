"""Material market changes → learning events."""

from __future__ import annotations

from typing import Any

from continuous_market_knowledge.schema import MarketKnowledgeObject, MarketLearningEvent


def generate_learning(
    mko: MarketKnowledgeObject,
    *,
    materiality: dict[str, Any],
) -> MarketLearningEvent | None:
    if not materiality.get("learn"):
        return None
    return MarketLearningEvent(
        domain_key=mko.domain_key,
        summary=(
            f"{mko.label}: regime={mko.market_regime}, sentiment={mko.risk_sentiment}, "
            f"health={mko.health_score} ({materiality.get('reason')})"
        ),
        tier=materiality.get("tier") or mko.materiality_tier,
        reason=str(materiality.get("reason") or "material_change"),
        trigger=mko.trigger,
    )
