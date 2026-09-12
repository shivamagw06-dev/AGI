"""Historical acquisition pipeline — bulk / incremental ingest into Historical Knowledge Store."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from app.builders.historical import HistoricalKnowledgeBuilder
from app.collectors.base import BaseHistoricalCollector
from app.contracts.models import (
    HistoricalKnowledgeObject,
    IngestionRun,
    RawHistoricalEvent,
    ValidationStatus,
    utc_now,
)
from app.entity_resolution.resolver import HistoricalEntityResolver
from app.normalizers.canonical import HistoricalNormalizer
from app.storage.db import HipStore
from app.timeline import traces
from app.validators.gates import HistoricalValidationGate

logger = logging.getLogger("hip.pipeline")


@dataclass
class HistoricalPipelineResult:
    run_id: str
    raw_events: list[RawHistoricalEvent] = field(default_factory=list)
    accepted: list[RawHistoricalEvent] = field(default_factory=list)
    rejected: list[RawHistoricalEvent] = field(default_factory=list)
    duplicates: list[RawHistoricalEvent] = field(default_factory=list)
    objects: list[HistoricalKnowledgeObject] = field(default_factory=list)


class HistoricalAcquisitionPipeline:
    def __init__(self, store: HipStore) -> None:
        self.store = store
        self.validator = HistoricalValidationGate()
        self.normalizer = HistoricalNormalizer()
        self.resolver = HistoricalEntityResolver(store)
        self.builder = HistoricalKnowledgeBuilder(store)

    def run_collector(
        self,
        collector: BaseHistoricalCollector,
        *,
        mode: str = "bootstrap",
        symbols: list[str] | None = None,
    ) -> HistoricalPipelineResult:
        span = traces.begin(
            "historical_ingestion",
            meta={"collector_id": collector.collector_id, "mode": mode, "symbols": symbols or []},
        )
        run = IngestionRun(
            mode=mode,
            collector_id=collector.collector_id,
            symbols=symbols or [],
            categories=list(collector.categories),
        )
        self.store.start_run(run)
        events = collector.collect(ingestion_run_id=run.run_id)
        result = self.ingest_events(events, run=run)
        run.ended_at = utc_now()
        run.status = "completed"
        run.raw_accepted = len(result.accepted)
        run.raw_rejected = len(result.rejected)
        run.objects_written = len(result.objects)
        run.detail = {
            "duplicates": len(result.duplicates),
            "raw_total": len(result.raw_events),
        }
        self.store.finish_run(run)
        result.run_id = run.run_id
        traces.end(
            span,
            output={
                "run_id": result.run_id,
                "accepted": len(result.accepted),
                "objects": len(result.objects),
                "duplicates": len(result.duplicates),
            },
        )
        return result

    def ingest_events(
        self,
        events: list[RawHistoricalEvent],
        *,
        run: IngestionRun | None = None,
    ) -> HistoricalPipelineResult:
        run_id = run.run_id if run else None
        result = HistoricalPipelineResult(run_id=run_id or "")
        result.raw_events = list(events)

        for event in events:
            if event.ingestion_run_id is None and run_id:
                event.ingestion_run_id = run_id

            if self.store.checksum_exists(event.checksum):
                event.validation_status = ValidationStatus.DUPLICATE
                event.validation_errors = ["duplicate_checksum"]
                result.duplicates.append(event)
                continue

            inserted = self.store.insert_raw(event)
            if not inserted:
                event.validation_status = ValidationStatus.DUPLICATE
                event.validation_errors = ["duplicate_checksum"]
                result.duplicates.append(event)
                continue

            validated = self.validator.validate(event)
            self.store.update_raw_validation(validated)

            if validated.validation_status == ValidationStatus.REJECTED:
                result.rejected.append(validated)
                continue

            result.accepted.append(validated)
            for canonical in self.normalizer.normalize(validated):
                entity = self.resolver.resolve(canonical, source=validated.source)
                ko = self.builder.build(
                    canonical=canonical,
                    entity_refs=entity,
                    source=validated.source,
                    collector_id=validated.collector_id,
                    ingestion_run_id=run_id,
                )
                if ko is None:
                    continue
                try:
                    self.store.insert_historical_object(ko)
                    result.objects.append(ko)
                except Exception:
                    logger.exception(
                        "failed to insert historical object type=%s date=%s",
                        ko.object_type,
                        ko.effective_date,
                    )
        return result

    def bootstrap_all(
        self,
        collectors: dict[str, BaseHistoricalCollector],
        *,
        symbols: list[str] | None = None,
    ) -> dict[str, Any]:
        summary = {}
        for cid, collector in collectors.items():
            res = self.run_collector(collector, mode="bootstrap", symbols=symbols)
            summary[cid] = {
                "run_id": res.run_id,
                "accepted": len(res.accepted),
                "rejected": len(res.rejected),
                "duplicates": len(res.duplicates),
                "objects": len(res.objects),
            }
        return summary
