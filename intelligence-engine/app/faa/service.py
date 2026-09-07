"""FAA service facade — production live acquisition; never answers/reasons."""

from __future__ import annotations

import time
from typing import Any

from app.core.config import get_settings
from app.faa.cache import DocumentCache
from app.faa.connectors import build_connectors
from app.faa.connectors.search_api import available_search_providers
from app.faa.web_enrichment import enrichment_status
from app.faa.flags import FaaFlags
from app.faa.models import FaaMetrics
from app.faa.pipeline import FaaPipeline
from app.faa.scheduler import WATCHLIST_QUERIES, FaaScheduler
from app.faa.store import FaaStore


class FaaService:
    """Finance Acquisition Agent — gather/update public data only."""

    def __init__(
        self,
        *,
        flags: FaaFlags | None = None,
        fre: Any | None = None,
        aoi: Any | None = None,
        cache: DocumentCache | None = None,
        store: FaaStore | None = None,
    ) -> None:
        self.flags = flags or FaaFlags.from_settings(get_settings())
        self.fre = fre
        self.aoi = aoi
        self.cache = cache or DocumentCache()
        self.store = store or FaaStore()
        self.metrics = FaaMetrics()
        self.scheduler = FaaScheduler()
        self.connectors = build_connectors(live_fetch=self.flags.faa_live_fetch)
        workers = int(self.flags.faa_max_workers or getattr(get_settings(), "faa_max_workers", 6) or 6)
        self.pipeline = FaaPipeline(
            cache=self.cache,
            store=self.store,
            fre=fre,
            aoi=aoi,
            live_fetch=self.flags.faa_live_fetch,
            pdf_enabled=self.flags.faa_pdf,
            metrics=self.metrics,
            max_workers=workers,
            connectors=self.connectors,
        )

    def bind(self, **engines: Any) -> None:
        if "fre" in engines:
            self.fre = engines["fre"]
            self.pipeline.bind_fre(self.fre)
        if "aoi" in engines:
            self.aoi = engines["aoi"]
            self.pipeline.aoi = self.aoi

    def _require(self) -> None:
        if not self.flags.faa:
            raise RuntimeError("FAA disabled")

    def health(self) -> dict[str, Any]:
        from app.faa.background import schedule_status

        connector_health = [c.health() for c in self.connectors.values()]
        degraded = [c["connector_id"] for c in connector_health if c.get("status") != "ok"]
        return {
            "status": "ok" if self.flags.faa else "disabled",
            "layer": "Finance Acquisition Agent",
            "programme": "FAA",
            "version": "faa-v1.3.5",
            "architecture_status": "v1.0.1 LOCKED",
            "position": "upstream_of_fre",
            "does_not_answer": True,
            "never_reasons": True,
            "feeds": ["fre"],
            "no_redesign": ["fre", "aoi", "eve", "cae", "ask_agi"],
            "services": ["discovery", "fetch", "processing", "index"],
            "invariants": [
                "never_answer_user",
                "never_reason",
                "dedupe_by_url_etag_checksum",
                "immutable_versions",
                "prefer_authoritative_connectors",
                "parallel_fetch_with_retry",
            ],
            "flags": self.flags.as_dict(),
            "live_fetch_enabled": self.flags.faa_live_fetch,
            "search_providers_configured": available_search_providers(),
            "web_enrichment": enrichment_status(),
            "connectors": connector_health,
            "connector_degraded": degraded,
            "queue_depth": self.metrics.queue_size,
            "worker_count": self.metrics.worker_count,
            "cache": self.cache.snapshot(),
            "versions": self.store.snapshot(),
            "http": self.pipeline.client.stats(),
            "metrics": self.metrics.model_dump(),
            "scheduler": self.scheduler.status() if self.flags.faa_scheduler else {},
            "collection_policy": schedule_status(),
            "fre_bound": self.fre is not None,
            "last_successful_acquisition": self.metrics.last_success_at,
        }

    def dashboard(self) -> dict[str, Any]:
        from app.faa.background import schedule_status

        self._require()
        return {
            "programme": "FAA",
            "architecture_status": "v1.0.1 LOCKED",
            "version": "faa-v1.3.5",
            "does_not_answer": True,
            "live_fetch_enabled": self.flags.faa_live_fetch,
            "search_providers_configured": available_search_providers(),
            "metrics": self.metrics.model_dump(),
            "cache": self.cache.snapshot(),
            "versions": self.store.snapshot(),
            "http": self.pipeline.client.stats(),
            "scheduler": self.scheduler.status(),
            "collection_policy": schedule_status(),
            "connectors": [c.health() for c in self.connectors.values()],
            "recent_urls": list(self.cache.by_url.values())[-40:],
        }

    def acquire(self, q: str, *, limit: int = 24) -> dict[str, Any]:
        self._require()
        result = self.pipeline.acquire_for_query(q, limit=limit)
        self.scheduler.mark_run(
            "query_acquire",
            query=q,
            discovered=result.discovered,
            fetched=result.fetched,
            skipped=result.skipped_cached,
            failed=result.failed,
            indexed=result.indexed_to_fre,
            live_fetch=result.live_fetch,
            timings=result.timings,
        )
        payload = result.to_dict()
        docs = payload.get("documents") or []
        return {
            "programme": "FAA",
            "architecture_status": "v1.0.1 LOCKED",
            "version": "faa-v1.3.5",
            "does_not_answer": True,
            "never_reasons": True,
            **payload,
            "summary": {
                "live_acquisition_enabled": bool(payload.get("live_fetch")),
                "documents_discovered": payload.get("discovered") or 0,
                "documents_downloaded": payload.get("fetched") or 0,
                "documents_skipped": payload.get("skipped_cached") or 0,
                "documents_failed": payload.get("failed") or 0,
                "documents_parsed": payload.get("processed") or 0,
                "documents_indexed": payload.get("indexed_to_fre") or 0,
                "connector_names": sorted({d.get("source") or d.get("metadata", {}).get("faa_connector") for d in docs if d}),
                "source_urls": [d.get("url") for d in docs if d.get("url")][:40],
                "retrieved_timestamps": [
                    (d.get("metadata") or {}).get("faa_retrieved_at") for d in docs if (d.get("metadata") or {}).get("faa_retrieved_at")
                ][:40],
                "validation_status": [
                    (d.get("metadata") or {}).get("validation_status") or "ok" for d in docs
                ][:40],
                "authority_scores": [d.get("authority") for d in docs if d.get("authority") is not None][:40],
            },
        }

    def discover(self, q: str, *, limit: int = 40) -> dict[str, Any]:
        self._require()
        tasks, candidates = self.pipeline.discovery.discover(q, aoi=self.aoi, limit=limit)
        return {
            "programme": "FAA",
            "query": q,
            "tasks": [t.to_dict() for t in tasks],
            "candidates": [c.to_dict() for c in candidates],
            "connector_count": len(self.connectors),
        }

    def connectors_health(self) -> dict[str, Any]:
        return {
            "programme": "FAA",
            "live_fetch_enabled": self.flags.faa_live_fetch,
            "search_providers_configured": available_search_providers(),
            "connectors": [c.health() for c in sorted(self.connectors.values(), key=lambda c: c.priority())],
        }

    def run_jobs(self) -> dict[str, Any]:
        self._require()
        runs = []
        for q in WATCHLIST_QUERIES:
            runs.append(self.acquire(q, limit=16))
        self.scheduler.mark_run("scheduled_batch", queries=len(WATCHLIST_QUERIES))
        return {
            "programme": "FAA",
            "runs": runs,
            "scheduler": self.scheduler.status(),
            "metrics": self.metrics.model_dump(),
            "cache": self.cache.snapshot(),
            "versions": self.store.snapshot(),
        }

    def refresh_snapshots(
        self,
        *,
        limit_per_query: int = 6,
        mode: str = "nightly",
        max_runtime_sec: int = 3_600,
    ) -> dict[str, Any]:
        """Background collector cycle — fills FRE/FAA snapshot store off the Ask path."""
        self._require()
        runs: list[dict[str, Any]] = []
        errors: list[str] = []
        from app.faa.scheduler import EVENING_FILINGS_QUERIES

        queries = EVENING_FILINGS_QUERIES if mode == "evening_filings" else WATCHLIST_QUERIES
        deadline = time.monotonic() + max(60, min(int(max_runtime_sec), 3_600))
        deferred = 0
        for index, q in enumerate(queries):
            if time.monotonic() >= deadline:
                deferred = len(queries) - index
                break
            try:
                runs.append(self.acquire(q, limit=limit_per_query))
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{q[:48]}: {str(exc)[:120]}")
                runs.append({"query": q, "error": str(exc)[:160]})
        self.scheduler.mark_run(
            mode,
            queries=len(runs),
            errors=len(errors),
            deferred=deferred,
        )
        return {
            "ok": not errors,
            "programme": "FAA",
            "mode": mode,
            "queries": len(runs),
            "deferred": deferred,
            "runs": runs,
            "errors": errors,
            "scheduler": self.scheduler.status(),
            "cache": self.cache.snapshot(),
            "versions": self.store.snapshot(),
        }

    def consult(self, query: str, *, limit: int = 8) -> dict[str, Any]:
        """Observability path only — acquisition summary, never an answer."""
        self._require()
        result = self.acquire(query, limit=max(limit, 12))
        return {
            "programme": "FAA",
            "architecture_status": "v1.0.1 LOCKED",
            "does_not_answer": True,
            "never_reasons": True,
            "query": query,
            "live_fetch": result.get("live_fetch"),
            "discovered": result.get("discovered"),
            "fetched": result.get("fetched"),
            "skipped_cached": result.get("skipped_cached"),
            "failed": result.get("failed"),
            "indexed_to_fre": result.get("indexed_to_fre"),
            "timings": result.get("timings"),
            "documents": (result.get("documents") or [])[:limit],
            "versions": (result.get("versions") or [])[:limit],
            "errors": result.get("errors") or [],
            "guidance": {
                "enable_live_fetch": "Set FAA_LIVE_FETCH=true on intelligence-engine",
                "optional_search_keys": [
                    "EXA_API_KEY",
                    "FIRECRAWL_API_KEY",
                    "BROWSERBASE_API_KEY",
                    "TAVILY_API_KEY",
                    "SERPAPI_API_KEY",
                    "BING_SEARCH_API_KEY",
                    "GOOGLE_CSE_API_KEY+GOOGLE_CSE_ID",
                ],
                "playwright": {
                    "enable": "FAA_PLAYWRIGHT=true",
                    "install": "playwright install chromium",
                    "role": "JS IR/exchange fetch + free DuckDuckGo web search",
                },
                "strategy": {
                    "exa": "Preferred for research / industry / publications",
                    "firecrawl": "Deep search + URL→markdown enrichment of top hits",
                    "playwright": "Self-hosted Chromium for JS pages + free web search",
                    "browserbase": "Cloud JS-heavy / exchange / IR fallback fetch",
                },
            },
        }
