"""Schedule Engine — compute adaptive intervals from session + events + health."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.ako.calendar import EventCalendar
from app.ako.schedule_profiles import ScheduleProfile
from app.ako.sessions import MarketSession, SessionState


@dataclass(frozen=True)
class ScheduleDecision:
    job_id: str
    interval_seconds: int
    should_run: bool
    priority: int
    trigger_reason: str
    session: MarketSession
    boost_multiplier: float
    skip_reason: str | None = None


class ScheduleEngine:
    def __init__(self, calendar: EventCalendar | None = None) -> None:
        self.calendar = calendar or EventCalendar()

    def decide(
        self,
        profile: ScheduleProfile,
        session: SessionState,
        *,
        last_run_at: float | None,
        now_ts: float,
        source_available: bool = True,
        system_load_high: bool = False,
        queue_depth: int = 0,
        watch_symbol: str | None = None,
        session_run_done: bool = False,
    ) -> ScheduleDecision:
        if not source_available:
            return ScheduleDecision(
                job_id=profile.job_id,
                interval_seconds=profile.quiet_interval_seconds,
                should_run=False,
                priority=0,
                trigger_reason="source_unavailable",
                session=session.session,
                boost_multiplier=1.0,
                skip_reason="source_unavailable",
            )

        # Overnight heavy jobs only in overnight / weekend rebuild windows
        if profile.overnight_heavy and not session.allow_heavy_rebuild:
            return ScheduleDecision(
                job_id=profile.job_id,
                interval_seconds=profile.overnight_interval_seconds,
                should_run=False,
                priority=profile.priority_base,
                trigger_reason="awaiting_overnight_window",
                session=session.session,
                boost_multiplier=1.0,
                skip_reason="not_overnight",
            )

        # Once-per-session jobs (bhavcopy)
        if profile.once_per_session is not None:
            if session.session != profile.once_per_session:
                return ScheduleDecision(
                    job_id=profile.job_id,
                    interval_seconds=3600,
                    should_run=False,
                    priority=profile.priority_base,
                    trigger_reason="awaiting_session",
                    session=session.session,
                    boost_multiplier=1.0,
                    skip_reason=f"wait_{profile.once_per_session.value}",
                )
            if session_run_done:
                return ScheduleDecision(
                    job_id=profile.job_id,
                    interval_seconds=24 * 3600,
                    should_run=False,
                    priority=profile.priority_base,
                    trigger_reason="already_ran_this_session",
                    session=session.session,
                    boost_multiplier=1.0,
                    skip_reason="once_complete",
                )
            return ScheduleDecision(
                job_id=profile.job_id,
                interval_seconds=0,
                should_run=True,
                priority=min(100, profile.priority_base + 15),
                trigger_reason=f"session:{session.session.value}",
                session=session.session,
                boost_multiplier=1.0,
            )

        base = self._base_interval(profile, session.session)
        boost = 1.0
        reasons = [f"session:{session.session.value}"]

        if profile.allow_event_boost:
            boost = self.calendar.boost_for_symbol(watch_symbol, session.as_of_ist)
            if boost > 1.0:
                reasons.extend(self.calendar.reasons(session.as_of_ist, watch_symbol))

        # Load / queue backoff — never starve, but slow non-critical work
        if system_load_high or queue_depth > 20:
            if profile.priority_base < 70:
                base = int(base * 2)
                reasons.append("load_backoff")

        interval = max(5, int(base / boost)) if boost > 1 else base
        # Cap live floor
        if session.allow_live_polling and profile.live_interval_seconds <= 60:
            interval = max(profile.live_interval_seconds // 2 if boost > 1 else profile.live_interval_seconds, interval)
            interval = max(15, interval)

        due = last_run_at is None or (now_ts - last_run_at) >= interval
        priority = min(100, int(profile.priority_base + (20 if boost > 1 else 0)))

        return ScheduleDecision(
            job_id=profile.job_id,
            interval_seconds=interval,
            should_run=due,
            priority=priority,
            trigger_reason="+".join(reasons),
            session=session.session,
            boost_multiplier=boost,
        )

    def _base_interval(self, profile: ScheduleProfile, session: MarketSession) -> int:
        if session in {MarketSession.LIVE_MARKET, MarketSession.MARKET_OPEN}:
            return profile.live_interval_seconds
        if session == MarketSession.PRE_MARKET:
            return max(profile.live_interval_seconds, 60)
        if session == MarketSession.POST_MARKET:
            return profile.after_close_interval_seconds or profile.quiet_interval_seconds
        if session == MarketSession.AFTER_CLOSE:
            return profile.after_close_interval_seconds or profile.quiet_interval_seconds
        if session == MarketSession.OVERNIGHT:
            return profile.overnight_interval_seconds
        if session in {MarketSession.WEEKEND, MarketSession.HOLIDAY}:
            return profile.weekend_interval_seconds
        return profile.quiet_interval_seconds
