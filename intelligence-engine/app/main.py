"""AGI Intelligence Engine — FastAPI multi-agent research service."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.routes import router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.agents.registry import bootstrap_registry

configure_logging()
log = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    # Refuse ephemeral KIP only when KIP_REQUIRE_PERSISTENT=1 (after disk is live).
    # Default is warn-only so Free→Starter upgrades succeed before a paid disk exists.
    from app.kip.persist import enforce_persistent_kip_or_raise

    persist_cfg = enforce_persistent_kip_or_raise(app_env=settings.app_env)
    if persist_cfg.get("warning"):
        log.warning(
            "kip_persistence_warning",
            extra={
                "durable": persist_cfg.get("durable"),
                "configured": persist_cfg.get("configured"),
                "kip_data_dir": persist_cfg.get("kip_data_dir"),
                "supabase_mirror": persist_cfg.get("supabase_mirror"),
                "warning": persist_cfg.get("warning"),
            },
        )
        # Also emit plain text so Render logs surface it immediately.
        print(persist_cfg["warning"], flush=True)
    else:
        log.info(
            "kip_persistence_ok",
            extra={
                "durable": True,
                "kip_data_dir": persist_cfg.get("kip_data_dir"),
                "supabase_mirror": persist_cfg.get("supabase_mirror"),
            },
        )

    bootstrap_registry()
    # Reload durable KIP snapshot (disk / optional Supabase) before serving traffic.
    try:
        from app.api.routes import _kip

        boot = _kip.reload_snapshot()
        log.info(
            "kip_snapshot_loaded",
            extra={
                "ok": boot.get("ok"),
                "loaded": boot.get("loaded"),
                "source": boot.get("source"),
                "documents": boot.get("documents"),
                "chunks": boot.get("chunks"),
            },
        )
    except Exception as exc:
        log.warning("kip_snapshot_load_failed", extra={"error": str(exc)[:160]})
    # Temporary migration-priority mode. The durable CapIQ job is the only
    # heavyweight background workload allowed on this service until it reaches
    # a terminal state. API/health/warehouse reads remain available.
    migration_priority = False
    try:
        from financial_warehouse_completion.capiq_background import latest_job, migration_active_cached

        active_capiq_job = latest_job()
        migration_priority = migration_active_cached()
        if migration_priority:
            log.warning(
                "capiq_migration_priority_mode",
                extra={
                    "job_id": active_capiq_job.get("job_id"),
                    "status": active_capiq_job.get("status"),
                    "paused_workloads": [
                        "institutional_stack_bootstrap", "ikt_capital_iq_seed",
                        "historical_sector_baseline", "valuation_consensus_seed",
                        "gather_collectors", "mission_control_builder",
                    ],
                },
            )
    except Exception as exc:
        log.warning("capiq_migration_priority_check_failed", extra={"error": str(exc)[:160]})
    # Soft-seed Institutional Stack (FIL corpus + FDI/MII refresh) — never blocks startup
    try:
        if getattr(settings, "institutional_stack", True) and not migration_priority:
            from institutional_stack.production import bootstrap_stack

            boot = bootstrap_stack()
            log.info(
                "institutional_stack_bootstrapped",
                extra={
                    "ok": boot.get("ok"),
                    "documents": (boot.get("seed") or {}).get("document_count"),
                    "tickers": boot.get("tickers"),
                },
            )
    except Exception as exc:
        log.warning("institutional_stack_bootstrap_failed", extra={"error": str(exc)[:160]})
    # IKT Capital IQ company-reference seed (bulk-uploaded screener exports,
    # re-derived from the committed source spreadsheets on every boot since
    # Render's filesystem is ephemeral without a persistent disk — see
    # institutional_knowledge_tables/seed_capital_iq.py). Idempotent, cheap
    # to skip once already seeded; runs in a background thread since a full
    # ingest of ~2,000 companies takes ~90s and must never block startup.
    try:
        import threading

        from institutional_knowledge_tables.seed_capital_iq import seed_if_needed

        def _run_ikt_seed() -> None:
            try:
                result = seed_if_needed()
                log.info(
                    "ikt_capital_iq_seed",
                    extra={
                        "ok": result.get("ok"),
                        "skipped": result.get("skipped"),
                        "total_resolved": result.get("total_resolved"),
                        "total_unresolved": result.get("total_unresolved"),
                    },
                )
            except Exception as exc:  # pragma: no cover - defensive
                log.warning("ikt_capital_iq_seed_failed", extra={"error": str(exc)[:160]})

        if not migration_priority:
            threading.Thread(target=_run_ikt_seed, name="ikt-capital-iq-seed", daemon=True).start()
    except Exception as exc:
        log.warning("ikt_capital_iq_seed_thread_failed", extra={"error": str(exc)[:160]})
    # Resume the first incomplete Capital IQ migration from its durable chunk
    # checkpoint. Completed chunks are never replayed.
    try:
        from financial_warehouse_completion.capiq_background import resume_incomplete
        capiq_resume = resume_incomplete()
        log.info("capiq_background_resume", extra=capiq_resume)
    except Exception as exc:
        log.warning("capiq_background_resume_failed", extra={"error": str(exc)[:160]})
    # Seed the committed 10-year CapIQ sector-ratio workbook into the durable
    # warehouse.  It is fingerprinted and idempotent: a matching deploy only
    # performs a registry lookup, while a new workbook rebuilds the affected
    # annual sector medians in the background without blocking HTTP startup.
    try:
        import threading

        from financial_warehouse_completion.sector_ratio_workbook import seed_if_needed as seed_sector_history

        def _run_sector_history_seed() -> None:
            try:
                result = seed_sector_history()
                log.info(
                    "historical_sector_baseline_seed",
                    extra={
                        "ok": result.get("ok"), "skipped": result.get("skipped"),
                        "rows": result.get("rows"), "median_rows": result.get("median_rows"),
                        "period_start": result.get("period_start"), "period_end": result.get("period_end"),
                    },
                )
            except Exception as exc:  # pragma: no cover - defensive startup path
                log.warning("historical_sector_baseline_seed_failed", extra={"error": str(exc)[:200]})

        if not migration_priority:
            threading.Thread(target=_run_sector_history_seed, name="historical-sector-baseline", daemon=True).start()
    except Exception as exc:
        log.warning("historical_sector_baseline_seed_thread_failed", extra={"error": str(exc)[:160]})
    # Valuation Consensus — Broker Estimates seed (committed CapIQ export).
    try:
        import threading

        from valuation_consensus.seed_broker_estimates import seed_if_needed as seed_broker_estimates

        def _run_vc_seed() -> None:
            try:
                result = seed_broker_estimates()
                log.info(
                    "valuation_consensus_seed",
                    extra={
                        "ok": result.get("ok"),
                        "skipped": result.get("skipped"),
                        "row_count": result.get("row_count"),
                    },
                )
            except Exception as exc:  # pragma: no cover
                log.warning("valuation_consensus_seed_failed", extra={"error": str(exc)[:160]})

        if not migration_priority:
            threading.Thread(target=_run_vc_seed, name="valuation-consensus-seed", daemon=True).start()
    except Exception as exc:
        log.warning("valuation_consensus_seed_thread_failed", extra={"error": str(exc)[:160]})
    # Valuation Terminal no longer seeds from committed Yahoo JSON.
    # It reads Warehouse → Unified Valuation Engine (PR: valuation-terminal-migration).
    log.info("valuation_terminal_json_loader_retired")
    # Gather loops belong on the sidecar / dedicated worker (AGI_ROLE=gather_worker).
    # When this process is the HTTP web role, skip starting them so Ask / Mission
    # Control are not starved — even if env flags were left true by mistake.
    import os

    # Only skip when explicitly marked as the HTTP process (start_engine.sh sets
    # AGI_ROLE=web). Unset role keeps legacy flag-gated in-process gather for
    # local/dev uvicorn launches without the sidecar script.
    agi_role = (os.environ.get("AGI_ROLE") or "").strip().lower()
    http_only = agi_role in {"web", "http", "api"} or str(
        os.environ.get("AGI_HTTP_NO_GATHER") or ""
    ).strip().lower() in {"1", "true", "yes", "on"}

    stop_faa_collector = None
    stop_cgl = None
    stop_mie_runtime = None
    if http_only or migration_priority:
        log.info(
            "gather_skipped_http_role",
            extra={"agi_role": agi_role, "reason": "capiq_migration_priority" if migration_priority else "sidecar_or_worker_owns_gather"},
        )
    else:
        # Global Markets is snapshot-first. Build it only in the dedicated
        # gather worker, never on the HTTP service that serves clients.
        if agi_role == "gather_worker" and str(os.environ.get("MIE_RUNTIME_ENABLED", "")).lower() in {"1", "true", "yes", "on"}:
            try:
                from macro_intelligence_engine.runtime import start as mie_runtime_start

                stop_mie_runtime = mie_runtime_start()
                logger.info("mie_snapshot_runtime_started")
            except Exception:
                logger.exception("mie_snapshot_runtime_failed")


        # FAA background collector — fills snapshot/index off the Ask path.
        try:
            from app.api.routes import _faa
            from app.faa.background import start_background_collector, stop_background_collector

            boot_faa = start_background_collector(lambda: _faa)
            stop_faa_collector = stop_background_collector
            log.info("faa_background_collector", extra=boot_faa)
        except Exception as exc:
            log.warning("faa_background_collector_failed", extra={"error": str(exc)[:160]})
        # Continuous Gather → Learn — autonomous historical collection + knowledge loop.
        try:
            from continuous_gather_learn.production import start as start_cgl
            from continuous_gather_learn.production import stop as stop_cgl_fn

            boot_cgl = start_cgl()
            stop_cgl = stop_cgl_fn
            log.info("continuous_gather_learn", extra=boot_cgl)
        except Exception as exc:
            log.warning("continuous_gather_learn_failed", extra={"error": str(exc)[:160]})
        # FSE-00 Pipeline Orchestrator — auto-start on evidence.stored.
        try:
            from financial_statements_engine.orchestrator.subscriber import bind_orchestrator_subscriber

            bind_orchestrator_subscriber()
            log.info(
                "fse_orchestrator_bound",
                extra={"subscriber": "fse00_orchestrator", "event": "evidence.stored", "auto_start": True},
            )
        except Exception as exc:
            log.warning("fse_orchestrator_bind_failed", extra={"error": str(exc)[:160]})

    # Mission Control snapshot: HTTP never builds. Prefer gather_worker / sidecar
    # (shared disk). When AGI_GATHER_SIDECAR=false (dedicated worker elsewhere),
    # start a local background builder so this box still has snapshot.json.
    stop_mc_snapshot = None
    try:
        from mission_control.snapshot import should_run_builder_on_web, start_scheduler, stop_scheduler

        run_mc = (not http_only) or should_run_builder_on_web()
        # gather_worker process starts its own scheduler; avoid double-start there.
        if migration_priority:
            log.info("mission_control_builder_paused", extra={"reason": "capiq_migration_priority"})
        elif http_only and should_run_builder_on_web():
            boot_mc = start_scheduler(boot_build=True)
            stop_mc_snapshot = stop_scheduler
            log.info("mc_snapshot_builder_on_web", extra=boot_mc)
        elif not http_only and (os.environ.get("AGI_ROLE") or "").strip().lower() != "gather_worker":
            # Legacy in-process gather (no AGI_ROLE=web) — also own MC snapshots.
            if run_mc:
                boot_mc = start_scheduler(boot_build=True)
                stop_mc_snapshot = stop_scheduler
                log.info("mc_snapshot_builder_inprocess", extra=boot_mc)
    except Exception as exc:
        log.warning("mc_snapshot_builder_failed", extra={"error": str(exc)[:160]})

    # NOTE: Do not auto-download Chromium at startup on free-tier Render — the
    # install can starve CPU/RAM and make /v1/health time out. Bake browsers via
    # buildCommand (`python -m playwright install chromium`) or set
    # FAA_PLAYWRIGHT_AUTO_INSTALL=true only when disk/CPU budget allows.
    log.info(
        "intelligence_engine_started",
        extra={"env": settings.app_env, "agib_base": settings.agib_api_base_url},
    )
    yield
    try:
        if stop_cgl is not None:
            stop_cgl()
    except Exception:
        pass
    try:
        if stop_faa_collector is not None:
            stop_faa_collector()
    except Exception:
        pass
    try:
        if stop_mie_runtime is not None:
            stop_mie_runtime()
    except Exception:
        pass


    try:
        if stop_mc_snapshot is not None:
            stop_mc_snapshot()
    except Exception:
        pass
    log.info("intelligence_engine_stopped")


app = FastAPI(
    title="AGI Intelligence Engine",
    version="0.1.0",
    description="Multi-agent institutional research engine for Agarwal Global Investments.",
    lifespan=lifespan,
)
app.include_router(router)


_MIGRATION_ALLOWLIST = (
    "/",
    "/v1/health",
    "/v1/warehouse/import/capital-iq-workbook/jobs/",
)


@app.middleware("http")
async def capiq_migration_load_shed(request, call_next):
    """Reserve the shared web process for the active controlled migration.

    This is deliberately temporary and state-driven: once the durable job is
    terminal, normal Intelligence Engine traffic is admitted automatically.
    """
    path = request.url.path
    if path == "/" or any(path.startswith(prefix) for prefix in _MIGRATION_ALLOWLIST[1:]):
        return await call_next(request)
    try:
        from financial_warehouse_completion.capiq_background import migration_active_cached

        if migration_active_cached():
            return JSONResponse(
                status_code=503,
                content={
                    "ok": False,
                    "error": "capiq_migration_priority",
                    "message": "Intelligence workload temporarily paused while controlled accounting migration completes.",
                    "migration_status": "ACTIVE",
                    "retry_after_seconds": 30,
                },
                headers={"Retry-After": "30"},
            )
    except Exception:
        pass
    return await call_next(request)


@app.get("/")
async def root():
    return {
        "service": "agi-intelligence-engine",
        "status": "running",
        "docs": "/docs",
    }
