"""Step 5 — Sector Learning: patterns across supporting companies."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.contracts.models import Importance, new_id, utc_now
from app.ile.materiality import ScoredChange
from app.storage.db import KaipStore


@dataclass
class SectorLearning:
    learning_id: str
    sector: str
    sector_key: str
    observation: str
    supporting_companies: list[str] = field(default_factory=list)
    field_name: str | None = None
    importance: str = "Medium"
    created_at: str = ""


class SectorLearningEngine:
    """Emit sector learning when ≥2 peers show the same material field direction."""

    def __init__(self, store: KaipStore) -> None:
        self.store = store

    def maybe_learn(
        self,
        *,
        sector: str | None,
        company_symbol: str | None,
        learnable: list[ScoredChange],
    ) -> list[SectorLearning]:
        if not sector or not company_symbol or not learnable:
            return []
        sector_key = sector.lower().replace(" ", "_")
        out: list[SectorLearning] = []
        for scored in learnable:
            if scored.materiality.category not in {"Financial Performance", "Valuation", "Ownership"}:
                continue
            direction = _direction(scored.change.previous_value, scored.change.new_value)
            if direction == 0:
                continue
            # Record this company's signal
            self.store.record_sector_signal(
                sector_key=sector_key,
                field_name=scored.change.field_name,
                direction=direction,
                company_symbol=company_symbol,
            )
            supporters = self.store.sector_signal_supporters(
                sector_key=sector_key,
                field_name=scored.change.field_name,
                direction=direction,
                limit=10,
            )
            if len(supporters) < 2:
                continue
            observation = _sector_observation(scored.change.field_name, direction, sector)
            importance = (
                Importance.HIGH.value
                if scored.materiality.importance == "High" and len(supporters) >= 3
                else scored.materiality.importance
            )
            item = SectorLearning(
                learning_id=new_id(),
                sector=sector,
                sector_key=sector_key,
                observation=observation,
                supporting_companies=supporters,
                field_name=scored.change.field_name,
                importance=importance,
                created_at=utc_now().isoformat(),
            )
            self.store.insert_sector_learning(item)
            out.append(item)
        return out


def _direction(prev: Any, new: Any) -> int:
    try:
        p = float(prev)
        n = float(new)
    except (TypeError, ValueError):
        return 0
    if n > p:
        return 1
    if n < p:
        return -1
    return 0


def _sector_observation(field: str, direction: int, sector: str) -> str:
    if field in {"pat_margin", "ebitda_margin"}:
        return (
            "Industry-wide margin compression emerging."
            if direction < 0
            else f"{sector} sector margins expanding across multiple companies."
        )
    if field == "revenue_growth":
        return (
            f"{sector} sector showing broad revenue acceleration."
            if direction > 0
            else f"{sector} sector revenue growth slowing across multiple companies."
        )
    if field in {"pe", "pe_ratio"}:
        return (
            f"{sector} sector valuation multiples expanding."
            if direction > 0
            else f"{sector} sector valuation multiples compressing."
        )
    return f"{sector} sector pattern detected on {field.replace('_', ' ')}."
