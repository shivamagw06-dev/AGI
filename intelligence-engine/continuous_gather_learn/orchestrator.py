"""Continuous Gather → Learn orchestrator.

Loop (independent of Ask / user queries):
  Collect → Validate → Clean → Store → Embed/Extract → Update knowledge
  → Generate signals → Evaluate forecasts → Learn → Update confidence → Archive

Reuses existing LIDI, KF HD, FAA, Institutional Scheduler, FVL, FLE, ILO, CAL.
Does not create new analyst agents.
"""

from __future__ import annotations

import time
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from continuous_gather_learn import persist as cgl_persist
from continuous_gather_learn.flags import (
    faa_in_loop_enabled,
    historical_backfill_enabled,
    is_enabled,
    kf_hd_enabled,
    learning_loop_enabled,
    lidi_enabled,
    morning_dag_enabled,
)
from continuous_gather_learn.knowledge_extract import extract_batch_from_daily_report

PHASES = (
    "collect",
    "validate",
    "clean",
    "store",
    "embed_extract",
    "update_knowledge",
    "generate_signals",
    "evaluate_forecasts",
    "learn",
    "update_confidence",
    "archive",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _soft(fn: Callable[[], Any], *, label: str) -> dict[str, Any]:
    t0 = time.time()
    try:
        result = fn()
        return {
            "ok": True,
            "label": label,
            "latency_ms": int((time.time() - t0) * 1000),
            "result": result if isinstance(result, dict) else {"value": result},
        }
    except Exception as exc:  # noqa: BLE001 — never fail the loop
        return {
            "ok": False,
            "label": label,
            "latency_ms": int((time.time() - t0) * 1000),
            "error": str(exc)[:300],
            "trace": traceback.format_exc()[-400:],
        }


def _ist_hour() -> int:
    # Approximate IST without zoneinfo dependency issues.
    # UTC+5:30
    from datetime import timedelta

    ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
    return ist.hour


def select_slot() -> str:
    """Choose collection intensity by IST hour."""
    h = _ist_hour()
    if 5 <= h < 9:
        return "pre_market"
    if 9 <= h < 16:
        return "intraday"
    if 16 <= h < 20:
        return "post_market"
    return "overnight"


def _collect_lidi(*, slot: str) -> dict[str, Any]:
    if not lidi_enabled():
        return {"ok": False, "skipped": True, "reason": "CONTINUOUS_LIDI=false"}
    from live_data.production import run_morning_live_ingestion

    # Intraday: still run full soft ingestion — collectors are incremental by design.
    # Checkpoint records last successful as_of for resume visibility.
    ck = cgl_persist.get_checkpoint("lidi")
    report = run_morning_live_ingestion()
    cgl_persist.put_checkpoint(
        "lidi",
        {
            "slot": slot,
            "last_ok": bool((report or {}).get("ok", True)),
            "resume_from": (report or {}).get("as_of") or ck.get("resume_from"),
            "summary": {
                k: (report or {}).get(k)
                for k in ("ok", "sources", "freshness", "status", "as_of")
                if (report or {}).get(k) is not None
            },
        },
    )
    return report if isinstance(report, dict) else {"ok": True, "report": report}


def _collect_kf_hd(*, slot: str) -> dict[str, Any]:
    if not kf_hd_enabled():
        return {"ok": False, "skipped": True, "reason": "CONTINUOUS_KF_HD=false"}
    # Prefer full daily+HD on post_market / overnight; lighter HD-only otherwise.
    if slot in {"post_market", "overnight", "pre_market"}:
        from knowledge_factory.production import run_daily_pipeline

        report = run_daily_pipeline(historical_depth=True, institutional_knowledge=False)
    else:
        from knowledge_factory.production import run_historical_depth_pipeline

        report = run_historical_depth_pipeline()
    cgl_persist.put_checkpoint(
        "kf_hd",
        {
            "slot": slot,
            "last_ok": True,
            "resume_from": (report or {}).get("as_of")
            or (report or {}).get("generated_at")
            or _now(),
            "entities": len((report or {}).get("entities") or (report or {}).get("tickers") or []),
        },
    )
    return report if isinstance(report, dict) else {"ok": True}


def _collect_faa() -> dict[str, Any]:
    if not faa_in_loop_enabled():
        return {"ok": False, "skipped": True, "reason": "CONTINUOUS_FAA_REFRESH=false"}
    # Prefer dedicated FAA background flag path; still callable once from CGL.
    try:
        from app.api.routes import _faa
        from app.faa.background import run_collector_once

        return run_collector_once(_faa)
    except Exception:
        from app.faa.background import run_collector_once

        # Soft construct if routes unbound
        try:
            from app.faa.service import FaaService

            return run_collector_once(FaaService())
        except Exception as exc:
            return {"ok": False, "error": str(exc)[:200]}


def _run_morning_dag() -> dict[str, Any]:
    if not morning_dag_enabled():
        return {"ok": False, "skipped": True, "reason": "CONTINUOUS_MORNING_DAG=false"}
    from institutional_scheduler.production import run_morning

    return run_morning(dry_run=False, parallel=True)


def _evaluate_and_learn() -> dict[str, Any]:
    if not learning_loop_enabled():
        return {"ok": False, "skipped": True, "reason": "CONTINUOUS_LEARNING_LOOP=false"}

    out: dict[str, Any] = {"fvl": None, "fle": None, "ilo": None, "cal": None, "archived": []}

    # FVL — pull performance/calibration/learning; archive durable copies.
    def _fvl_cycle() -> dict[str, Any]:
        from forecast_validation_learning import production as fvl

        learning = fvl.learning(limit=40)
        for row in list(learning.get("learnings") or learning.get("items") or [])[:40]:
            if isinstance(row, dict):
                lid = cgl_persist.archive_learning(
                    {**row, "source": "fvl", "loop": "continuous_gather_learn"}
                )
                out["archived"].append(lid)
        return {
            "performance": fvl.performance(),
            "calibration": fvl.calibration(),
            "learning": learning,
        }

    out["fvl"] = _soft(_fvl_cycle, label="fvl_cycle")

    # FLE — run jobs / learning / calibration consult
    def _fle_cycle() -> dict[str, Any]:
        from app.fle.service import FleService

        svc = FleService()
        jobs = svc.run_jobs() if hasattr(svc, "run_jobs") else {"skipped": True}
        learning = svc.learning() if hasattr(svc, "learning") else {}
        calibration = svc.calibration() if hasattr(svc, "calibration") else {}
        return {"jobs": jobs, "learning": learning, "calibration": calibration}

    out["fle"] = _soft(_fle_cycle, label="fle_cycle")

    # ILO — snapshot recent process memory into durable archive
    def _ilo_cycle() -> dict[str, Any]:
        from institutional_learning_office.production import history as ilo_history
        from institutional_learning_office.production import telemetry as ilo_telemetry

        hist = ilo_history(limit=30)
        for row in list(hist.get("recent_learnings") or [])[:30]:
            if isinstance(row, dict):
                cgl_persist.archive_learning(
                    {**row, "source": "ilo", "loop": "continuous_gather_learn"}
                )
        return {"history": hist, "telemetry": ilo_telemetry()}

    out["ilo"] = _soft(_ilo_cycle, label="ilo_cycle")

    # CAL — soft confidence / governance dashboard (proposals only)
    out["cal"] = _soft(
        lambda: __import__(
            "institutional_reasoning.cal.production", fromlist=["dashboard"]
        ).dashboard(),
        label="cal_dashboard",
    )
    return out


def _analyst_accuracy_memory() -> dict[str, Any]:
    """Build long-term accuracy memory for ResearchDirector weighting."""
    archived = cgl_persist.list_archived_learnings(limit=200)
    by_source: dict[str, dict[str, Any]] = {}
    for row in archived:
        src = str(row.get("source") or row.get("analyst") or row.get("signal") or "unknown")
        bucket = by_source.setdefault(
            src, {"source": src, "n": 0, "correct": 0, "incorrect": 0, "samples": []}
        )
        bucket["n"] += 1
        outcome = str(row.get("outcome") or row.get("label") or row.get("result") or "").lower()
        if outcome in {"correct", "hit", "true", "win", "accurate"}:
            bucket["correct"] += 1
        elif outcome in {"incorrect", "miss", "false", "loss", "inaccurate"}:
            bucket["incorrect"] += 1
        if len(bucket["samples"]) < 3:
            bucket["samples"].append(
                {
                    "learning_id": row.get("learning_id"),
                    "summary": str(row.get("explanation") or row.get("summary") or "")[:180],
                }
            )
    for b in by_source.values():
        n = max(1, b["correct"] + b["incorrect"])
        b["accuracy"] = round(b["correct"] / n, 4) if (b["correct"] + b["incorrect"]) else None
    memory = {
        "updated_at": _now(),
        "n_learnings": len(archived),
        "by_source": list(by_source.values()),
        "note": "Process accuracy memory — not ML weight updates.",
    }
    cgl_persist.put_checkpoint("analyst_accuracy_memory", memory)
    return memory


def run_cycle(
    *,
    slot: str | None = None,
    force_morning_dag: bool = False,
    include_faa: bool | None = None,
) -> dict[str, Any]:
    """One autonomous gather→learn cycle. Never raises to caller."""
    if not is_enabled():
        return {
            "ok": False,
            "enabled": False,
            "reason": "CONTINUOUS_GATHER_LEARN=false",
            "generated_at": _now(),
        }

    slot = slot or select_slot()
    run_id = f"cgl_{uuid.uuid4().hex[:12]}"
    t0 = time.time()
    phases: dict[str, Any] = {p: {"status": "pending"} for p in PHASES}
    errors: list[str] = []
    volumes = {
        "collectors_ok": 0,
        "collectors_failed": 0,
        "knowledge_extracts": 0,
        "learnings_archived": 0,
        "backfill_extracts": 0,
        "answer_packs_written": 0,
    }

    # 1. Collect
    collect_payload: dict[str, Any] = {"slot": slot, "steps": {}}
    phases["collect"]["status"] = "running"
    if force_morning_dag or (slot == "pre_market" and morning_dag_enabled()):
        dag = _soft(_run_morning_dag, label="morning_dag")
        collect_payload["steps"]["morning_dag"] = dag
        if dag.get("ok"):
            volumes["collectors_ok"] += 1
        else:
            volumes["collectors_failed"] += 1
            if dag.get("error"):
                errors.append(f"morning_dag: {dag['error']}")
    else:
        # Direct LIDI + KF when full DAG not scheduled this slot
        lidi = _soft(lambda: _collect_lidi(slot=slot), label="lidi")
        collect_payload["steps"]["lidi"] = lidi
        if lidi.get("ok") and not (lidi.get("result") or {}).get("skipped"):
            volumes["collectors_ok"] += 1
        elif not (lidi.get("result") or {}).get("skipped"):
            volumes["collectors_failed"] += 1

        if slot in {"post_market", "overnight", "pre_market"}:
            kf = _soft(lambda: _collect_kf_hd(slot=slot), label="kf_hd")
            collect_payload["steps"]["kf_hd"] = kf
            if kf.get("ok") and not (kf.get("result") or {}).get("skipped"):
                volumes["collectors_ok"] += 1
            elif not (kf.get("result") or {}).get("skipped"):
                volumes["collectors_failed"] += 1

    # Continuous historical backfill — drain until remaining=0, then maintenance.
    # Outside morning-DAG branch so backlog keeps moving every cycle.
    if historical_backfill_enabled() and _should_run_backfill(slot):
        def _bf() -> dict[str, Any]:
            from continuous_gather_learn.historical_backfill import run_historical_backfill

            return run_historical_backfill()

        bf = _soft(_bf, label="historical_backfill")
        collect_payload["steps"]["historical_backfill"] = bf
        if bf.get("ok") and not (bf.get("result") or {}).get("skipped"):
            volumes["collectors_ok"] += 1
            volumes["backfill_extracts"] = len(
                ((bf.get("result") or {}).get("knowledge_extracts") or [])
            )
        elif not (bf.get("result") or {}).get("skipped"):
            volumes["collectors_failed"] += 1

    do_faa = faa_in_loop_enabled() if include_faa is None else include_faa
    if do_faa and slot in {"post_market", "overnight"}:
        faa = _soft(_collect_faa, label="faa")
        collect_payload["steps"]["faa"] = faa
        if faa.get("ok"):
            volumes["collectors_ok"] += 1
        else:
            volumes["collectors_failed"] += 1
    phases["collect"] = {"status": "ok", "payload": collect_payload}

    # 2–4 Validate / Clean / Store — owned by LIDI & KF pipelines; record provenance
    phases["validate"] = {
        "status": "ok",
        "note": "Validation performed inside LIDI/KF pipelines",
        "lidi_checkpoint": cgl_persist.get_checkpoint("lidi"),
        "kf_checkpoint": cgl_persist.get_checkpoint("kf_hd"),
    }
    phases["clean"] = {"status": "ok", "note": "Normalisation inside LIDI/KF collectors"}
    phases["store"] = {
        "status": "ok",
        "note": "Persisted to LIDI_STORE_ROOT / KF_HD_STORE_ROOT / CGL_STORE_ROOT",
        "cgl_store": str(cgl_persist.store_root()),
    }

    # 5–6 Embed/Extract + Update knowledge
    kf_result = (
        ((collect_payload.get("steps") or {}).get("kf_hd") or {}).get("result")
        or ((collect_payload.get("steps") or {}).get("morning_dag") or {}).get("result")
        or {}
    )
    extracts = []
    try:
        # Prefer nested historical / daily payload
        report = kf_result
        if isinstance(report, dict) and report.get("payload"):
            report = report.get("payload") or report
        extracts = extract_batch_from_daily_report(report if isinstance(report, dict) else {})
        volumes["knowledge_extracts"] = len(extracts) + int(volumes.get("backfill_extracts") or 0)
        phases["embed_extract"] = {
            "status": "ok",
            "n": volumes["knowledge_extracts"],
            "from_report": len(extracts),
            "from_backfill": int(volumes.get("backfill_extracts") or 0),
        }
        phases["update_knowledge"] = {
            "status": "ok",
            "n": len(extracts),
            "note": "Structured knowledge extracts written to CGL store for analyst packs",
        }
    except Exception as exc:  # noqa: BLE001
        phases["embed_extract"] = {"status": "error", "error": str(exc)[:200]}
        phases["update_knowledge"] = {"status": "degraded"}
        errors.append(f"extract: {exc}")

    # 7 Generate signals — soft: use extracts / FVL performance as signal feed
    phases["generate_signals"] = {
        "status": "ok",
        "signals": [
            {
                "type": "knowledge_refresh",
                "entity": e.get("entity"),
                "metrics": list((e.get("metrics") or {}).keys())[:8],
            }
            for e in extracts[:20]
        ],
    }

    # 8–10 Evaluate / Learn / Confidence
    learn = _soft(_evaluate_and_learn, label="learning_loop")
    phases["evaluate_forecasts"] = {
        "status": "ok" if learn.get("ok") else "degraded",
        "fvl": ((learn.get("result") or {}).get("fvl")),
        "fle": ((learn.get("result") or {}).get("fle")),
    }
    phases["learn"] = {
        "status": "ok" if learn.get("ok") else "degraded",
        "ilo": ((learn.get("result") or {}).get("ilo")),
        "archived": ((learn.get("result") or {}).get("archived") or [])[:20],
    }
    volumes["learnings_archived"] = len((learn.get("result") or {}).get("archived") or [])
    memory = _analyst_accuracy_memory()
    phases["update_confidence"] = {
        "status": "ok",
        "analyst_accuracy_memory": {
            "n_learnings": memory.get("n_learnings"),
            "sources": len(memory.get("by_source") or []),
        },
        "cal": ((learn.get("result") or {}).get("cal")),
        "note": "Confidence memory updated for ResearchDirector weighting — no LLM retraining.",
    }

    # 11 Archive
    run = {
        "run_id": run_id,
        "ok": volumes["collectors_failed"] == 0 or volumes["collectors_ok"] > 0,
        "enabled": True,
        "slot": slot,
        "generated_at": _now(),
        "latency_ms": int((time.time() - t0) * 1000),
        "phases": phases,
        "volumes": volumes,
        "errors": errors[:20],
        "loop": list(PHASES),
        "ask_isolated": True,
        "ml_retrain": False,
    }
    phases["archive"] = {"status": "ok", "run_id": run_id}
    run["phases"] = phases
    cgl_persist.put_run(run)

    # Observability metrics snapshot
    prev = cgl_persist.get_metrics()
    cgl_persist.put_metrics(
        {
            "last_run_id": run_id,
            "last_slot": slot,
            "last_ok": run["ok"],
            "last_latency_ms": run["latency_ms"],
            "collectors_ok_total": int(prev.get("collectors_ok_total") or 0) + volumes["collectors_ok"],
            "collectors_failed_total": int(prev.get("collectors_failed_total") or 0)
            + volumes["collectors_failed"],
            "knowledge_extracts_total": int(prev.get("knowledge_extracts_total") or 0)
            + volumes["knowledge_extracts"],
            "learnings_archived_total": int(prev.get("learnings_archived_total") or 0)
            + volumes["learnings_archived"],
            "cycles_total": int(prev.get("cycles_total") or 0) + 1,
            "freshness": {
                "lidi": cgl_persist.get_checkpoint("lidi").get("updated_at"),
                "kf_hd": cgl_persist.get_checkpoint("kf_hd").get("updated_at"),
            },
            "knowledge_growth": {
                "extracts": volumes["knowledge_extracts"],
                "archived_learnings": volumes["learnings_archived"],
            },
            "historical_coverage": _coverage_snapshot(),
        }
    )

    # KIL-01 — Knowledge Integration Layer soft-wire (CGL gathers; KIL integrates)
    try:
        from institutional_evidence.integration.layer import integrate_cgl_run

        kil = integrate_cgl_run(run)
        run["kil_integration"] = {
            "ok": bool(kil.get("ok")),
            "knowledge_version": (kil.get("snapshot") or {}).get("knowledge_version"),
            "summary": kil.get("summary"),
        }
        cgl_persist.put_run(run)
    except Exception as exc:  # noqa: BLE001
        run["kil_integration"] = {"ok": False, "error": str(exc)[:200]}
        try:
            cgl_persist.put_run(run)
        except Exception:
            pass

    # IKL — Institutional Knowledge Intelligence Layer (extract → memories → graph)
    try:
        from institutional_knowledge_layer.production import after_cgl_cycle as ikl_after_cgl

        run["ikl_writeback"] = ikl_after_cgl(run)
        cgl_persist.put_run(run)
    except Exception as exc:  # noqa: BLE001
        run["ikl_writeback"] = {"ok": False, "error": str(exc)[:200], "soft": True}
        try:
            cgl_persist.put_run(run)
        except Exception:
            pass

    # Ask AGI answer packs — rotate through covered companies from database state.
    # Runs after knowledge integration and never on the interactive Ask path.
    try:
        from answer_packs.materializer import materialize_batch

        answer_pack_checkpoint = cgl_persist.get_checkpoint("answer_pack_materializer") or {}
        answer_pack_result = materialize_batch(
            batch_size=5,
            start_cursor=int(answer_pack_checkpoint.get("next_cursor") or 0),
        )
        run["answer_pack_materialization"] = answer_pack_result
        volumes["answer_packs_written"] = int(answer_pack_result.get("written") or 0)
        cgl_persist.put_checkpoint("answer_pack_materializer", answer_pack_result)
        cgl_persist.put_run(run)
    except Exception as exc:  # noqa: BLE001
        run["answer_pack_materialization"] = {
            "ok": False,
            "error": str(exc)[:240],
            "soft": True,
        }

    # IO V1.3.1 — Morning Snapshot Builder (soft). Never blocks CGL/Ask.
    try:
        from investment_office.morning_snapshot import after_cgl_cycle

        run["investment_office_snapshot"] = after_cgl_cycle(run)
        try:
            cgl_persist.put_run(run)
        except Exception:
            pass
    except Exception as exc:  # noqa: BLE001
        run["investment_office_snapshot"] = {
            "ok": False,
            "error": str(exc)[:200],
            "soft_wire": True,
        }

    # Mission Control snapshot (soft). Worker owns compute; HTTP only reads.
    try:
        from mission_control.snapshot import after_cgl_cycle as mc_after_cgl

        run["mission_control_snapshot"] = mc_after_cgl(run)
        try:
            cgl_persist.put_run(run)
        except Exception:
            pass
    except Exception as exc:  # noqa: BLE001
        run["mission_control_snapshot"] = {
            "ok": False,
            "error": str(exc)[:200],
            "soft_wire": True,
        }

    return run


def _should_run_backfill(slot: str) -> bool:
    """While backlog > 0, run every slot; in maintenance, deep slots only."""
    try:
        from continuous_gather_learn.historical_backfill import until_complete_enabled
        from knowledge_factory.historical_depth import queue as bf_queue

        state = bf_queue.load_engine_state()
        if state.get("maintenance_only"):
            return slot in {"post_market", "overnight"}
        if until_complete_enabled():
            stats = bf_queue.backlog_stats()
            if int(stats.get("remaining") or 0) > 0:
                return True
        return slot in {"post_market", "overnight"}
    except Exception:
        return slot in {"post_market", "overnight"}


def _coverage_snapshot() -> dict[str, Any]:
    try:
        from knowledge_factory.historical_depth.backfill import coverage_progress
        from knowledge_factory.historical_depth.dashboard import historical_depth_dashboard

        dash = historical_depth_dashboard()
        prog = coverage_progress()
        return {
            "total_companies": prog.get("total_companies") or dash.get("universe_n"),
            "current_listed_universe": prog.get("current_listed_universe"),
            "covered_companies": prog.get("covered_companies"),
            "historical_coverage_pct": prog.get("historical_coverage_pct")
            or dash.get("historical_coverage_pct")
            or dash.get("historical_completeness_pct"),
            "hard_coverage_pct": prog.get("hard_coverage_pct"),
            "soft_coverage_pct": prog.get("soft_coverage_pct"),
            "average_history_years": prog.get("average_history_years")
            or dash.get("average_history_years"),
            "companies_fully_backfilled": prog.get("companies_fully_backfilled")
            or dash.get("companies_fully_backfilled"),
            "remaining_backlog": prog.get("remaining_backlog"),
            "queue_length": prog.get("queue_length"),
            "companies_processed_today": prog.get("companies_processed_today"),
            "companies_remaining": prog.get("remaining_backlog"),
            "new_listings_count": prog.get("new_listings_count"),
            "delisted_count": prog.get("delisted_count"),
            "pending_ipos_count": prog.get("pending_ipos_count"),
            "pending_ipos": prog.get("pending_ipos"),
            "company_scorecards": prog.get("company_scorecards"),
            "knowledge_extracts": prog.get("knowledge_extracts"),
            "embeddings": prog.get("embeddings"),
            "documents": dash.get("documents"),
            "documents_downloaded": prog.get("documents_downloaded"),
            "corporate_actions_coverage_pct": dash.get("corporate_actions_coverage_pct"),
            "macro_series_points": dash.get("macro_series_points"),
            "estimated_completion_days": prog.get("estimated_completion_days"),
            "historical_growth_per_day_entities": prog.get("historical_growth_per_day_entities"),
            "companies_gt_10y": dash.get("companies_gt_10y"),
            "mode": prog.get("mode"),
            "maintenance_only": prog.get("maintenance_only"),
            "completed_at": prog.get("completed_at"),
            "continues_until_complete": prog.get("continues_until_complete"),
            "coverage_finished": False,
            "queue_always_ready": True,
            "living_universe": prog.get("living_universe"),
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)[:160]}


def learning_for_director(*, query: str = "", limit: int = 8) -> dict[str, Any]:
    """Soft context pack for ResearchDirector — historical learning before synthesis."""
    memory = cgl_persist.get_checkpoint("analyst_accuracy_memory") or {}
    learnings = cgl_persist.list_archived_learnings(limit=limit)
    fle_consult: dict[str, Any] = {}
    try:
        from app.fle.service import FleService

        fle_consult = FleService().consult(query or "institutional learning", limit=limit) or {}
    except Exception:
        fle_consult = {}
    weights = []
    for row in memory.get("by_source") or []:
        if row.get("accuracy") is not None:
            weights.append(
                {
                    "source": row.get("source"),
                    "accuracy": row.get("accuracy"),
                    "n": row.get("n"),
                    "weight_hint": "higher" if (row.get("accuracy") or 0) >= 0.55 else "lower",
                }
            )
    return {
        "enabled": True,
        "ml_retrain": False,
        "analyst_accuracy_memory": memory,
        "recent_learnings": learnings[:limit],
        "fle_consult": fle_consult,
        "opinion_weights": weights[:12],
        "instruction": (
            "Weight analyst opinions using historical accuracy memory when available. "
            "Do not invent facts. Prefer sources with higher historical accuracy."
        ),
    }
