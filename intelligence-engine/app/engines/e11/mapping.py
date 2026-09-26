"""E11 P0 bindings — news-only soft voter (Architecture v1.0.1 / EPIC-015)."""

from __future__ import annotations

MODEL_VERSION = "e11-p0-sentiment-0.1.0"
ENGINE_VERSION = "1.0.0"
FORMULA_ID = "SM_AGI_SENT"
WEIGHT_SET_ID = "e11_composite_v1"

# Production social weight cap (IMP Sprint 16 / EPIC-015) — social disabled in P0
SOCIAL_WEIGHT_CAP = 0.05

# Soft voter contribution when present; absent ⇒ L4 weight 0 (chaos acceptance)
SOFT_VOTER_WEIGHT = 0.05

# Deterministic news reliability priors (no ML)
RELIABILITY: dict[str, float] = {
    "official_filing": 0.95,
    "exchange_announcement": 0.85,
    "tier1_news": 0.85,
    "news": 0.70,
    "unknown": 0.35,
    "social": 0.0,  # disabled
}

# Decay half-life (days) — news_* per E11 spec §6.3
NEWS_HALF_LIFE_DAYS = 3.0

REGISTRY_SENT: tuple[str, ...] = (
    "SENT_NEWS",
)
