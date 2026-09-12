"""Continuous Historical Backfill Engine — runs until 100% coverage, then maintenance.

Never stops after an arbitrary cycle count. Persistent queue + checkpoints.
Deep backfill drains until remaining=0, then switches to incremental maintenance.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Any

from knowledge_factory.historical_depth import store as hd_store
from knowledge_factory.historical_depth.collectors import collect_entity_history, collect_market_history
from knowledge_factory.historical_depth.completion import (
    TARGET_YEARS,
    evaluate_completion,
    record_attempt,
)
from knowledge_factory.historical_depth.dashboard import historical_depth_dashboard
from knowledge_factory.historical_depth.objects.company import compile_historical_company
from knowledge_factory.historical_depth.packs import build_historical_pack
from knowledge_factory.historical_depth.producers.derived import produce_derived
from knowledge_factory.historical_depth import queue as bf_queue
from knowledge_factory.historical_depth.universe_priority import supported_universe
from knowledge_factory.historical_depth.validators import validate_series

BACKFILL_VERSION = "hd-backfill-v2.0.0"
BATCH_DEFAULT = int(os.getenv("KF_HD_BACKFILL_BATCH") or "12")
BATCHES_PER_CYCLE = int(os.getenv("KF_HD_BACKFILL_BATCHES_PER_CYCLE") or "3")
PARALLEL_WORKERS = max(1, int(os.getenv("KF_HD_BACKFILL_WORKERS") or "2"))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Backward-compatible helpers (Phase 1 API) ---------------------------------

def _entity_years(entity: str) -> float:
    from knowledge_factory.historical_depth.completion import history_years

    return history_years(entity)


def is_complete(entity: str, *, target_years: float = TARGET_YEARS) -> bool:
    return bool(evaluate_completion(entity, target_years=target_years).get("complete"))


def load_checkpoint() -> dict[str, Any]:
    q = bf_queue.load_queue()
    done = [
        str(c.get("company"))
        for c in (q.get("companies") or [])
        if str(c.get("status")) in {bf_queue.STATUS_COMPLETE, bf_queue.STATUS_MAINTENANCE}
    ]
    failed = {
        str(c.get("company")): {"streak": c.get("attempts"), "error": (c.get("errors") or [{}])[0].get("error")}
        for c in (q.get("companies") or [])
        if str(c.get("status")) in {bf_queue.STATUS_FAILED, bf_queue.STATUS_COOLDOWN}
    }
    return {
        "completed": done,
        "failed": failed,
        "cursor": 0,
        "updated_at": q.get("updated_at"),
        "queue_length": q.get("queue_length"),
    }


def save_checkpoint(ck: dict[str, Any]) -> None:
    hd_store.put_report("historical_backfill_checkpoint", {**ck, "updated_at": _now(), "backfill_version": BACKFILL_VERSION})


def pending_entities(entities: list[str] | None = None, *, target_years: float = TARGET_YEARS) -> list[str]:
    bf_queue.ensure_queue()
    batch = bf_queue.next_batch(batch_size=10_000, maintenance=False)
    wanted = {e.upper() for e in (entities or supported_universe())}
    return [str(r["company"]) for r in batch if str(r.get("company") or "").upper() in wanted]


def _enrich_entity(entity: str, *, maintenance: bool) -> dict[str, Any]:
    """Collect → validate → derive → extract hooks for one company.

    Uses institutional connectors (financials, shareholding, IR discovery) and
    chunked checkpoints when INSTITUTIONAL_DATA_CONNECTORS is enabled (default on).
    """
    e = entity.upper()
    use_connectors = str(os.getenv("INSTITUTIONAL_DATA_CONNECTORS", "true")).lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    live_on = str(os.getenv("KF_HD_LIVE_COLLECTORS", "false")).lower() in {"1", "true", "yes", "on"}

    if use_connectors and live_on:
        try:
            from institutional_data.backfill.chunked import ChunkedBackfillEngine

            row = ChunkedBackfillEngine().enrich_company_chunked(e, maintenance=maintenance)
            # Derived packs still run for Ask/KF consumers
            produce_derived(e)
            compile_historical_company(e)
            build_historical_pack(e)
            actions = hd_store.get_series("corporate_actions", e) or {}
            record_attempt(
                e,
                "corporate_actions",
                status="complete" if (actions.get("records")) else "empty",
                detail=f"n={len(actions.get('records') or [])}",
            )
            record_attempt(e, "historical_news", status="n_a", detail="exchange_snapshot_soft")
            record_attempt(e, "announcements", status="n_a", detail="exchange_snapshot_soft")
            record_attempt(e, "_wave", status="complete", detail="connector_suite")
            return row
        except Exception as exc:  # noqa: BLE001
            # Soft fall through to legacy path
            _ = exc

    prefer_live = live_on
    if maintenance:
        ev = evaluate_completion(e)
        if ev.get("dimensions", {}).get("ohlcv", {}).get("status") == "complete":
            prefer_live = False
    row = collect_entity_history(e, prefer_live=prefer_live)

    # Connector-backed IR / shareholding / financials even in legacy path when offline-safe
    try:
        from institutional_data.connectors.registry import get_connector

        if live_on:
            ir = get_connector("company_ir").run(entity=e, download_files=True, max_downloads=4)
            docs = ir.normalized or ir.records
            types = {str(d.get("doc_type")) for d in docs}
            record_attempt(e, "annual_reports", status="complete" if "annual_report" in types else "empty")
            record_attempt(
                e, "investor_presentations", status="complete" if "investor_presentation" in types else "empty"
            )
            record_attempt(e, "earnings_transcripts", status="complete" if "earnings_transcript" in types else "n_a")
            record_attempt(e, "esg_reports", status="complete" if "esg_report" in types else "n_a")
            sh = get_connector("shareholding").run(entity=e)
            record_attempt(
                e,
                "shareholding",
                status="complete" if sh.ok else "n_a",
                detail=sh.error or f"n={len(sh.records)}",
            )
            get_connector("financial_statements").run(entity=e)
        else:
            record_attempt(e, "annual_reports", status="n_a", detail="ir_deferred_or_offline")
            record_attempt(e, "investor_presentations", status="n_a", detail="ir_deferred_or_offline")
            record_attempt(e, "earnings_transcripts", status="n_a", detail="ir_deferred_or_offline")
            record_attempt(e, "esg_reports", status="n_a", detail="ir_deferred_or_offline")
            record_attempt(e, "shareholding", status="n_a", detail="offline")
    except Exception as exc:  # noqa: BLE001
        record_attempt(e, "annual_reports", status="n_a", detail=str(exc)[:120])
        record_attempt(e, "investor_presentations", status="n_a", detail=str(exc)[:120])
        record_attempt(e, "earnings_transcripts", status="n_a", detail=str(exc)[:120])
        record_attempt(e, "esg_reports", status="n_a", detail=str(exc)[:120])
        record_attempt(e, "shareholding", status="n_a", detail=str(exc)[:120])

    actions = hd_store.get_series("corporate_actions", e) or {}
    record_attempt(
        e,
        "corporate_actions",
        status="complete" if (actions.get("records")) else "empty",
        detail=f"n={len(actions.get('records') or [])}",
    )
    record_attempt(e, "historical_news", status="n_a", detail="exchange_snapshot_soft")
    record_attempt(e, "announcements", status="n_a", detail="exchange_snapshot_soft")
    record_attempt(e, "_wave", status="complete", detail="soft_dims_attempted")

    validation_failures = []
    for kind in ("financials_annual", "financials_quarterly", "prices"):
        series = hd_store.get_series(kind, e)
        verdict = validate_series(series) if series else {"ok": True}
        if series and not verdict.get("ok"):
            validation_failures.append({"entity": e, "kind": kind, **verdict})

    produce_derived(e)
    compile_historical_company(e)
    build_historical_pack(e)

    extract = None
    embedding = None
    try:
        from continuous_gather_learn.embeddings import embed_knowledge_extract
        from continuous_gather_learn.knowledge_extract import extract_from_hd_series

        extract = extract_from_hd_series(e)
        embedding = embed_knowledge_extract(e, extract)
    except Exception as exc:  # noqa: BLE001
        row["extract_error"] = str(exc)[:160]

    evaluation = evaluate_completion(e)
    row.update(
        {
            "history_years": evaluation.get("history_years"),
            "complete": evaluation.get("complete"),
            "coverage_pct": evaluation.get("coverage_pct"),
            "evaluation": evaluation,
            "validation_failures": validation_failures,
            "extract_ok": bool(extract and not extract.get("error")),
            "embedding_ok": bool(embedding and embedding.get("vector")),
            "maintenance": maintenance,
        }
    )
    return row


def run_backfill_batch(
    *,
    entities: list[str] | None = None,
    batch_size: int | None = None,
    target_years: float = TARGET_YEARS,
    derive: bool = True,
    maintenance: bool | None = None,
) -> dict[str, Any]:
    """Process one prioritised batch. Never restarts completed companies."""
    t0 = time.perf_counter()
    batch_size = max(1, int(batch_size or BATCH_DEFAULT))
    state = bf_queue.load_engine_state()
    if maintenance is None:
        maintenance = bool(state.get("maintenance_only"))

    bf_queue.ensure_queue()
    selected = bf_queue.next_batch(batch_size=batch_size, maintenance=maintenance)
    if entities:
        want = {e.upper() for e in entities}
        selected = [r for r in selected if str(r.get("company") or "").upper() in want]
        # If explicit entities not on queue selection (tests), force them
        if not selected:
            selected = [{"company": e.upper(), "status": "pending"} for e in entities][:batch_size]

    collect_market_history()
    rows: list[dict[str, Any]] = []

    def _one(company: str) -> dict[str, Any]:
        bf_queue.mark_running(company)
        try:
            row = _enrich_entity(company, maintenance=bool(maintenance))
            bf_queue.mark_result(company, row.get("evaluation") or evaluate_completion(company))
            return row
        except Exception as exc:  # noqa: BLE001
            ev = evaluate_completion(company)
            bf_queue.mark_result(company, ev, error=str(exc)[:200])
            return {"entity": company, "status": "error", "error": str(exc)[:200], "complete": False}

    workers = 1 if len(selected) <= 1 else min(PARALLEL_WORKERS, len(selected))
    if workers == 1:
        for r in selected:
            rows.append(_one(str(r.get("company"))))
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(_one, str(r.get("company"))): r for r in selected}
            for fut in as_completed(futs):
                rows.append(fut.result())

    processed_ok = [r for r in rows if not r.get("skipped")]
    bf_queue.bump_processed_today(len(processed_ok))
    try:
        from continuous_gather_learn.ops_observability import record_throughput_sample

        years_sum = sum(float(r.get("history_years") or 0) for r in processed_ok)
        extracts_n = sum(1 for r in processed_ok if r.get("extract_ok"))
        docs_n = 0
        for r in processed_ok:
            dens = ((r.get("evaluation") or {}).get("density") or {})
            docs_n += int(dens.get("documents") or 0)
        record_throughput_sample(
            companies=len(processed_ok),
            years=years_sum,
            documents=docs_n,
            extracts=extracts_n,
        )
    except Exception:
        pass
    transition = bf_queue.maybe_transition_to_maintenance()
    stats = bf_queue.backlog_stats()
    dash = historical_depth_dashboard(entities=entities or supported_universe())

    # Sync legacy checkpoint
    save_checkpoint(load_checkpoint())

    report = {
        "backfill_version": BACKFILL_VERSION,
        "ok": True,
        "mode": "maintenance" if maintenance else "deep_backfill",
        "batch_size": batch_size,
        "processed": len(rows),
        "completed_total": stats.get("fully_backfilled"),
        "remaining": stats.get("remaining"),
        "queue_length": stats.get("queue_length"),
        "target_years": target_years,
        "rows": rows,
        "validation_failures": [f for r in rows for f in (r.get("validation_failures") or [])],
        "dashboard": {
            "average_history_years": dash.get("average_history_years"),
            "historical_completeness_pct": dash.get("historical_completeness_pct"),
            "companies_gt_10y": dash.get("companies_gt_10y"),
            "universe_n": dash.get("universe_n"),
        },
        "progress": stats,
        "engine": transition.get("engine") or bf_queue.load_engine_state(),
        "transitioned_to_maintenance": bool(transition.get("transitioned")),
        "runtime_seconds": round(time.perf_counter() - t0, 2),
        "generated_at": _now(),
        "resumable": True,
        "continues_until_complete": True,
        "note": "Runs until remaining=0 then maintenance-only; never redownloads completed history unnecessarily",
    }
    hd_store.put_report("historical_backfill_last", report)
    return report


def run_until_batch_budget(
    *,
    max_batches: int | None = None,
    batch_size: int | None = None,
    stop_when_empty: bool = True,
) -> dict[str, Any]:
    """Drain multiple batches in one call — used by continuous scheduler.

    Does not stop merely because one cycle succeeded; stops when backlog empty
    or max_batches reached (budget for this wake).
    """
    max_batches = max(1, int(max_batches or BATCHES_PER_CYCLE))
    state = bf_queue.load_engine_state()
    maintenance = bool(state.get("maintenance_only"))
    batches = []
    for i in range(max_batches):
        stats = bf_queue.backlog_stats()
        if not maintenance and stop_when_empty and int(stats.get("remaining") or 0) == 0:
            break
        # In maintenance mode run one light batch of completed names for incremental refresh
        if maintenance and i >= 1:
            break
        report = run_backfill_batch(batch_size=batch_size, maintenance=maintenance)
        batches.append(
            {
                "batch_index": i,
                "processed": report.get("processed"),
                "remaining": report.get("remaining"),
                "mode": report.get("mode"),
            }
        )
        maintenance = bool((report.get("engine") or {}).get("maintenance_only")) or bool(
            report.get("transitioned_to_maintenance")
        )
        if not maintenance and int(report.get("remaining") or 0) == 0:
            break
        if int(report.get("processed") or 0) == 0:
            break

    stats = bf_queue.backlog_stats()
    return {
        "ok": True,
        "backfill_version": BACKFILL_VERSION,
        "batches_run": len(batches),
        "batches": batches,
        "remaining": stats.get("remaining"),
        "fully_backfilled": stats.get("fully_backfilled"),
        "total_companies": stats.get("total_companies"),
        "coverage_pct": stats.get("coverage_pct"),
        "mode": stats.get("mode"),
        "maintenance_only": stats.get("maintenance_only"),
        "completed_at": stats.get("completed_at"),
        "continues_until_complete": not bool(stats.get("maintenance_only")),
        "generated_at": _now(),
    }


def coverage_progress(*, entities: list[str] | None = None) -> dict[str, Any]:
    stats = bf_queue.backlog_stats()
    dash = historical_depth_dashboard(entities=entities or supported_universe())
    try:
        from continuous_gather_learn import persist as cgl_persist

        extracts_n = cgl_persist.count_knowledge_extracts()
        embeddings_n = cgl_persist.count_embeddings()
    except Exception:
        extracts_n = 0
        embeddings_n = 0
    docs = dash.get("documents") or {}
    try:
        from knowledge_factory.historical_depth.living_universe import living_universe_board

        living = living_universe_board()
    except Exception:
        living = {"coverage_finished": False, "queue_ready": True}
    # Sample density / hard-soft scorecards for Mission Control
    scorecards = []
    try:
        from knowledge_factory.historical_depth.completion import company_scorecard

        sample = list(entities or supported_universe())[:12]
        # Prefer names with queue activity
        q = bf_queue.load_queue()
        ranked = sorted(
            [c for c in (q.get("companies") or []) if c.get("status") != bf_queue.STATUS_DELISTED],
            key=lambda c: (-float(c.get("years") or 0), str(c.get("company"))),
        )
        for row in ranked[:8]:
            scorecards.append(company_scorecard(str(row.get("company"))))
        if not scorecards:
            scorecards = [company_scorecard(s) for s in sample[:5]]
    except Exception:
        scorecards = []
    return {
        "universe_n": stats.get("total_companies") or dash.get("universe_n"),
        "total_companies": stats.get("total_companies"),
        "current_listed_universe": living.get("current_listed_universe") or stats.get("total_companies"),
        "covered_companies": living.get("covered_companies") or stats.get("fully_backfilled"),
        "companies_fully_backfilled": stats.get("fully_backfilled"),
        "remaining_backlog": stats.get("remaining"),
        "queue_length": stats.get("queue_length"),
        "average_history_years": stats.get("average_years") or dash.get("average_history_years"),
        "historical_coverage_pct": living.get("coverage_pct") or stats.get("coverage_pct"),
        "hard_coverage_pct": stats.get("hard_coverage_pct"),
        "soft_coverage_pct": stats.get("soft_coverage_pct"),
        "new_listings": living.get("new_listings") or [],
        "new_listings_count": living.get("new_listings_count") or 0,
        "delisted_companies": living.get("delisted_companies") or [],
        "delisted_count": living.get("delisted_count") or 0,
        "pending_ipos": living.get("pending_ipos") or [],
        "pending_ipos_count": living.get("pending_ipos_count") or 0,
        "companies_gt_10y": dash.get("companies_gt_10y"),
        "companies_gt_15y": dash.get("companies_gt_15y"),
        "estimated_completion_days": bf_queue.eta_days(),
        "historical_growth_per_day_entities": None,
        "companies_processed_today": stats.get("companies_processed_today"),
        "knowledge_extracts": extracts_n,
        "embeddings": embeddings_n,
        "documents_downloaded": docs.get("documents_total"),
        "annual_reports": docs.get("annual_reports"),
        "quarterly_results": docs.get("quarterly_results"),
        "investor_presentations": docs.get("investor_presentations"),
        "company_scorecards": scorecards,
        "mode": stats.get("mode"),
        "maintenance_only": stats.get("maintenance_only"),
        "completed_at": stats.get("completed_at"),
        "last_backfill_at": (hd_store.get_report("historical_backfill_last") or {}).get("generated_at"),
        "target_years": TARGET_YEARS,
        "continues_until_complete": not bool(stats.get("maintenance_only")),
        "coverage_finished": False,
        "queue_always_ready": True,
        "living_universe": living,
    }
