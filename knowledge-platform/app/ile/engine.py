"""Institutional Learning Engine — orchestrates compare → learn → memory → publish artifacts."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.contracts.models import KnowledgeObject, LearningEvent
from app.ile.comparator import KnowledgeComparator
from app.ile.contradictions import ContradictionEngine, KnowledgeConflict
from app.ile.impact import ImpactAssessment, ImpactAssessmentEngine
from app.ile.learning_builder import LearningEventBuilder
from app.ile.market_learning import MarketLearning, MarketLearningEngine
from app.ile.materiality import MaterialityEngine, ScoredChange
from app.ile.memory import InstitutionalMemoryWriter, MemoryEntry
from app.ile.sector_learning import SectorLearning, SectorLearningEngine
from app.ile.timeline import LearningTimelineWriter, TimelineEntry
from app.storage.db import KaipStore


@dataclass
class IleResult:
    ignored: list[ScoredChange] = field(default_factory=list)
    learnable: list[ScoredChange] = field(default_factory=list)
    learning_events: list[LearningEvent] = field(default_factory=list)
    impact: ImpactAssessment | None = None
    sector_learning: list[SectorLearning] = field(default_factory=list)
    market_learning: list[MarketLearning] = field(default_factory=list)
    conflicts: list[KnowledgeConflict] = field(default_factory=list)
    memory: list[MemoryEntry] = field(default_factory=list)
    timeline: list[TimelineEntry] = field(default_factory=list)


class InstitutionalLearningEngine:
    def __init__(self, store: KaipStore) -> None:
        self.store = store
        self.comparator = KnowledgeComparator()
        self.materiality = MaterialityEngine()
        self.impact_engine = ImpactAssessmentEngine(store)
        self.learning_builder = LearningEventBuilder()
        self.sector_engine = SectorLearningEngine(store)
        self.market_engine = MarketLearningEngine(store)
        self.contradiction_engine = ContradictionEngine()
        self.memory_writer = InstitutionalMemoryWriter()
        self.timeline_writer = LearningTimelineWriter()

    def learn(self, ko: KnowledgeObject, previous: KnowledgeObject | None) -> IleResult:
        comparison = self.comparator.compare(ko, previous)
        scored = self.materiality.evaluate(comparison)
        result = IleResult(ignored=scored.ignored, learnable=scored.learnable)

        if not scored.learnable:
            return result

        impact = self.impact_engine.assess(ko, scored.learnable, entity=ko.entity_refs)
        result.impact = impact

        events = self.learning_builder.build(ko, scored.learnable, impact)
        result.learning_events = events

        result.sector_learning = self.sector_engine.maybe_learn(
            sector=impact.sector,
            company_symbol=ko.company_symbol,
            learnable=scored.learnable,
        )
        result.market_learning = self.market_engine.maybe_learn(
            impact=impact,
            learnable=scored.learnable,
        )
        result.conflicts = self.contradiction_engine.detect(ko, scored.learnable)
        result.memory = self.memory_writer.write(ko, scored.learnable, impact)
        result.timeline = self.timeline_writer.write(ko, scored.learnable)

        # Persist memory / timeline / conflicts (learning events persisted by publisher)
        for mem in result.memory:
            self.store.insert_institutional_memory(mem)
        for entry in result.timeline:
            self.store.insert_timeline_entry(entry)
        for conflict in result.conflicts:
            self.store.insert_knowledge_conflict(conflict)

        return result
