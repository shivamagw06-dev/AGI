"""FAA pipeline — Discovery → Fetch → Process → Index → notify FRE."""

from __future__ import annotations

import time
from typing import Any

from app.faa.cache import DocumentCache
from app.faa.discovery import DiscoveryService
from app.faa.fetch import FetchService
from app.faa.http_client import HttpClient
from app.faa.index_service import IndexService
from app.faa.models import AcquisitionResult, FaaMetrics, utc_now
from app.faa.processing import ProcessingService
from app.faa.store import FaaStore


class FaaPipeline:
    def __init__(
        self,
        *,
        cache: DocumentCache | None = None,
        store: FaaStore | None = None,
        fre: Any | None = None,
        aoi: Any | None = None,
        live_fetch: bool = False,
        pdf_enabled: bool = True,
        metrics: FaaMetrics | None = None,
        max_workers: int = 6,
        connectors: dict | None = None,
    ) -> None:
        self.cache = cache or DocumentCache()
        self.store = store or FaaStore()
        self.fre = fre
        self.aoi = aoi
        self.live_fetch = live_fetch
        self.metrics = metrics or FaaMetrics()
        self.max_workers = max_workers
        self.client = HttpClient()
        self.discovery = DiscoveryService(live_fetch=live_fetch, connectors=connectors)
        self.fetch = FetchService(
            self.cache,
            live_fetch=live_fetch,
            pdf_enabled=pdf_enabled,
            client=self.client,
            connectors=self.discovery.connectors,
            max_workers=max_workers,
        )
        self.processing = ProcessingService()
        self.index = IndexService(self.cache, fre=fre, store=self.store)
        self.metrics.worker_count = max_workers

    def bind_fre(self, fre: Any) -> None:
        self.fre = fre
        self.index.bind_fre(fre)

    def acquire_for_query(self, query: str, *, limit: int = 24) -> AcquisitionResult:
        result = AcquisitionResult(query=query, live_fetch=self.live_fetch, parallel_workers=self.max_workers)
        timings: dict[str, float] = {}

        t0 = time.perf_counter()
        tasks, candidates = self.discovery.discover(query, aoi=self.aoi, limit=limit)
        timings["discovery_ms"] = round((time.perf_counter() - t0) * 1000, 2)
        result.discovered = len(candidates)
        result.candidates = [c.to_dict() for c in candidates]
        self.metrics.discovery_runs += 1
        self.metrics.candidates_found += len(candidates)
        self.metrics.queue_size = len(candidates)

        t1 = time.perf_counter()
        fetched = self.fetch.fetch_many(candidates)
        timings["fetch_ms"] = round((time.perf_counter() - t1) * 1000, 2)
        self.metrics.downloads_attempted += len(fetched)
        self.metrics.avg_fetch_ms = self.fetch.avg_fetch_ms
        self.metrics.rate_limit_events = self.client.rate_limiter.rate_limit_events

        errors = []
        succeeded = []
        for f in fetched:
            if f.skipped:
                result.skipped_cached += 1
                self.metrics.cache_hits += 1
            elif f.error:
                result.failed += 1
                self.metrics.downloads_failed += 1
                errors.append(f"{f.url}: {f.error}")
            else:
                succeeded.append(f)
                self.metrics.downloads_succeeded += 1

        t2 = time.perf_counter()
        processed = self.processing.process(succeeded)
        timings["parse_ms"] = round((time.perf_counter() - t2) * 1000, 2)
        result.processed = len(processed)
        self.metrics.processed += len(processed)
        self.metrics.avg_parse_ms = self.processing.avg_parse_ms
        if len(succeeded) > len(processed):
            self.metrics.parse_failures += len(succeeded) - len(processed)

        indexed_meta: dict[str, Any] = {}
        if processed and self.fre is not None:
            t3 = time.perf_counter()
            indexed_meta = self.index.index(processed, fetched=succeeded)
            timings["index_ms"] = round((time.perf_counter() - t3) * 1000, 2)
            result.indexed_to_fre = int(indexed_meta.get("indexed") or 0)
            self.metrics.indexed_to_fre += result.indexed_to_fre
            self.metrics.avg_embed_ms = self.index.avg_embed_ms
            result.versions = list(indexed_meta.get("versions") or [])
            if result.indexed_to_fre:
                self.metrics.last_success_at = utc_now().isoformat()
        elif processed and self.fre is None:
            errors.append("fre_unbound_not_indexed")

        result.fetched = len(succeeded)
        result.documents = [d.to_dict() for d in processed]
        result.errors = errors
        result.timings = timings
        result.finished_at = utc_now()
        self.metrics.last_run_at = result.finished_at.isoformat()
        self.metrics.queue_size = 0
        if tasks and result.candidates:
            result.candidates[0] = {**result.candidates[0], "tasks_planned": len(tasks)}
        return result
