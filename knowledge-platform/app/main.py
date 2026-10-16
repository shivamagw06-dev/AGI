"""KAIP service entrypoint — Knowledge Acquisition Platform + AKO (Sprint 6.5)."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from app.ako.orchestrator import AdaptiveKnowledgeOrchestrator
from app.ako.overnight import run_overnight_pipeline
from app.ako.schedule_profiles import PROFILES
from app.api.routes import router
from app.collectors.bse.corporate_actions import BSECorporateActionCollector
from app.collectors.company_ir.collector import CompanyIRCollector
from app.collectors.nse.announcements import NSEAnnouncementCollector
from app.collectors.nse.bhavcopy import NSEBhavcopyCollector
from app.collectors.yahoo.collector import YahooCollector
from app.config.settings import Settings, get_settings
from app.krig.gateway import KnowledgeRetrievalGateway
from app.metrics.metrics import METRICS
from app.pipeline.orchestrator import AcquisitionPipeline
from app.scheduler.scheduler import AcquisitionScheduler
from app.storage.db import KaipStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("kaip")


def build_collectors(settings: Settings) -> dict[str, Any]:
    symbols = list(settings.watchlist)
    live = settings.live_collectors_enabled
    collectors = [
        YahooCollector(symbols=symbols, interval_seconds=settings.yahoo_interval_seconds, live=live),
        NSEAnnouncementCollector(
            symbols=symbols,
            interval_seconds=settings.nse_announcement_interval_seconds,
            live=live,
        ),
        NSEBhavcopyCollector(
            symbols=symbols,
            interval_seconds=settings.nse_bhavcopy_interval_seconds,
            live=live,
        ),
        BSECorporateActionCollector(
            symbols=symbols,
            interval_seconds=settings.bse_corporate_action_interval_seconds,
            live=live,
        ),
        CompanyIRCollector(
            symbols=symbols,
            interval_seconds=settings.company_ir_interval_seconds,
            live=live,
        ),
    ]
    return {c.collector_id: c for c in collectors}


def _make_runner(pipeline: AcquisitionPipeline, collectors: dict[str, Any], collector_id: str):
    def _run() -> Any:
        collector = collectors[collector_id]
        result = pipeline.run_collector(collector)
        METRICS.record_run(
            collector_id,
            accepted=len(result.accepted),
            rejected=len(result.rejected),
            duplicates=len(result.duplicates),
            published=len(result.knowledge_objects),
            learning=len(result.learning_events),
        )
        return result

    return _run


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        store = KaipStore(settings.db_path)
        pipeline = AcquisitionPipeline(store, settings)
        collectors = build_collectors(settings)
        gateway = KnowledgeRetrievalGateway(store, hip_base_url=settings.hip_base_url)

        ako: AdaptiveKnowledgeOrchestrator | None = None
        scheduler: AcquisitionScheduler | AdaptiveKnowledgeOrchestrator

        if settings.ako_enabled:
            ako = AdaptiveKnowledgeOrchestrator(
                tick_seconds=settings.ako_tick_seconds,
                store=store,
                watchlist=settings.watchlist,
            )
            for collector in collectors.values():
                profile = PROFILES.get(collector.collector_id)
                ako.register_collector(
                    collector.collector_id,
                    _make_runner(pipeline, collectors, collector.collector_id),
                    profile=profile,
                )

            # Overnight rebuild — no external collect; published-knowledge only.
            def _overnight() -> dict[str, Any]:
                return run_overnight_pipeline(store, watchlist=settings.watchlist)

            ako.register_collector(
                "OvernightKnowledgeRebuild",
                _overnight,
                profile=PROFILES["OvernightKnowledgeRebuild"],
            )
            ako.register_overnight_hook(_overnight)
            scheduler = ako
            if settings.scheduler_enabled:
                ako.start()
                logger.info(
                    "AKO started watchlist=%s tick=%ss",
                    list(settings.watchlist),
                    settings.ako_tick_seconds,
                )
        else:
            legacy = AcquisitionScheduler()
            for collector in collectors.values():
                legacy.register(collector, _make_runner(pipeline, collectors, collector.collector_id))
            scheduler = legacy
            if settings.scheduler_enabled:
                legacy.start()
                logger.info("KAIP fixed scheduler started watchlist=%s", list(settings.watchlist))

        app.state.settings = settings
        app.state.store = store
        app.state.pipeline = pipeline
        app.state.collectors = collectors
        app.state.scheduler = scheduler
        app.state.ako = ako
        app.state.gateway = gateway

        yield

        if ako is not None:
            ako.stop()
        elif isinstance(scheduler, AcquisitionScheduler):
            scheduler.stop()
        store.close()

    app = FastAPI(
        title="AGI Knowledge Acquisition Platform",
        version=settings.version,
        docs_url="/internal/docs",
        redoc_url=None,
        openapi_url="/internal/openapi.json",
        lifespan=lifespan,
    )
    app.include_router(router)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
