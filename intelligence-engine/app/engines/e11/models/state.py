"""E11-002/003 Sentiment State Builder — news soft envelope + social caps."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.engines.e11.features.builder import SentimentPanel
from app.engines.e11.mapping import RELIABILITY, SOCIAL_WEIGHT_CAP, SOFT_VOTER_WEIGHT
from app.engines.e11.models.decay import decay_weight
from app.engines.e11.models.scoring import aggregate_docs, news_document_score


@dataclass
class SentimentStateRow:
    symbol: str
    as_of: str
    entity_id: str
    entity_confidence: float
    sector_id: str | None
    news_score: float
    composite_score: float
    reliability_weight: float
    decay_weight: float
    freshness_hours: float
    soft_voter_weight: float
    social_weight_cap: float
    social_enabled: bool
    label: str
    side: str
    confidence: float
    doc_count: int = 0
    stale_inputs: list[str] = field(default_factory=list)
    discovery: str = "pit_news"
    sent_meta: dict[str, float] = field(default_factory=dict)


def compute_universe_states(panels: dict[str, SentimentPanel]) -> dict[str, SentimentStateRow]:
    out: dict[str, SentimentStateRow] = {}
    for sym in sorted(panels.keys()):
        out[sym] = _compute_one(panels[sym])
    return out


def _compute_one(panel: SentimentPanel) -> SentimentStateRow:
    src = (panel.news_source or "tier1_news").lower()
    if src.startswith("social"):
        rel = 0.0
    elif "tier1" in src or "tier-1" in src:
        rel = RELIABILITY["tier1_news"]
    elif "filing" in src:
        rel = RELIABILITY["official_filing"]
    elif "exchange" in src:
        rel = RELIABILITY["exchange_announcement"]
    else:
        rel = RELIABILITY.get(src, RELIABILITY["news"])

    docs = [
        {
            "tone": d.tone,
            "age_hours": d.age_hours,
            "entity_link": d.entity_link,
        }
        for d in panel.docs
    ]
    if docs:
        news, mean_decay, freshness = aggregate_docs(docs, reliability=rel)
    else:
        dw = decay_weight(age_hours=panel.news_recency_hours or 24.0)
        news = news_document_score(
            tone=panel.news_tone,
            volume=panel.news_volume,
            age_hours=panel.news_recency_hours or 24.0,
            decay_w=dw,
            reliability=rel,
            entity_link=panel.entity.confidence,
        )
        mean_decay = dw
        freshness = float(panel.news_recency_hours or 24.0)

    # P0 single-source composite = news soft score
    composite = news
    label, side = _label_side(composite)

    coverage = 1.0 - 0.12 * len(panel.stale)
    conf = round(
        max(
            0.35,
            min(
                0.95,
                0.45
                + 0.30 * rel
                + 0.15 * mean_decay
                + 0.10 * max(0.0, coverage)
                + 0.05 * panel.entity.confidence,
            ),
        ),
        6,
    )
    # Soft voter: present with capped weight; social disabled ⇒ 0 social share
    soft_w = SOFT_VOTER_WEIGHT if panel.docs or panel.news_tone is not None else 0.0
    soft_w = min(soft_w, SOCIAL_WEIGHT_CAP)  # encode cap rule even for soft path

    return SentimentStateRow(
        symbol=panel.symbol,
        as_of=panel.as_of,
        entity_id=panel.entity.entity_id,
        entity_confidence=panel.entity.confidence,
        sector_id=panel.sector_id,
        news_score=news,
        composite_score=composite,
        reliability_weight=round(rel, 6),
        decay_weight=round(mean_decay, 6),
        freshness_hours=round(freshness, 4),
        soft_voter_weight=soft_w,
        social_weight_cap=SOCIAL_WEIGHT_CAP,
        social_enabled=False,
        label=label,
        side=side,
        confidence=conf,
        doc_count=len(panel.docs),
        stale_inputs=list(panel.stale),
        discovery=panel.discovery,
        sent_meta=dict(panel.sent_meta),
    )


def _label_side(composite: float) -> tuple[str, str]:
    if composite >= 65.0:
        return "Bullish Sentiment", "bullish"
    if composite <= 35.0:
        return "Bearish Sentiment", "bearish"
    if 45.0 <= composite <= 55.0:
        return "Neutral Sentiment", "neutral"
    if composite > 55.0:
        return "Mildly Bullish", "bullish"
    return "Mildly Bearish", "bearish"
