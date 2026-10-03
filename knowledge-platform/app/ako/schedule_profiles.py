"""Base schedule profiles — nature of data drives base cadence; AKO adapts from here."""

from __future__ import annotations

from dataclasses import dataclass

from app.ako.sessions import MarketSession


@dataclass(frozen=True)
class ScheduleProfile:
    job_id: str
    collector_id: str
    knowledge_kind: str
    # base intervals by session family
    live_interval_seconds: int
    quiet_interval_seconds: int
    overnight_interval_seconds: int
    after_close_interval_seconds: int | None = None  # None = skip unless due once
    weekend_interval_seconds: int = 6 * 3600
    priority_base: int = 50  # 0–100
    once_per_session: MarketSession | None = None  # e.g. bhavcopy AFTER_CLOSE
    allow_event_boost: bool = True
    overnight_heavy: bool = False


# Profiles for Sprint 6.1 registered collectors (+ logical Yahoo facets)
PROFILES: dict[str, ScheduleProfile] = {
    "YahooCollector": ScheduleProfile(
        job_id="YahooCollector",
        collector_id="YahooCollector",
        knowledge_kind="market_snapshot",
        live_interval_seconds=30,
        quiet_interval_seconds=15 * 60,
        overnight_interval_seconds=2 * 3600,
        after_close_interval_seconds=30 * 60,
        priority_base=70,
        allow_event_boost=True,
    ),
    "NSEAnnouncementCollector": ScheduleProfile(
        job_id="NSEAnnouncementCollector",
        collector_id="NSEAnnouncementCollector",
        knowledge_kind="corporate_announcements",
        live_interval_seconds=30,
        quiet_interval_seconds=15 * 60,
        overnight_interval_seconds=3 * 3600,
        after_close_interval_seconds=10 * 60,
        priority_base=80,
        allow_event_boost=True,
    ),
    "BSECorporateActionCollector": ScheduleProfile(
        job_id="BSECorporateActionCollector",
        collector_id="BSECorporateActionCollector",
        knowledge_kind="corporate_actions",
        live_interval_seconds=30 * 60,
        quiet_interval_seconds=60 * 60,
        overnight_interval_seconds=6 * 3600,
        after_close_interval_seconds=30 * 60,
        priority_base=60,
        allow_event_boost=True,
    ),
    "NSEBhavcopyCollector": ScheduleProfile(
        job_id="NSEBhavcopyCollector",
        collector_id="NSEBhavcopyCollector",
        knowledge_kind="bhavcopy",
        live_interval_seconds=24 * 3600,
        quiet_interval_seconds=24 * 3600,
        overnight_interval_seconds=24 * 3600,
        after_close_interval_seconds=0,  # run once when AFTER_CLOSE
        priority_base=85,
        once_per_session=MarketSession.AFTER_CLOSE,
        allow_event_boost=False,
    ),
    "CompanyIRCollector": ScheduleProfile(
        job_id="CompanyIRCollector",
        collector_id="CompanyIRCollector",
        knowledge_kind="company_ir",
        live_interval_seconds=10 * 60,
        quiet_interval_seconds=60 * 60,
        overnight_interval_seconds=6 * 3600,
        after_close_interval_seconds=30 * 60,
        priority_base=65,
        allow_event_boost=True,
    ),
    # Logical overnight rebuild job (no external collect — pipeline tip)
    "OvernightKnowledgeRebuild": ScheduleProfile(
        job_id="OvernightKnowledgeRebuild",
        collector_id="OvernightKnowledgeRebuild",
        knowledge_kind="rebuild",
        live_interval_seconds=24 * 3600,
        quiet_interval_seconds=24 * 3600,
        overnight_interval_seconds=3600,
        priority_base=40,
        allow_event_boost=False,
        overnight_heavy=True,
    ),
    # Logical Yahoo facets (same collector body; AKO tracks nature-of-data cadence)
    "YahooNewsFacet": ScheduleProfile(
        job_id="YahooNewsFacet",
        collector_id="YahooCollector",
        knowledge_kind="news",
        live_interval_seconds=5 * 60,
        quiet_interval_seconds=30 * 60,
        overnight_interval_seconds=2 * 3600,
        after_close_interval_seconds=15 * 60,
        priority_base=55,
        allow_event_boost=True,
    ),
    "YahooFinancialsFacet": ScheduleProfile(
        job_id="YahooFinancialsFacet",
        collector_id="YahooCollector",
        knowledge_kind="financial_statements",
        live_interval_seconds=30 * 60,
        quiet_interval_seconds=6 * 3600,
        overnight_interval_seconds=12 * 3600,
        after_close_interval_seconds=60 * 60,
        priority_base=50,
        allow_event_boost=True,
    ),
    "YahooCalendarFacet": ScheduleProfile(
        job_id="YahooCalendarFacet",
        collector_id="YahooCollector",
        knowledge_kind="calendar",
        live_interval_seconds=6 * 3600,
        quiet_interval_seconds=6 * 3600,
        overnight_interval_seconds=12 * 3600,
        priority_base=35,
        allow_event_boost=True,
    ),
}


def profile_for(job_id: str) -> ScheduleProfile | None:
    return PROFILES.get(job_id)
