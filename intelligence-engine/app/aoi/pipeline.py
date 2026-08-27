"""AOI acquisition pipeline — discover → fetch → parse → extract → validate → publish."""

from __future__ import annotations

import datetime as _dt
import time
from typing import Any

from app.aoi.connectors.factory import build_connectors
from app.aoi.diffs import detect_diffs
from app.aoi.digest import build_daily_digest
from app.aoi.downloader import Downloader
from app.aoi.flags import AoiFlags
from app.aoi.gaps import detect_gaps
from app.aoi.graph import upsert_company_graph
from app.aoi.models import ConnectorHealth, DocumentArtifact
from app.aoi.parsers import parse_artifact
from app.aoi.publish import publish_artifact
from app.aoi.quality import score_all
from app.aoi.registry import CompanyRegistry
from app.aoi.scheduler import Scheduler
from app.aoi.store import AoiStore
from app.aoi.validation import validate_facts
from app.aoi.versioning import append_version, label_for_artifact


class AoiPipeline:
    def __init__(
        self,
        *,
        flags: AoiFlags,
        store: AoiStore | None = None,
        registry: CompanyRegistry | None = None,
        kip: Any | None = None,
        kc: Any | None = None,
        kf: Any | None = None,
        eve: Any | None = None,
    ) -> None:
        self.flags = flags
        self.store = store or AoiStore()
        self.registry = registry or CompanyRegistry()
        self.kip = kip
        self.kc = kc
        self.kf = kf
        self.eve = eve
        self.connectors = build_connectors(flags)
        self.scheduler = Scheduler(self.store)
        self.downloader = Downloader(self.store)
        self.connector_health: dict[str, ConnectorHealth] = {}
        self._seeded = False

    def ensure_registry(self) -> dict[str, int]:
        if not self._seeded:
            stats = self.registry.seed_default_universes()
            self._seeded = True
            self.store.audit_event("registry_seeded", detail=str(stats))
            return stats
        return {
            "entries": len(list(self.registry.all())),
            "nifty_50": len(self.registry.nifty50()),
        }

    def run(
        self,
        *,
        connector_ids: list[str] | None = None,
        limit_per_connector: int | None = 40,
        publish: bool | None = None,
    ) -> dict[str, Any]:
        """Execute an acquisition cycle (idempotent / incremental)."""
        reg = self.ensure_registry()
        due = self.scheduler.enqueue_due(cadence_filter="all")
        selected = connector_ids or [j.connector_id for j in due]
        # unique preserve order
        seen: set[str] = set()
        ordered = []
        for cid in selected:
            if cid in seen or cid not in self.connectors:
                continue
            seen.add(cid)
            ordered.append(cid)

        totals = {
            "discovered": 0,
            "downloaded": 0,
            "parsed": 0,
            "extracted_facts": 0,
            "validated_facts": 0,
            "published": 0,
            "skipped": 0,
            "failed": 0,
            "diffs": 0,
        }

        for cid in ordered:
            connector = self.connectors[cid]
            t0 = time.perf_counter()
            health = ConnectorHealth(connector_id=cid, name=connector.name, enabled=True, status="ok")
            try:
                updates = connector.fetch_updates(self.registry, known_checksums=self.store.known_checksums())
                if limit_per_connector is not None:
                    updates = updates[: max(0, int(limit_per_connector))]
                totals["discovered"] += len(updates)
                health.discovered = len(updates)
                for art in updates:
                    if art.status == "skipped":
                        totals["skipped"] += 1
                        continue
                    self._process_one(connector, art, totals, publish=self.flags.aoi_publish if publish is None else publish)
                health.downloaded = totals["downloaded"]
                health.last_success_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
            except Exception as exc:
                health.status = "error"
                health.error = str(exc)
                health.failed += 1
                self.store.metrics.errors += 1
            health.latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            health.last_run_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
            self.connector_health[cid] = health
            self.store.metrics.connector_latency_ms[cid] = health.latency_ms or 0.0
            for job in self.scheduler.list_jobs():
                if job.connector_id == cid:
                    self.scheduler.mark_run(job.job_id)

        qualities = score_all(self.store, self.registry)
        gaps = detect_gaps(self.store, self.registry)
        digest = build_daily_digest(self.store)
        return {
            "registry": reg,
            "connectors_run": ordered,
            "totals": totals,
            "quality_avg": round(sum(q.overall for q in qualities) / len(qualities), 2) if qualities else 0.0,
            "gaps": len(gaps),
            "digest_id": digest.digest_id,
            "coverage": self.store.coverage_counts(),
            "observability": self.store.metrics.model_dump(mode="json"),
        }

    def _process_one(self, connector, art: DocumentArtifact, totals: dict[str, int], *, publish: bool) -> None:
        downloaded = self.downloader.download(connector, art)
        if downloaded.status == "skipped":
            totals["skipped"] += 1
            return
        if downloaded.status == "failed":
            totals["failed"] += 1
            return
        totals["downloaded"] += 1

        try:
            parsed = connector.parse(downloaded)
            parsed = parse_artifact(parsed)
            self.store.upsert_artifact(parsed)
            self.store.metrics.parser_success += 1
            totals["parsed"] += 1
        except Exception as exc:
            downloaded.status = "failed"
            downloaded.error = f"parse:{exc}"
            self.store.upsert_artifact(downloaded)
            self.store.metrics.parser_failed += 1
            totals["failed"] += 1
            return

        try:
            facts = connector.extract(parsed)
            facts = connector.transform(facts, parsed)
            facts = validate_facts(facts, parsed)
            facts = connector.validate(facts, parsed)
            totals["extracted_facts"] += len(facts)
            totals["validated_facts"] += len(facts)
            self.store.metrics.extraction_success += len(facts)
            self.store.metrics.validation_success += len(facts)

            if parsed.company_id:
                diffs = detect_diffs(
                    self.store,
                    company_id=parsed.company_id,
                    new_facts=facts,
                    source_document_id=parsed.artifact_id,
                )
                totals["diffs"] += len(diffs)
                self.store.add_facts(facts)
                upsert_company_graph(
                    self.store,
                    self.registry,
                    company_id=parsed.company_id,
                    facts=facts,
                    document_id=parsed.artifact_id,
                )
                append_version(
                    self.store,
                    company_id=parsed.company_id,
                    fact_ids=[f.fact_id for f in facts],
                    artifact_ids=[parsed.artifact_id],
                    label=label_for_artifact(parsed.doc_type, parsed.title),
                    change_summary=[d.change_type + ":" + d.field for d in diffs] or [f"ingest:{parsed.doc_type}"],
                )
            else:
                self.store.add_facts(facts)

            parsed.status = "validated"
            self.store.upsert_artifact(parsed)
        except Exception as exc:
            parsed.status = "failed"
            parsed.error = f"extract:{exc}"
            self.store.upsert_artifact(parsed)
            totals["failed"] += 1
            self.store.metrics.errors += 1
            return

        if publish:
            pub = publish_artifact(
                artifact=parsed,
                facts=facts,
                registry=self.registry,
                kip=self.kip,
                kc=self.kc,
                kf=self.kf,
                eve=self.eve,
            )
            if pub.get("published"):
                totals["published"] += 1
                self.store.metrics.knowledge_updates += 1
                parsed.status = "published"
                parsed.published_at = _dt.datetime.now(_dt.timezone.utc).isoformat()
                self.store.upsert_artifact(parsed)
