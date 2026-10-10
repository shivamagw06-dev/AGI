"""Knowledge Publisher — publishes Institutional Knowledge Objects only. Never raw JSON."""

from __future__ import annotations

from app.contracts.iko import company_knowledge_view
from app.contracts.models import (
    Confidence,
    EntityRefs,
    KnowledgeMetadata,
    KnowledgeObject,
    KnowledgeObjectType,
    LearningEvent,
    PublicationEnvelope,
    PublishedBundle,
    Source,
    utc_now,
)
from app.kce.engine import KnowledgeConfidenceEngine
from app.kfe.engine import KnowledgeFreshnessEngine
from app.storage.db import KaipStore

PROVIDER_LEAK_KEYS = {
    "chart",
    "quote_summary",
    "yahoo_symbol",
    "raw",
    "provider",
    "marketCap",
    "trailingPE",
    "longName",
    "revenueGrowth",
    "regularMarketPrice",
}


class KnowledgePublisher:
    """Publishes versioned institutional knowledge into the IE-facing envelope."""

    def __init__(self, store: KaipStore) -> None:
        self.store = store
        self._last_bundle: PublishedBundle | None = None
        self.freshness = KnowledgeFreshnessEngine()
        self.confidence = KnowledgeConfidenceEngine()

    def publish(
        self,
        knowledge_objects: list[KnowledgeObject],
        learning_events: list[LearningEvent],
        ile_results: list | None = None,
    ) -> PublishedBundle:
        now = utc_now()
        published_kos: list[KnowledgeObject] = []
        published_learning: list[LearningEvent] = []
        ile_results = ile_results or []

        for ko in knowledge_objects:
            knowledge = {
                k: v
                for k, v in (ko.knowledge or ko.payload).items()
                if k not in PROVIDER_LEAK_KEYS
            }
            ko.knowledge = knowledge
            ko.payload = knowledge
            ko.published_at = now
            ko.updated_at = now
            self.store.insert_knowledge_object(ko)
            self.store.mark_published(ko.object_id, now)
            self._register_operate_metadata(ko, now)
            published_kos.append(ko)

        # Derive sector knowledge tips from company profiles (publication layer)
        derived_sector = self._derive_sector_knowledge(published_kos, now)
        for sko in derived_sector:
            self.store.insert_knowledge_object(sko)
            self.store.mark_published(sko.object_id, now)
            self._register_operate_metadata(sko, now)
            published_kos.append(sko)

        for le in learning_events:
            le.published_at = now
            self.store.insert_learning_event(le)
            self.store.mark_learning_published(le.learning_id, now)
            published_learning.append(le)

        envelope = self._build_envelope(published_kos, published_learning, ile_results, now)
        self.store.log_publication(envelope)

        bundle = PublishedBundle(
            knowledge_objects=published_kos,
            learning_events=published_learning,
            envelope=envelope,
            ile={
                "learning_event_count": len(published_learning),
                "sector_learning_count": len(envelope.sector_learning),
                "market_learning_count": len(envelope.market_learning),
                "memory_count": len(envelope.institutional_memory),
                "timeline_count": len(envelope.learning_timeline),
                "conflict_count": len(envelope.knowledge_conflicts),
            },
        )
        self._last_bundle = bundle
        return bundle

    def _register_operate_metadata(self, ko: KnowledgeObject, now) -> None:
        """Persist KFE + KCE registries at publish time (Operate layer)."""
        updated = now.isoformat() if hasattr(now, "isoformat") else str(now)
        self.freshness.register(
            self.store,
            object_type=ko.object_type.value,
            subject_key=ko.subject_key,
            updated_at=updated,
        )
        detail = (ko.metadata.confidence_detail if ko.metadata else None) or {}
        if ko.metadata and ko.metadata.confidence_pct is not None:
            from app.kce.engine import ConfidenceReport
            from app.contracts.models import Confidence as ConfEnum

            report = ConfidenceReport(
                confidence_pct=float(ko.metadata.confidence_pct),
                label=ko.metadata.confidence if isinstance(ko.metadata.confidence, ConfEnum) else ConfEnum.MEDIUM,
                sources=tuple(detail.get("sources") or [ko.metadata.source.value]),
                corroborating_sources=tuple(detail.get("corroborating_sources") or []),
                reasons=tuple(detail.get("reasons") or []),
                agreement_bonus=float(detail.get("agreement_bonus") or 0.0),
                object_type=ko.object_type.value,
                subject_key=ko.subject_key,
            )
            self.confidence.register(self.store, report)
        else:
            report = self.confidence.score_from_events(
                self.store,
                object_type=ko.object_type,
                primary_source=ko.metadata.source if ko.metadata else Source.DERIVED,
                source_event_ids=list(ko.source_event_ids or []),
                subject_key=ko.subject_key,
                knowledge=ko.knowledge or ko.payload,
            )
            self.confidence.register(self.store, report)

    def _derive_sector_knowledge(
        self, kos: list[KnowledgeObject], now
    ) -> list[KnowledgeObject]:
        out: list[KnowledgeObject] = []
        seen: set[str] = set()
        for ko in kos:
            if ko.object_type != KnowledgeObjectType.COMPANY_PROFILE:
                continue
            sector = ko.entity_refs.sector
            sector_key = ko.entity_refs.sector_key
            if not sector or not sector_key or sector_key in seen:
                continue
            seen.add(sector_key)
            previous = self.store.latest_ko(KnowledgeObjectType.SECTOR_KNOWLEDGE, sector_key)
            version = (previous.version + 1) if previous else 1
            leaders = list({*(previous.knowledge.get("leaders") if previous else []), ko.company_symbol})
            leaders = [x for x in leaders if x]
            knowledge = {
                "sector": sector,
                "sector_key": sector_key,
                "leaders": leaders,
                "industry_trends": [],
                "sector_valuation": {},
                "risks": [],
            }
            out.append(
                KnowledgeObject(
                    object_type=KnowledgeObjectType.SECTOR_KNOWLEDGE,
                    subject_key=sector_key,
                    sector_key=sector_key,
                    version=version,
                    previous_object_id=previous.object_id if previous else None,
                    changed_fields=["leaders"] if previous else ["sector"],
                    change_summary=f"Sector knowledge updated from {ko.company_symbol}",
                    knowledge=knowledge,
                    payload=knowledge,
                    metadata=KnowledgeMetadata(
                        source=Source.DERIVED,
                        confidence=Confidence.MEDIUM,
                        updated_at=now,
                        version=version,
                        verified=True,
                    ),
                    entity_refs=EntityRefs(sector=sector, sector_key=sector_key),
                    created_at=now,
                    updated_at=now,
                    published_at=now,
                )
            )
        return out

    def _build_envelope(
        self,
        kos: list[KnowledgeObject],
        learning: list[LearningEvent],
        ile_results: list,
        now,
    ) -> PublicationEnvelope:
        company_layer: list[KnowledgeObject] = []
        sector_layer: list[KnowledgeObject] = []
        market_layer: list[KnowledgeObject] = []

        for ko in kos:
            if ko.object_type == KnowledgeObjectType.SECTOR_KNOWLEDGE:
                sector_layer.append(ko)
            elif ko.object_type == KnowledgeObjectType.MARKET_KNOWLEDGE:
                market_layer.append(ko)
            elif ko.object_type in {
                KnowledgeObjectType.COMPANY_PROFILE,
                KnowledgeObjectType.MARKET_SNAPSHOT,
                KnowledgeObjectType.FINANCIAL_STATEMENT,
                KnowledgeObjectType.CORPORATE_EVENT,
                KnowledgeObjectType.CORPORATE_ACTION,
                KnowledgeObjectType.OWNERSHIP,
                KnowledgeObjectType.ANALYST_CONSENSUS,
                KnowledgeObjectType.NEWS_EVENT,
            }:
                company_layer.append(ko)

        sector_learning: list[dict] = []
        market_learning: list[dict] = []
        memory: list[dict] = []
        timeline: list[dict] = []
        conflicts: list[dict] = []
        for ile in ile_results:
            for item in ile.sector_learning:
                sector_learning.append(item.__dict__)
            for item in ile.market_learning:
                market_learning.append(item.__dict__)
            for item in ile.memory:
                memory.append(item.__dict__)
            for item in ile.timeline:
                timeline.append(item.__dict__)
            for item in ile.conflicts:
                conflicts.append(item.__dict__)

        return PublicationEnvelope(
            company_knowledge=company_layer,
            sector_knowledge=sector_layer,
            market_knowledge=market_layer,
            learning_events=learning,
            sector_learning=sector_learning,
            market_learning=market_learning,
            institutional_memory=memory,
            learning_timeline=timeline,
            knowledge_conflicts=conflicts,
            evidence_graph_ready=True,
            institutional_memory_ready=bool(memory) or True,
            published_at=now,
        )

    def company_view(self, symbol: str) -> dict | None:
        profile = self.store.get_company_profile(symbol)
        if not profile:
            return None
        meta = profile.get("metadata") or {}
        source = Source(meta.get("source", "derived"))
        return company_knowledge_view(
            profile["knowledge"],
            source=source,
            version=int(profile.get("version") or 1),
        )

    @property
    def last_bundle(self) -> PublishedBundle | None:
        return self._last_bundle
