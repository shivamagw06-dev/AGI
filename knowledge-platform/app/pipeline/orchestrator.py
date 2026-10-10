"""End-to-end KAIP acquisition → IKO → Institutional Learning pipeline."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.collectors.base import BaseCollector
from app.config.settings import Settings
from app.contracts.models import (
    EntityRefs,
    KnowledgeObject,
    KnowledgeObjectType,
    LearningEvent,
    PublishedBundle,
    RawEvent,
    ValidationStatus,
)
from app.entity_resolution.resolver import EntityResolver
from app.ile.engine import IleResult, InstitutionalLearningEngine
from app.knowledge_builder.builder import KnowledgeObjectBuilder
from app.normalizers.canonical import CanonicalNormalizer
from app.publisher.publisher import KnowledgePublisher
from app.relationships.builder import RelationshipBuilder
from app.storage.db import KaipStore
from app.validators.gates import ValidationGate

logger = logging.getLogger("kaip.pipeline")


@dataclass
class PipelineResult:
    raw_events: list[RawEvent] = field(default_factory=list)
    accepted: list[RawEvent] = field(default_factory=list)
    rejected: list[RawEvent] = field(default_factory=list)
    duplicates: list[RawEvent] = field(default_factory=list)
    knowledge_objects: list[KnowledgeObject] = field(default_factory=list)
    learning_events: list[LearningEvent] = field(default_factory=list)
    ile_results: list[IleResult] = field(default_factory=list)
    published: PublishedBundle | None = None


class AcquisitionPipeline:
    def __init__(self, store: KaipStore, settings: Settings) -> None:
        self.store = store
        self.settings = settings
        self.validator = ValidationGate(store, duplicate_window_seconds=settings.duplicate_window_seconds)
        self.normalizer = CanonicalNormalizer()
        self.resolver = EntityResolver(store)
        self.builder = KnowledgeObjectBuilder(store)
        self.relationships = RelationshipBuilder(store)
        self.ile = InstitutionalLearningEngine(store)
        self.publisher = KnowledgePublisher(store)

    def ingest_events(self, events: list[RawEvent]) -> PipelineResult:
        result = PipelineResult(raw_events=list(events))
        built: list[KnowledgeObject] = []
        learning: list[LearningEvent] = []
        ile_bundle: list[IleResult] = []

        for event in events:
            self.store.insert_raw_event(event)
            validated = self.validator.validate(event)
            self.store.update_raw_validation(validated)

            if validated.validation_status == ValidationStatus.REJECTED:
                result.rejected.append(validated)
                continue
            if validated.validation_status == ValidationStatus.DUPLICATE:
                result.duplicates.append(validated)
                continue

            result.accepted.append(validated)
            for canonical in self.normalizer.normalize(validated):
                try:
                    object_type = KnowledgeObjectType(canonical.get("object_type"))
                except Exception:
                    continue

                entity, subject = self._resolve_subject(object_type, canonical, validated)
                previous = self.store.latest_ko(object_type, subject)
                ko = self.builder.build(
                    canonical=canonical,
                    entity_refs=entity,
                    source_event_ids=[validated.event_id],
                    source=validated.source,
                    collector_id=validated.collector_id,
                )
                if ko is None:
                    continue
                self.relationships.apply(ko)

                # Sprint 6.3 — Institutional Learning Engine
                ile_result = self.ile.learn(ko, previous)
                ile_bundle.append(ile_result)
                learning.extend(ile_result.learning_events)
                built.append(ko)

        if built or learning:
            result.published = self.publisher.publish(
                built,
                learning,
                ile_results=ile_bundle,
            )
            result.knowledge_objects = list(result.published.knowledge_objects)
            result.learning_events = list(result.published.learning_events)
            result.ile_results = ile_bundle
        else:
            result.knowledge_objects = built
            result.learning_events = learning
            result.ile_results = ile_bundle
        return result

    def _resolve_subject(
        self,
        object_type: KnowledgeObjectType,
        canonical: dict[str, Any],
        event: RawEvent,
    ) -> tuple[EntityRefs, str]:
        if object_type == KnowledgeObjectType.SECTOR_KNOWLEDGE:
            sector = canonical.get("sector") or "Unknown"
            sector_key = canonical.get("sector_key") or sector.lower().replace(" ", "_")
            return EntityRefs(sector=sector, sector_key=sector_key), sector_key
        if object_type == KnowledgeObjectType.MARKET_KNOWLEDGE:
            market_key = canonical.get("market_key") or "india_equity"
            return EntityRefs(market_key=market_key), market_key

        entity = self.resolver.resolve(
            canonical.get("company_symbol") or event.company_symbol or "",
            hints={
                "company_name": canonical.get("company_name"),
                "sector": canonical.get("sector"),
                "industry": canonical.get("industry"),
            },
        )
        subject = entity.company_symbol or canonical.get("company_symbol") or ""
        return entity, subject

    def run_collector(self, collector: BaseCollector) -> PipelineResult:
        logger.info("collecting collector_id=%s", collector.collector_id)
        return self.ingest_events(collector.collect())

    def status(self) -> dict[str, Any]:
        return {
            "raw_events": self.store.count_raw_events(),
            "published_knowledge_objects": self.store.count_published_kos(),
        }
