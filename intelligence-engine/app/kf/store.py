"""Process-local KF1 knowledge object store."""

from __future__ import annotations

import datetime as _dt
from typing import Any

from app.kf.models import (
    CompanyKnowledgeObject,
    KnowledgeCoverage,
    KnowledgeKind,
    MacroKnowledgeObject,
    PredictionKnowledgeObject,
    ResearchExtractObject,
    SectorKnowledgeObject,
    ThemeKnowledgeObject,
)


class KfStore:
    def __init__(self) -> None:
        self.companies: dict[str, CompanyKnowledgeObject] = {}
        self.sectors: dict[str, SectorKnowledgeObject] = {}
        self.themes: dict[str, ThemeKnowledgeObject] = {}
        self.macros: dict[str, MacroKnowledgeObject] = {}
        self.predictions: dict[str, PredictionKnowledgeObject] = {}
        self.extracts: dict[str, ResearchExtractObject] = {}
        self.duplicate_reductions: int = 0
        self.relationships: int = 0

    def upsert_company(self, obj: CompanyKnowledgeObject) -> CompanyKnowledgeObject:
        key = obj.ticker.upper()
        if key in self.companies:
            self.duplicate_reductions += 1
        self.companies[key] = obj
        return obj

    def upsert_sector(self, obj: SectorKnowledgeObject) -> SectorKnowledgeObject:
        key = obj.sector_id.lower()
        if key in self.sectors:
            self.duplicate_reductions += 1
        self.sectors[key] = obj
        return obj

    def upsert_theme(self, obj: ThemeKnowledgeObject) -> ThemeKnowledgeObject:
        key = obj.theme_id.lower()
        if key in self.themes:
            self.duplicate_reductions += 1
        self.themes[key] = obj
        return obj

    def upsert_macro(self, obj: MacroKnowledgeObject) -> MacroKnowledgeObject:
        key = obj.macro_id.lower()
        if key in self.macros:
            self.duplicate_reductions += 1
        self.macros[key] = obj
        return obj

    def upsert_prediction(self, obj: PredictionKnowledgeObject) -> PredictionKnowledgeObject:
        key = obj.prediction_id
        if key in self.predictions:
            self.duplicate_reductions += 1
        self.predictions[key] = obj
        return obj

    def upsert_extract(self, obj: ResearchExtractObject) -> ResearchExtractObject:
        key = obj.document_id
        if key in self.extracts:
            self.duplicate_reductions += 1
        self.extracts[key] = obj
        return obj

    def get(self, kind: KnowledgeKind | str, key: str) -> Any | None:
        k = str(kind)
        key_u = key.upper() if k == "company" else key.lower()
        table = {
            "company": self.companies,
            "sector": self.sectors,
            "theme": self.themes,
            "macro": self.macros,
            "prediction": self.predictions,
            "research_extract": self.extracts,
        }.get(k)
        if table is None:
            return None
        return table.get(key_u) or table.get(key)

    def coverage(self, *, seeded: dict[str, int]) -> KnowledgeCoverage:
        confs: list[float] = []
        fresh: list[float] = []
        latest: _dt.datetime | None = None
        for obj in (
            list(self.companies.values())
            + list(self.sectors.values())
            + list(self.themes.values())
            + list(self.macros.values())
        ):
            confs.append(float(obj.meta.confidence))
            fresh.append(float(obj.meta.freshness))
            if latest is None or obj.meta.updated_at > latest:
                latest = obj.meta.updated_at
        return KnowledgeCoverage(
            companies_covered=len(self.companies),
            companies_seeded=seeded.get("companies", 0),
            sector_coverage=len(self.sectors),
            sectors_seeded=seeded.get("sectors", 0),
            theme_coverage=len(self.themes),
            themes_seeded=seeded.get("themes", 0),
            macro_coverage=len(self.macros),
            macros_seeded=seeded.get("macros", 0),
            research_extracts=len(self.extracts),
            prediction_coverage=len(self.predictions),
            relationship_count=self.relationships,
            avg_confidence=round(sum(confs) / len(confs), 4) if confs else 0.0,
            avg_freshness=round(sum(fresh) / len(fresh), 4) if fresh else 0.0,
            duplicate_reductions=self.duplicate_reductions,
            last_updated=latest.isoformat() if latest else None,
        )
