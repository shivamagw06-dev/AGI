"""InstitutionalScheduler — single operational heartbeat."""

from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from institutional_scheduler import store
from institutional_scheduler.dag.morning import build_morning_dag, dependencies_satisfied
from institutional_scheduler.execution.handlers import HANDLERS
from institutional_scheduler.health.engine import health_snapshot
from institutional_scheduler.retry.engine import run_with_retry
from institutional_scheduler.schema import FREEZE_LOCKS, PROGRAMME, SCHEDULER_VERSION
from institutional_scheduler.telemetry.recorder import record_run_telemetry
from institutional_scheduler.workflows.definitions import WORKFLOWS


class InstitutionalScheduler:
    """Schedule, depend, execute, retry, timeout, recover, health, telemetry."""

    def __init__(self) -> None:
        self.version = SCHEDULER_VERSION
        self.programme = PROGRAMME

    def status(self) -> dict[str, Any]:
        st = store.get_status()
        return {
            "programme": self.programme,
            "version": self.version,
            **st,
            "dag": build_morning_dag(),
            "freeze_locks": FREEZE_LOCKS,
            "fabricated": False,
        }

    def set_maintenance(self, enabled: bool = True) -> dict[str, Any]:
        return store.set_status(
            state="MAINTENANCE" if enabled else "INITIALISING",
            maintenance=bool(enabled),
            system_ready=False,
        )

    def run_morning(
        self,
        *,
        dry_run: bool = False,
        parallel: bool = True,
        manual_override: bool = False,
        skip: list[str] | None = None,
        operator_notes: str | None = None,
    ) -> dict[str, Any]:
        if store.get_status().get("maintenance") and not manual_override:
            return {
                "status": "blocked",
                "state": "MAINTENANCE",
                "reason": "scheduler_in_maintenance",
                "fabricated": False,
            }

        run_id = f"morn_{uuid.uuid4().hex[:14]}"
        started = time.time()
        date = store.utc_now()[:10]
        skip_set = set(skip or [])
        dag = build_morning_dag()

        store.set_status(
            state="RUNNING",
            current_run_id=run_id,
            current_workflow=None,
            system_ready=False,
        )

        completed: dict[str, str] = {}
        results: dict[str, Any] = {}
        recovery_actions: list[dict[str, Any]] = []

        ctx: dict[str, Any] = {
            "run_id": run_id,
            "completed": completed,
            "results": results,
            "dry_run": dry_run,
        }

        for level in dag["levels"]:
            peers = [wid for wid in level if wid not in skip_set]
            skipped_here = [wid for wid in level if wid in skip_set]
            for wid in skipped_here:
                completed[wid] = "skipped"
                results[wid] = {"status": "skipped", "reason": "manual_skip"}
                store.note_workflow_stat(wid, ok=True, duration_ms=0)

            runnable = []
            blocked = []
            for wid in peers:
                if dependencies_satisfied(wid, completed):
                    runnable.append(wid)
                else:
                    blocked.append(wid)
            for wid in blocked:
                completed[wid] = "blocked"
                results[wid] = {"status": "error", "error": "dependencies_unsatisfied", "blocked": True}
                store.note_workflow_stat(wid, ok=False, duration_ms=0)

            if not runnable:
                continue

            # Knowledge-layer workflows may dry-run; gates/queue/reports/ready always execute.
            _ALWAYS_EXECUTE = {
                "quality_gates",
                "research_queue",
                "morning_reports",
                "ready_declaration",
            }

            def _exec(wid: str) -> tuple[str, dict[str, Any]]:
                store.set_status(current_workflow=wid)
                wf = WORKFLOWS[wid]
                handler = HANDLERS[wid]
                t0 = time.time()
                out = run_with_retry(
                    lambda: handler(ctx),
                    workflow_id=wid,
                    retry_policy=wf.get("retry_policy"),
                    dry_run=bool(dry_run and wid not in _ALWAYS_EXECUTE),
                )
                duration = int((time.time() - t0) * 1000)
                out["duration_ms"] = duration
                return wid, out

            if parallel and len(runnable) > 1:
                with ThreadPoolExecutor(max_workers=min(4, len(runnable))) as pool:
                    futs = {pool.submit(_exec, wid): wid for wid in runnable}
                    for fut in as_completed(futs):
                        wid, out = fut.result()
                        results[wid] = out
                        st = out.get("status") or "error"
                        # Treat isolated errors as completed-for-deps (failure isolation)
                        completed[wid] = st if st != "skipped" else "skipped"
                        if st == "error":
                            completed[wid] = "error"
                            recovery_actions.append(
                                {
                                    "workflow": wid,
                                    "action": "continue_with_insufficiency",
                                    "permanent_failure": out.get("permanent_failure"),
                                    "operator_alert": out.get("operator_alert"),
                                }
                            )
                        ok = st in {"ok", "degraded", "partial", "skipped"}
                        store.note_workflow_stat(wid, ok=ok, duration_ms=int(out.get("duration_ms") or 0))
            else:
                for wid in runnable:
                    wid, out = _exec(wid)
                    results[wid] = out
                    st = out.get("status") or "error"
                    completed[wid] = st
                    if st == "error":
                        recovery_actions.append(
                            {
                                "workflow": wid,
                                "action": "continue_with_insufficiency",
                                "permanent_failure": out.get("permanent_failure"),
                                "operator_alert": out.get("operator_alert"),
                            }
                        )
                    ok = st in {"ok", "degraded", "partial", "skipped"}
                    store.note_workflow_stat(wid, ok=ok, duration_ms=int(out.get("duration_ms") or 0))

            # Refresh ctx mirrors
            ctx["completed"] = completed
            ctx["results"] = results

        # Ensure ready_declaration ran (if skipped somehow, force)
        if "ready_declaration" not in results:
            from institutional_scheduler.execution.handlers import handle_ready

            out = handle_ready(ctx)
            results["ready_declaration"] = out
            completed["ready_declaration"] = out.get("status") or "ok"

        ready_payload = ((results.get("ready_declaration") or {}).get("payload") or {})
        state = ready_payload.get("state") or store.get_status().get("state") or "WARNING"
        reports = ((results.get("morning_reports") or {}).get("payload") or {})
        if reports:
            store.put_reports(run_id, reports)

        duration_ms = int((time.time() - started) * 1000)
        health = health_snapshot()
        run_row = {
            "run_id": run_id,
            "date": date,
            "started_at": store.utc_now(),
            "duration_ms": duration_ms,
            "dry_run": dry_run,
            "parallel": parallel,
            "dag": {"levels": dag["levels"], "max_parallelism": dag["max_parallelism"]},
            "workflow_results": results,
            "completed": completed,
            "failures": [w for w, s in completed.items() if s == "error"],
            "recovery_actions": recovery_actions,
            "coverage": ((results.get("coverage_validation") or {}).get("payload")),
            "health": health,
            "reports_generated": list(reports.keys()) if isinstance(reports, dict) else [],
            "operator_notes": operator_notes,
            "state": state,
            "system_ready": bool(ready_payload.get("system_ready")),
            "version": SCHEDULER_VERSION,
            "freeze_locks": FREEZE_LOCKS,
            "fabricated": False,
            "reasoning_changed": False,
            "knowledge_factory_changed": False,
        }
        store.append_history(run_row)
        tel = record_run_telemetry(run_row)
        store.set_status(
            state=state,
            current_run_id=run_id,
            current_workflow=None,
            system_ready=bool(ready_payload.get("system_ready")),
        )
        result = {
            "status": "ok",
            "run_id": run_id,
            "state": state,
            "system_ready": bool(ready_payload.get("system_ready")),
            "duration_ms": duration_ms,
            "failures": run_row["failures"],
            "recovery_actions": recovery_actions,
            "reports_generated": run_row["reports_generated"],
            "telemetry": tel,
            "quality_gates": ((results.get("quality_gates") or {}).get("payload")),
            "dag": dag,
            "version": SCHEDULER_VERSION,
            "fabricated": False,
        }
        # Soft-wire: Institutional Research Office after READY (knowledge-only desk).
        # Never breaks the scheduler if research_office is unavailable.
        if result.get("system_ready"):
            try:
                from research_office.production import after_scheduler_ready

                result["research_office"] = after_scheduler_ready(result)
            except Exception as exc:
                result["research_office"] = {
                    "status": "error",
                    "error": str(exc)[:200],
                    "soft_wire": True,
                }
            # Soft-wire: Investment Office morning snapshot for interactive desk.
            try:
                from investment_office.morning_snapshot import after_scheduler_ready as io_after_ready

                result["investment_office_snapshot"] = io_after_ready(result)
            except Exception as exc:
                result["investment_office_snapshot"] = {
                    "ok": False,
                    "error": str(exc)[:200],
                    "soft_wire": True,
                }
        else:
            result["research_office"] = {
                "status": "skipped",
                "reason": "scheduler_not_ready",
            }
        return result

    def retry_workflow(
        self,
        workflow_id: str,
        *,
        run_id: str | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        if workflow_id not in WORKFLOWS:
            return {"found": False, "reason": "unknown_workflow", "workflow_id": workflow_id}
        if workflow_id not in HANDLERS:
            return {"found": False, "reason": "no_handler", "workflow_id": workflow_id}
        ctx = {"completed": {}, "results": {}, "run_id": run_id}
        # Seed prior completed as ok for deps
        for dep in WORKFLOWS[workflow_id].get("dependencies") or []:
            ctx["completed"][dep] = "ok"
        out = run_with_retry(
            lambda: HANDLERS[workflow_id](ctx),
            workflow_id=workflow_id,
            retry_policy=WORKFLOWS[workflow_id].get("retry_policy"),
            dry_run=dry_run,
        )
        store.alert("info", f"Manual retry: {workflow_id}", workflow_id=workflow_id)
        return {"found": True, "workflow_id": workflow_id, "result": out, "partial_retry": True}


_SCHEDULER: InstitutionalScheduler | None = None


def get_scheduler() -> InstitutionalScheduler:
    global _SCHEDULER
    if _SCHEDULER is None:
        _SCHEDULER = InstitutionalScheduler()
        store.set_status(state="INITIALISING")
    return _SCHEDULER
