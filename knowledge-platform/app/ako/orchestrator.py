"""Adaptive Knowledge Orchestrator — OS for continuous institutional learning."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

from app.ako.calendar import EventCalendar
from app.ako.dispatcher import CollectorDispatcher
from app.ako.event_engine import EventEngine
from app.ako.priority_engine import PriorityEngine
from app.ako.schedule_engine import ScheduleEngine
from app.ako.schedule_profiles import PROFILES, ScheduleProfile, profile_for
from app.ako.sessions import MarketSession, next_session_boundary, resolve_session
from app.ako.telemetry import TelemetryHub

logger = logging.getLogger("kaip.ako")


class AdaptiveKnowledgeOrchestrator:
    """Standalone orchestration engine — does not collect or reason."""

    def __init__(
        self,
        *,
        calendar: EventCalendar | None = None,
        tick_seconds: float = 1.0,
        system_load_high: bool = False,
        store: Any | None = None,
        watchlist: tuple[str, ...] = (),
    ) -> None:
        self.calendar = calendar or EventCalendar()
        self.schedule_engine = ScheduleEngine(self.calendar)
        self.priority_engine = PriorityEngine()
        self.event_engine = EventEngine(self.calendar)
        self.telemetry = TelemetryHub()
        self.dispatcher = CollectorDispatcher(self.telemetry)
        self.tick_seconds = tick_seconds
        self.system_load_high = system_load_high
        self.store = store
        self.watchlist = watchlist
        self._profiles: dict[str, ScheduleProfile] = dict(PROFILES)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._overnight_hooks: list[Callable[[], Any]] = []

    # ----- registration -----

    def register_collector(
        self,
        collector_id: str,
        runner: Callable[[], Any],
        *,
        job_id: str | None = None,
        profile: ScheduleProfile | None = None,
    ) -> None:
        jid = job_id or collector_id
        if profile:
            self._profiles[jid] = profile
        elif jid not in self._profiles:
            # fallback profile from collector defaults
            self._profiles[jid] = ScheduleProfile(
                job_id=jid,
                collector_id=collector_id,
                knowledge_kind="custom",
                live_interval_seconds=60,
                quiet_interval_seconds=900,
                overnight_interval_seconds=3600,
            )
        self.dispatcher.register(jid, collector_id, runner)

    def register_overnight_hook(self, hook: Callable[[], Any]) -> None:
        self._overnight_hooks.append(hook)

    # ----- lifecycle -----

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="ako-orchestrator", daemon=True)
        self._thread.start()
        logger.info("AKO started")

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3.0)

    def tick_once(self, *, clock=None, now_ts: float | None = None) -> list[dict[str, Any]]:
        """Deterministic single evaluation cycle (also used by tests)."""
        session = resolve_session(clock)
        session_key = f"{session.as_of_ist.date().isoformat()}:{session.session.value}"
        now_ts = time.time() if now_ts is None else now_ts
        decisions = []

        with self._lock:
            job_items = list(self.dispatcher.jobs.values())

        for job in job_items:
            profile = self._profiles.get(job.job_id) or profile_for(job.job_id)
            if profile is None:
                continue
            session_run_done = job.session_runs.get(session_key) == session.session.value
            decision = self.schedule_engine.decide(
                profile,
                session,
                last_run_at=job.last_run_at,
                now_ts=now_ts,
                source_available=job.source_available,
                system_load_high=self.system_load_high,
                queue_depth=self.dispatcher.queue_depth,
                watch_symbol=_primary_watch_symbol(job.collector_id),
                session_run_done=session_run_done,
            )
            decisions.append(decision)
            self.telemetry.log_decision(
                {
                    "job_id": decision.job_id,
                    "should_run": decision.should_run,
                    "interval_seconds": decision.interval_seconds,
                    "priority": decision.priority,
                    "trigger_reason": decision.trigger_reason,
                    "session": decision.session.value,
                    "boost_multiplier": decision.boost_multiplier,
                    "skip_reason": decision.skip_reason,
                }
            )

        ordered = self.priority_engine.order(decisions)
        executed = []
        for decision in ordered:
            # Overnight rebuild hook path (hooks + optional registered runner)
            if decision.job_id == "OvernightKnowledgeRebuild" and decision.should_run:
                self._run_overnight(decision, session_key)
                executed.append(
                    {
                        "job_id": decision.job_id,
                        "success": True,
                        "trigger_reason": decision.trigger_reason,
                        "interval_seconds": decision.interval_seconds,
                        "priority": decision.priority,
                        "session": decision.session.value,
                    }
                )
                continue
            rec = self.dispatcher.dispatch(decision, session_key=session_key)
            if rec:
                executed.append(
                    {
                        "job_id": decision.job_id,
                        "execution_id": rec.execution_id,
                        "success": rec.success,
                        "trigger_reason": decision.trigger_reason,
                        "interval_seconds": decision.interval_seconds,
                        "priority": decision.priority,
                        "session": decision.session.value,
                    }
                )
        return executed

    def list_jobs(self) -> list[dict]:
        """Compatibility with legacy /v1/internal/jobs consumers."""
        snap = self.mission_control_snapshot()
        return [
            {
                "job_id": j["job_id"],
                "collector_id": j["collector_id"],
                "interval_seconds": j["current_interval_seconds"],
                "run_count": j["run_count"],
                "last_run_at": None,
                "last_error": j["last_error"],
                "health": j["health"],
                "next_run_in_seconds": j["next_run_in_seconds"],
            }
            for j in snap["jobs"]
        ]

    def decide_all(self, *, clock=None, now_ts: float | None = None) -> list[Any]:
        """Return schedule decisions without executing (tests / Mission Control preview)."""
        session = resolve_session(clock)
        session_key = f"{session.as_of_ist.date().isoformat()}:{session.session.value}"
        now_ts = time.time() if now_ts is None else now_ts
        out = []
        for job in self.dispatcher.jobs.values():
            profile = self._profiles.get(job.job_id) or profile_for(job.job_id)
            if profile is None:
                continue
            session_run_done = job.session_runs.get(session_key) == session.session.value
            out.append(
                self.schedule_engine.decide(
                    profile,
                    session,
                    last_run_at=job.last_run_at,
                    now_ts=now_ts,
                    source_available=job.source_available,
                    system_load_high=self.system_load_high,
                    queue_depth=self.dispatcher.queue_depth,
                    watch_symbol=_primary_watch_symbol(job.collector_id),
                    session_run_done=session_run_done,
                )
            )
        return out

    def _run_overnight(self, decision, session_key: str) -> None:
        job = self.dispatcher.jobs.get(decision.job_id)
        t0 = time.perf_counter()
        rec = self.telemetry.begin(
            job_id=decision.job_id,
            collector_id=decision.job_id,
            session=decision.session.value,
            trigger_reason=decision.trigger_reason,
            priority=decision.priority,
            interval_seconds=decision.interval_seconds,
            boost_multiplier=1.0,
        )
        error = None
        try:
            for hook in self._overnight_hooks:
                hook()
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
        self.telemetry.complete(
            rec,
            success=error is None,
            error=error,
            freshness_impact="rebuild",
            started_mono=t0,
        )
        if job:
            job.last_run_at = time.time()
            job.run_count += 1
            job.session_runs[session_key] = decision.session.value

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self.tick_once()
            except Exception:
                logger.exception("ako tick failed")
            self._stop.wait(self.tick_seconds)

    # ----- observability / Mission Control -----

    def mission_control_snapshot(self) -> dict[str, Any]:
        session = resolve_session()
        jobs = []
        now_ts = time.time()
        for job in self.dispatcher.jobs.values():
            profile = self._profiles.get(job.job_id)
            interval = job.last_interval_seconds
            if profile and interval is None:
                decision = self.schedule_engine.decide(
                    profile,
                    session,
                    last_run_at=job.last_run_at,
                    now_ts=now_ts,
                    source_available=job.source_available,
                    system_load_high=self.system_load_high,
                    queue_depth=self.dispatcher.queue_depth,
                )
                interval = decision.interval_seconds
            next_run_in = None
            if job.last_run_at is not None and interval:
                next_run_in = max(0, int(interval - (now_ts - job.last_run_at)))
            jobs.append(
                {
                    "job_id": job.job_id,
                    "collector_id": job.collector_id,
                    "knowledge_kind": profile.knowledge_kind if profile else None,
                    "current_interval_seconds": interval,
                    "next_run_in_seconds": next_run_in,
                    "run_count": job.run_count,
                    "success_count": job.success_count,
                    "failure_count": job.failure_count,
                    "consecutive_failures": job.consecutive_failures,
                    "source_available": job.source_available,
                    "last_error": job.last_error,
                    "last_trigger_reason": job.last_trigger_reason,
                    "health": _health(job),
                }
            )

        tel = self.telemetry.snapshot()
        return {
            "service": "ako",
            "version": "0.5.0",
            "session": {
                "current": session.session.value,
                "label": session.label,
                "as_of_ist": session.as_of_ist.isoformat(),
                "is_trading_day": session.is_trading_day,
                "allow_live_polling": session.allow_live_polling,
                "allow_heavy_rebuild": session.allow_heavy_rebuild,
                "next_boundary_ist": next_session_boundary(session.as_of_ist).isoformat(),
            },
            "events": self.event_engine.snapshot(),
            "jobs": jobs,
            "schedule_profiles": [
                {
                    "job_id": p.job_id,
                    "collector_id": p.collector_id,
                    "knowledge_kind": p.knowledge_kind,
                    "live_interval_seconds": p.live_interval_seconds,
                    "quiet_interval_seconds": p.quiet_interval_seconds,
                    "overnight_interval_seconds": p.overnight_interval_seconds,
                    "once_per_session": p.once_per_session.value if p.once_per_session else None,
                    "overnight_heavy": p.overnight_heavy,
                    "allow_event_boost": p.allow_event_boost,
                }
                for p in PROFILES.values()
            ],
            "queue_depth": self.dispatcher.queue_depth,
            "dead_letter_count": len(self.dispatcher.dead_letters),
            "dead_letters": [
                {
                    "job_id": d.job_id,
                    "collector_id": d.collector_id,
                    "error": d.error,
                    "attempts": d.attempts,
                    "last_trigger_reason": d.last_trigger_reason,
                }
                for d in self.dispatcher.dead_letters[-20:]
            ],
            "telemetry": tel,
            "freshness": self._freshness_snapshot(),
            "confidence": self._confidence_snapshot(),
            "principles": {
                "ask_never_triggers_collectors": True,
                "ie_consumes_published_knowledge_only": True,
                "adaptive_not_fixed": True,
                "kfe_enabled": True,
                "kce_enabled": True,
            },
        }

    def _freshness_snapshot(self) -> dict[str, Any]:
        if self.store is None:
            return {"status": "store_unavailable"}
        from app.kfe.engine import KnowledgeFreshnessEngine

        return KnowledgeFreshnessEngine().portfolio_snapshot(self.store, watchlist=self.watchlist)

    def _confidence_snapshot(self) -> dict[str, Any]:
        if self.store is None:
            return {"status": "store_unavailable"}
        rows = self.store.list_confidence(limit=50)
        if not rows:
            return {"tracked": 0, "average_pct": None, "samples": []}
        avg = round(sum(float(r.get("confidence_pct") or 0) for r in rows) / len(rows), 1)
        return {
            "tracked": len(rows),
            "average_pct": avg,
            "low_confidence_count": sum(1 for r in rows if float(r.get("confidence_pct") or 0) < 60),
            "samples": rows[:10],
        }

    def register_event(self, **kwargs) -> dict:
        ev = self.event_engine.register_event(**kwargs)
        return {
            "event_id": ev.event_id,
            "kind": ev.kind.value,
            "title": ev.title,
            "event_date": ev.event_date.isoformat(),
            "symbols": list(ev.symbols),
            "boost_multiplier": ev.boost_multiplier,
        }


def _health(job) -> str:
    if not job.source_available:
        return "dead_letter"
    if job.consecutive_failures >= 3:
        return "degraded"
    if job.run_count == 0:
        return "registered"
    return "healthy"


def _primary_watch_symbol(collector_id: str) -> str | None:
    # Earnings boosts often key off INFY for demo; production would map watchlist.
    if "Yahoo" in collector_id or "CompanyIR" in collector_id or "NSE" in collector_id:
        return "INFY"
    return None
