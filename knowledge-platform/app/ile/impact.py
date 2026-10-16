"""Steps 3 — Relationship + Impact Assessment Engine."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.contracts.models import EntityRefs, KnowledgeObject
from app.ile.materiality import ScoredChange
from app.storage.db import KaipStore


# Theme tags implied by company/sector characteristics
SECTOR_THEMES: dict[str, list[str]] = {
    "Technology": ["Export Companies", "USD Sensitive", "Growth"],
    "Financials": ["Rate Sensitive", "Domestic Demand"],
    "Energy": ["Commodity", "Global Macro"],
    "Consumer Cyclical": ["Domestic Demand", "Rate Sensitive"],
    "Consumer Defensive": ["Domestic Demand"],
    "Real Estate": ["Rate Sensitive", "Housing"],
    "Industrials": ["Capex Cycle"],
    "Healthcare": ["Defensive Growth"],
}


@dataclass
class ImpactAssessment:
    company_symbol: str | None
    affected: list[str] = field(default_factory=list)
    relationship_paths: list[list[str]] = field(default_factory=list)
    themes: list[str] = field(default_factory=list)
    sector: str | None = None
    industry: str | None = None
    indexes: list[str] = field(default_factory=list)
    peers: list[str] = field(default_factory=list)
    relationship_changes: list[dict] = field(default_factory=list)


class ImpactAssessmentEngine:
    def __init__(self, store: KaipStore) -> None:
        self.store = store

    def assess(
        self,
        ko: KnowledgeObject,
        learnable: list[ScoredChange],
        entity: EntityRefs | None = None,
    ) -> ImpactAssessment:
        refs = entity or ko.entity_refs
        symbol = ko.company_symbol or refs.company_symbol
        sector = refs.sector
        industry = refs.industry
        indexes = list(refs.indexes or [])
        peers = list(refs.peers or [])

        affected: list[str] = ["Company"]
        categories = {s.materiality.category for s in learnable}
        if any(c.startswith("Financial") for c in categories) or "Financial Performance" in categories:
            affected.extend(["Sector", "Valuation"])
        if "Valuation" in categories:
            affected.append("Valuation")
        if "Ownership" in categories:
            affected.append("Ownership")
        if "Market" in categories:
            affected.extend(["Market", "Valuation"])
        if "Corporate" in categories:
            affected.append("Corporate")
        if sector:
            affected.append("Sector")
        affected = list(dict.fromkeys(affected))

        paths: list[list[str]] = []
        if symbol and industry and sector:
            path = [symbol, industry, sector]
            for idx in indexes:
                path.append(idx)
            for theme in SECTOR_THEMES.get(sector, []):
                path.append(theme)
            paths.append(path)
        elif symbol and sector:
            paths.append([symbol, sector, *indexes])

        themes = list(SECTOR_THEMES.get(sector or "", []))
        rel_changes: list[dict] = []
        for scored in learnable:
            rel_changes.append(
                {
                    "company_symbol": symbol,
                    "field_name": scored.change.field_name,
                    "affected": affected,
                    "sector": sector,
                    "industry": industry,
                    "indexes": indexes,
                    "peers": peers,
                    "themes": themes,
                    "path": paths[0] if paths else [symbol],
                    "materiality_score": scored.materiality.score,
                }
            )
            # Persist relationship tip edges already exist; record change log
            if symbol:
                self.store.insert_relationship_change(
                    company_symbol=symbol,
                    field_name=scored.change.field_name,
                    detail={
                        "affected": affected,
                        "path": paths[0] if paths else [symbol],
                        "themes": themes,
                        "score": scored.materiality.score,
                    },
                )

        return ImpactAssessment(
            company_symbol=symbol,
            affected=affected,
            relationship_paths=paths,
            themes=themes,
            sector=sector,
            industry=industry,
            indexes=indexes,
            peers=peers,
            relationship_changes=rel_changes,
        )
