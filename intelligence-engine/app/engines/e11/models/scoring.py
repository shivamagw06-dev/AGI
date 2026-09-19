"""E11-002 News sentiment P0 — lexicon/tone scoring (deterministic, no NLP/LLM/ML)."""

from __future__ import annotations

import math
from typing import Any


# Minimal deterministic lexicon (P0 classifier stub — not ML)
_POS = {
    "beat", "surge", "upgrade", "growth", "strong", "record", "outperform",
    "buy", "bullish", "raise", "positive", "gain", "expand",
}
_NEG = {
    "miss", "cut", "downgrade", "weak", "loss", "fraud", "probe", "sell",
    "bearish", "slash", "negative", "decline", "shrink", "lawsuit",
}


def tone_from_text(text: str | None) -> float:
    """Return tone in [-1, 1] from simple lexicon counts."""
    if not text:
        return 0.0
    tokens = "".join(ch.lower() if ch.isalnum() else " " for ch in text).split()
    if not tokens:
        return 0.0
    pos = sum(1 for t in tokens if t in _POS)
    neg = sum(1 for t in tokens if t in _NEG)
    if pos == 0 and neg == 0:
        return 0.0
    return max(-1.0, min(1.0, (pos - neg) / max(1, pos + neg)))


def tone_to_score(tone: float | None) -> float:
    """Map tone [-1,1] or score [0,100] → [0,100]."""
    if tone is None:
        return 50.0
    t = float(tone)
    if -1.5 <= t <= 1.5:
        return round(max(0.0, min(100.0, 100.0 * (t + 1.0) / 2.0)), 6)
    return round(max(0.0, min(100.0, t)), 6)


def news_document_score(
    *,
    tone: float | None,
    volume: float | None,
    age_hours: float,
    decay_w: float,
    reliability: float,
    entity_link: float = 1.0,
) -> float:
    """Aggregate single-symbol news score with decay × reliability × entity-link gate."""
    if entity_link < 0.6:
        return 50.0
    base = tone_to_score(tone)
    if volume is None:
        vol_term = 1.0
    else:
        vol_term = 0.85 + 0.15 * min(1.0, math.log1p(max(0.0, float(volume))) / math.log1p(50.0))
    if age_hours > 72:
        vol_term *= 0.95
    raw = base * vol_term
    # Pull toward 50 as decay/reliability fall (historic news must not permanently bias)
    intensity = max(0.0, min(1.0, decay_w * reliability * entity_link))
    score = 50.0 + (raw - 50.0) * intensity
    return round(max(0.0, min(100.0, score)), 6)


def aggregate_docs(docs: list[dict[str, Any]], *, reliability: float) -> tuple[float, float, float]:
    """Return (score, mean_decay, freshness_hours) from document list."""
    from app.engines.e11.models.decay import decay_weight

    if not docs:
        return 50.0, 0.0, 999.0
    num = 0.0
    den = 0.0
    decays: list[float] = []
    ages: list[float] = []
    for d in docs:
        age = float(d.get("age_hours") or 24.0)
        ages.append(age)
        dw = decay_weight(age_hours=age)
        decays.append(dw)
        e = float(d.get("entity_link") or 1.0)
        if e < 0.6:
            continue
        s = tone_to_score(d.get("tone"))
        w = dw * reliability * e
        num += w * s
        den += w
    if den < 1e-12:
        return 50.0, 0.0, min(ages) if ages else 999.0
    return round(num / den, 6), round(sum(decays) / len(decays), 6), min(ages)
