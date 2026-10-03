"""Sprint 6.5 — Adaptive Knowledge Orchestrator tests."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.ako.calendar import EventCalendar, EventKind, InstitutionalEvent
from app.ako.orchestrator import AdaptiveKnowledgeOrchestrator
from app.ako.schedule_engine import ScheduleEngine
from app.ako.schedule_profiles import PROFILES
from app.ako.sessions import IST, MarketSession, resolve_session
from app.config.settings import Settings
from app.main import create_app


def _ist(y, m, d, hh, mm=0) -> datetime:
    return datetime(y, m, d, hh, mm, tzinfo=IST)


class TestMarketSessions:
    def test_live_market_weekday(self):
        s = resolve_session(_ist(2026, 7, 28, 10, 0))  # Tuesday
        assert s.session == MarketSession.LIVE_MARKET
        assert s.allow_live_polling is True
        assert s.allow_heavy_rebuild is False

    def test_pre_market(self):
        s = resolve_session(_ist(2026, 7, 28, 8, 45))
        assert s.session == MarketSession.PRE_MARKET

    def test_after_close(self):
        s = resolve_session(_ist(2026, 7, 28, 16, 30))
        assert s.session == MarketSession.AFTER_CLOSE
        assert s.allow_live_polling is False

    def test_overnight(self):
        s = resolve_session(_ist(2026, 7, 28, 23, 30))
        assert s.session == MarketSession.OVERNIGHT
        assert s.allow_heavy_rebuild is True

    def test_weekend(self):
        s = resolve_session(_ist(2026, 8, 1, 10, 0))  # Saturday
        assert s.session == MarketSession.WEEKEND
        assert s.allow_heavy_rebuild is True

    def test_holiday(self):
        s = resolve_session(_ist(2026, 1, 26, 10, 0))  # Republic Day
        assert s.session == MarketSession.HOLIDAY


class TestAdaptiveSchedule:
    def test_live_interval_shorter_than_quiet(self):
        engine = ScheduleEngine()
        profile = PROFILES["YahooCollector"]
        live = resolve_session(_ist(2026, 7, 27, 11, 0))  # Mon — no Infy earnings boost day offset
        # Use calendar without Infy boost for baseline
        engine = ScheduleEngine(EventCalendar(events=[]))
        d_live = engine.decide(
            profile, live, last_run_at=None, now_ts=1_000_000.0, watch_symbol="TCS"
        )
        quiet = resolve_session(_ist(2026, 7, 27, 20, 0))
        d_quiet = engine.decide(
            profile, quiet, last_run_at=None, now_ts=1_000_000.0, watch_symbol="TCS"
        )
        assert d_live.interval_seconds == 30
        assert d_quiet.interval_seconds > d_live.interval_seconds

    def test_earnings_boost_shortens_interval(self):
        cal = EventCalendar(
            events=[
                InstitutionalEvent(
                    event_id="infy_test",
                    kind=EventKind.EARNINGS,
                    title="Infosys Earnings",
                    event_date=date(2026, 7, 28),
                    symbols=("INFY",),
                    boost_multiplier=4.0,
                    boost_hours_before=12,
                    boost_hours_after=18,
                )
            ]
        )
        engine = ScheduleEngine(cal)
        profile = PROFILES["YahooCollector"]
        session = resolve_session(_ist(2026, 7, 28, 11, 0))
        boosted = engine.decide(
            profile, session, last_run_at=None, now_ts=1.0, watch_symbol="INFY"
        )
        baseline = ScheduleEngine(EventCalendar(events=[])).decide(
            profile, session, last_run_at=None, now_ts=1.0, watch_symbol="INFY"
        )
        assert boosted.boost_multiplier == 4.0
        assert boosted.interval_seconds < baseline.interval_seconds
        assert "earnings" in boosted.trigger_reason

    def test_bhavcopy_once_after_close(self):
        engine = ScheduleEngine(EventCalendar(events=[]))
        profile = PROFILES["NSEBhavcopyCollector"]
        live = resolve_session(_ist(2026, 7, 28, 11, 0))
        d_live = engine.decide(profile, live, last_run_at=None, now_ts=1.0)
        assert d_live.should_run is False
        after = resolve_session(_ist(2026, 7, 28, 16, 30))
        d_after = engine.decide(profile, after, last_run_at=None, now_ts=1.0, session_run_done=False)
        assert d_after.should_run is True
        d_done = engine.decide(profile, after, last_run_at=1.0, now_ts=2.0, session_run_done=True)
        assert d_done.should_run is False

    def test_overnight_heavy_blocked_during_live(self):
        engine = ScheduleEngine(EventCalendar(events=[]))
        profile = PROFILES["OvernightKnowledgeRebuild"]
        live = resolve_session(_ist(2026, 7, 28, 11, 0))
        d = engine.decide(profile, live, last_run_at=None, now_ts=1.0)
        assert d.should_run is False
        assert d.skip_reason == "not_overnight"
        night = resolve_session(_ist(2026, 7, 28, 23, 30))
        d_night = engine.decide(profile, night, last_run_at=None, now_ts=1.0)
        assert d_night.should_run is True


class TestOrchestratorExecution:
    def test_tick_runs_due_jobs_and_records_telemetry(self):
        ako = AdaptiveKnowledgeOrchestrator(calendar=EventCalendar(events=[]), tick_seconds=60)
        runs: list[str] = []

        def runner():
            runs.append("yahoo")
            return type("R", (), {"accepted": [1], "knowledge_objects": [1], "learning_events": []})()

        ako.register_collector("YahooCollector", runner, profile=PROFILES["YahooCollector"])
        executed = ako.tick_once(clock=_ist(2026, 7, 27, 11, 0), now_ts=1000.0)
        assert len(executed) == 1
        assert executed[0]["job_id"] == "YahooCollector"
        assert runs == ["yahoo"]
        snap = ako.mission_control_snapshot()
        assert snap["principles"]["ask_never_triggers_collectors"] is True
        assert snap["telemetry"]["stats"]["executions_tracked"] >= 1

    def test_overnight_runs_only_overnight(self):
        ako = AdaptiveKnowledgeOrchestrator(calendar=EventCalendar(events=[]))
        hooks: list[str] = []
        ako.register_collector(
            "OvernightKnowledgeRebuild",
            lambda: hooks.append("runner"),
            profile=PROFILES["OvernightKnowledgeRebuild"],
        )
        ako.register_overnight_hook(lambda: hooks.append("hook"))
        live_exec = ako.tick_once(clock=_ist(2026, 7, 28, 11, 0), now_ts=1.0)
        assert live_exec == []
        night_exec = ako.tick_once(clock=_ist(2026, 7, 28, 23, 15), now_ts=2.0)
        assert any(e["job_id"] == "OvernightKnowledgeRebuild" for e in night_exec)
        assert "hook" in hooks

    def test_priority_orders_announcements_before_ir(self):
        ako = AdaptiveKnowledgeOrchestrator(calendar=EventCalendar(events=[]))
        order: list[str] = []
        ako.register_collector(
            "CompanyIRCollector",
            lambda: order.append("ir") or None,
            profile=PROFILES["CompanyIRCollector"],
        )
        ako.register_collector(
            "NSEAnnouncementCollector",
            lambda: order.append("nse") or None,
            profile=PROFILES["NSEAnnouncementCollector"],
        )
        ako.tick_once(clock=_ist(2026, 7, 27, 11, 0), now_ts=1.0)
        assert order[0] == "nse"


class TestAskSeparation:
    def test_krig_bundle_path_has_no_collector_side_effects(self, tmp_path: Path):
        db = tmp_path / "ako.db"
        settings = Settings(
            db_path=db,
            scheduler_enabled=False,
            live_collectors_enabled=False,
            ako_enabled=True,
        )
        app = create_app(settings)
        with TestClient(app) as client:
            # KRIG retrieve must not invoke collectors
            before = client.get("/v1/ako/mission-control").json()
            runs_before = sum(j["run_count"] for j in before["jobs"])
            resp = client.post("/v1/knowledge/bundle", json={"symbols": ["INFY"], "question": "Infosys"})
            assert resp.status_code == 200
            after = client.get("/v1/ako/mission-control").json()
            runs_after = sum(j["run_count"] for j in after["jobs"])
            assert runs_after == runs_before
            body = resp.json()
            assert "bundle_id" in body or "policy" in body or "sections" in body or "checklist" in body

    def test_ie_client_has_no_collect_methods(self):
        """Intelligence Engine KAIP/KRIG client is read-only — never triggers collectors."""
        client_path = Path(__file__).resolve().parents[2] / "intelligence-engine" / "app" / "kaip_client" / "client.py"
        source = client_path.read_text(encoding="utf-8")
        assert "def collect" not in source
        assert "run_collector" not in source
        assert "/v1/internal/run" not in source
        assert "retrieve_bundle" in source
        assert "Ask performs zero data discovery" in source or "zero data discovery" in source
