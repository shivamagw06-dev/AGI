"""Step 6 — Market Learning: cross-sector themes."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.contracts.models import new_id, utc_now
from app.ile.impact import ImpactAssessment
from app.ile.materiality import ScoredChange
from app.storage.db import KaipStore

# Simple institutional theme map for Sprint 6.3
THEME_BENEFICIARIES: dict[str, list[str]] = {
    "Lower Rates": ["Banks", "Autos", "Housing", "Real Estate"],
    "USD Sensitive": ["IT Services", "Technology", "Export Companies"],
    "Risk On": ["Financials", "Industrials", "Consumer Cyclical"],
    "Commodity Strength": ["Energy", "Materials"],
}


@dataclass
class MarketLearning:
    learning_id: str
    theme: str
    observation: str
    beneficiaries: list[str] = field(default_factory=list)
    supporting_sectors: list[str] = field(default_factory=list)
    historical_confidence: str = "Medium"
    created_at: str = ""


class MarketLearningEngine:
    def __init__(self, store: KaipStore) -> None:
        self.store = store

    def maybe_learn(
        self,
        *,
        impact: ImpactAssessment,
        learnable: list[ScoredChange],
    ) -> list[MarketLearning]:
        if not learnable or not impact.sector:
            return []
        out: list[MarketLearning] = []
        themes = list(impact.themes)
        # Rate-sensitive price rallies can imply Lower Rates theme when Financials/Auto/RE rally
        if impact.sector in {"Financials", "Consumer Cyclical", "Real Estate"}:
            if any(s.change.field_name in {"price", "last_price"} and _up(s) for s in learnable):
                themes.append("Lower Rates")
        if impact.sector in {"Technology"} and any(
            s.change.field_name == "revenue_growth" and _up(s) for s in learnable
        ):
            themes.append("USD Sensitive")

        for theme in dict.fromkeys(themes):
            if theme not in THEME_BENEFICIARIES and theme not in {"Lower Rates", "USD Sensitive"}:
                # still record known SECTOR_THEMES as soft market learnings when reinforced
                beneficiaries = [impact.sector]
            else:
                beneficiaries = THEME_BENEFICIARIES.get(theme, [impact.sector])

            self.store.record_market_theme_signal(theme=theme, sector=impact.sector)
            sectors = self.store.market_theme_sectors(theme)
            if theme == "Lower Rates" and len(sectors) < 2:
                continue
            if theme != "Lower Rates" and len(sectors) < 1:
                continue

            confidence = "High" if len(sectors) >= 3 else "Medium"
            item = MarketLearning(
                learning_id=new_id(),
                theme=theme,
                observation=_theme_observation(theme),
                beneficiaries=beneficiaries,
                supporting_sectors=sectors,
                historical_confidence=confidence,
                created_at=utc_now().isoformat(),
            )
            self.store.insert_market_learning(item)
            out.append(item)
        return out


def _up(scored: ScoredChange) -> bool:
    try:
        return float(scored.change.new_value) > float(scored.change.previous_value)
    except (TypeError, ValueError):
        return False


def _theme_observation(theme: str) -> str:
    if theme == "Lower Rates":
        return "Multiple rate-sensitive sectors rallying — lower-rate regime benefiting Banks, Autos and Housing."
    if theme == "USD Sensitive":
        return "Export / USD-sensitive complex showing fundamental strength."
    return f"Market theme emerging: {theme}."
