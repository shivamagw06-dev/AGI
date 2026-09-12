"""Knowledge Freshness Engine — per-object age, status, and 'current as of' statements."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

from app.contracts.models import KnowledgeObjectType
from app.krig.policies import BundleSection

IST = ZoneInfo("Asia/Kolkata")


@dataclass(frozen=True)
class FreshnessSla:
    label: str
    max_age_seconds: int


# Institutional defaults (shared with KRIG section assembly)
SLA_BY_SECTION: dict[BundleSection, FreshnessSla] = {
    BundleSection.COMPANY: FreshnessSla("7 days", 7 * 86400),
    BundleSection.FINANCIALS: FreshnessSla("Quarterly", 7 * 86400),
    BundleSection.VALUATION: FreshnessSla("30 seconds", 30),
    BundleSection.CORPORATE_EVENTS: FreshnessSla("1 day", 86400),
    BundleSection.SECTOR: FreshnessSla("1 day", 86400),
    BundleSection.MARKET: FreshnessSla("30 seconds", 30),
    BundleSection.MACRO: FreshnessSla("1 hour", 3600),
    BundleSection.LEARNING: FreshnessSla("1 day", 86400),
    BundleSection.MEMORY: FreshnessSla("1 day", 86400),
    BundleSection.TIMELINE: FreshnessSla("1 day", 86400),
    BundleSection.RELATIONSHIPS: FreshnessSla("1 day", 86400),
    BundleSection.MONITORING: FreshnessSla("1 day", 86400),
    BundleSection.EVIDENCE: FreshnessSla("1 day", 86400),
    BundleSection.CONFLICTS: FreshnessSla("1 day", 86400),
}

OBJECT_TYPE_SLA: dict[KnowledgeObjectType, FreshnessSla] = {
    KnowledgeObjectType.MARKET_SNAPSHOT: FreshnessSla("30–60 seconds (live)", 60),
    KnowledgeObjectType.COMPANY_PROFILE: FreshnessSla("1 day", 86400),
    KnowledgeObjectType.FINANCIAL_STATEMENT: FreshnessSla("6–12 hours", 12 * 3600),
    KnowledgeObjectType.CORPORATE_EVENT: FreshnessSla("30 minutes (live)", 30 * 60),
    KnowledgeObjectType.CORPORATE_ACTION: FreshnessSla("30 minutes", 30 * 60),
    KnowledgeObjectType.OWNERSHIP: FreshnessSla("7 days", 7 * 86400),
    KnowledgeObjectType.ANALYST_CONSENSUS: FreshnessSla("12 hours", 12 * 3600),
    KnowledgeObjectType.NEWS_EVENT: FreshnessSla("5 minutes (live)", 5 * 60),
    KnowledgeObjectType.SECTOR_KNOWLEDGE: FreshnessSla("1 day", 86400),
    KnowledgeObjectType.MARKET_KNOWLEDGE: FreshnessSla("1 hour", 3600),
}

# Human-facing status vocabulary (Sprint 6.5 Operate)
STATUS_FRESH = "Fresh"
STATUS_NEEDS_REFRESH = "Needs Refresh"
STATUS_MISSING = "Missing"
STATUS_UNKNOWN = "Unknown"


def _parse_ts(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value:
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def format_age(age_seconds: int | None) -> str | None:
    if age_seconds is None:
        return None
    age = max(0, int(age_seconds))
    if age < 60:
        return f"{age} seconds"
    if age < 3600:
        mins = age // 60
        return f"{mins} minute" if mins == 1 else f"{mins} minutes"
    if age < 86400:
        hours = age // 3600
        return f"{hours} hour" if hours == 1 else f"{hours} hours"
    days = age // 86400
    return f"{days} day" if days == 1 else f"{days} days"


def current_as_of_statement(updated_at: Any, *, now: datetime | None = None) -> str | None:
    """IE-facing sentence: 'My knowledge is current as of 10:32 AM IST.'"""
    ts = _parse_ts(updated_at)
    if ts is None:
        return None
    ist = ts.astimezone(IST)
    # 10:32 AM style
    stamp = ist.strftime("%I:%M %p IST").lstrip("0")
    date_part = ist.strftime("%d %b %Y")
    return f"My knowledge is current as of {stamp} ({date_part})."


def _report(
    *,
    status: str,
    sla: FreshnessSla,
    updated: str | None,
    age_seconds: int | None,
    needs_refresh: bool,
    subject: str | None = None,
    object_type: str | None = None,
) -> dict[str, Any]:
    return {
        "subject": subject,
        "object_type": object_type,
        "status": status,
        # Backward-compatible alias used by older KRIG consumers
        "status_legacy": "Stale" if status == STATUS_NEEDS_REFRESH else status,
        "sla": sla.label,
        "updated": updated,
        "age_seconds": age_seconds,
        "age": format_age(age_seconds),
        "freshness": format_age(age_seconds),
        "needs_refresh": needs_refresh,
        "current_as_of": current_as_of_statement(updated),
    }


def evaluate_freshness(
    section: BundleSection,
    *,
    updated_at: Any = None,
    present: bool = True,
    now: datetime | None = None,
    subject: str | None = None,
) -> dict[str, Any]:
    sla = SLA_BY_SECTION[section]
    return _evaluate(sla, updated_at=updated_at, present=present, now=now, subject=subject, object_type=section.value)


def evaluate_object_freshness(
    object_type: KnowledgeObjectType | str,
    *,
    updated_at: Any = None,
    present: bool = True,
    now: datetime | None = None,
    subject: str | None = None,
) -> dict[str, Any]:
    if isinstance(object_type, str):
        try:
            object_type = KnowledgeObjectType(object_type)
        except Exception:
            sla = FreshnessSla("1 day", 86400)
            return _evaluate(sla, updated_at=updated_at, present=present, now=now, subject=subject, object_type=object_type)
    sla = OBJECT_TYPE_SLA.get(object_type, FreshnessSla("1 day", 86400))
    return _evaluate(
        sla,
        updated_at=updated_at,
        present=present,
        now=now,
        subject=subject,
        object_type=object_type.value,
    )


def _evaluate(
    sla: FreshnessSla,
    *,
    updated_at: Any,
    present: bool,
    now: datetime | None,
    subject: str | None,
    object_type: str | None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    if not present:
        return _report(
            status=STATUS_MISSING,
            sla=sla,
            updated=None,
            age_seconds=None,
            needs_refresh=True,
            subject=subject,
            object_type=object_type,
        )
    ts = _parse_ts(updated_at)
    if ts is None:
        return _report(
            status=STATUS_UNKNOWN,
            sla=sla,
            updated=None,
            age_seconds=None,
            needs_refresh=True,
            subject=subject,
            object_type=object_type,
        )
    age = max(0, int((now - ts).total_seconds()))
    fresh = age <= sla.max_age_seconds
    return _report(
        status=STATUS_FRESH if fresh else STATUS_NEEDS_REFRESH,
        sla=sla,
        updated=ts.isoformat(),
        age_seconds=age,
        needs_refresh=not fresh,
        subject=subject,
        object_type=object_type,
    )


class KnowledgeFreshnessEngine:
    """First-class freshness for Knowledge Objects + KRIG sections."""

    def register(
        self,
        store,
        *,
        object_type: str,
        subject_key: str,
        updated_at: str,
        report: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        report = report or evaluate_object_freshness(
            object_type, updated_at=updated_at, present=True, subject=subject_key
        )
        store.upsert_freshness(
            object_type=object_type,
            subject_key=subject_key,
            updated_at=updated_at,
            status=report.get("status"),
            age_seconds=report.get("age_seconds"),
            sla_label=report.get("sla"),
            current_as_of=report.get("current_as_of"),
        )
        return report

    def section_report(
        self,
        section: BundleSection,
        *,
        updated_at: Any,
        present: bool,
        subject: str | None = None,
    ) -> dict[str, Any]:
        return evaluate_freshness(section, updated_at=updated_at, present=present, subject=subject)

    def object_report(
        self,
        object_type: KnowledgeObjectType | str,
        *,
        updated_at: Any,
        present: bool = True,
        subject: str | None = None,
    ) -> dict[str, Any]:
        return evaluate_object_freshness(
            object_type, updated_at=updated_at, present=present, subject=subject
        )

    def report_for_store(self, store, *, object_type: str, subject_key: str) -> dict[str, Any]:
        row = store.get_freshness(object_type=object_type, subject_key=subject_key)
        if not row:
            return evaluate_object_freshness(object_type, present=False, subject=subject_key)
        return evaluate_object_freshness(
            object_type,
            updated_at=row.get("updated_at"),
            present=True,
            subject=subject_key,
        )

    def portfolio_snapshot(self, store, *, watchlist: tuple[str, ...] = ()) -> dict[str, Any]:
        """Mission Control / overnight health summary."""
        symbols = [s.upper() for s in watchlist] or ["INFY", "RELIANCE", "TCS", "HDFCBANK"]
        objects: list[dict[str, Any]] = []
        for symbol in symbols:
            profile = store.get_company_profile(symbol)
            objects.append(
                self.object_report(
                    KnowledgeObjectType.COMPANY_PROFILE,
                    updated_at=(profile or {}).get("updated_at"),
                    present=profile is not None,
                    subject=symbol,
                )
            )
            market = store.get_latest_market(symbol)
            objects.append(
                self.object_report(
                    KnowledgeObjectType.MARKET_SNAPSHOT,
                    updated_at=(market or {}).get("updated_at") or (market or {}).get("as_of"),
                    present=market is not None,
                    subject=symbol,
                )
            )
        sector = store.get_sector_knowledge("information_technology")
        objects.append(
            self.object_report(
                KnowledgeObjectType.SECTOR_KNOWLEDGE,
                updated_at=(sector or {}).get("updated_at"),
                present=sector is not None,
                subject="information_technology",
            )
        )
        registry = store.list_freshness(limit=100)
        needs = [o for o in objects if o.get("needs_refresh")]
        return {
            "objects": objects,
            "registry_count": len(registry),
            "fresh_count": sum(1 for o in objects if o.get("status") == STATUS_FRESH),
            "needs_refresh_count": len(needs),
            "missing_count": sum(1 for o in objects if o.get("status") == STATUS_MISSING),
            "samples_needing_refresh": needs[:10],
        }


# Backward-compatible alias
FreshnessEngine = KnowledgeFreshnessEngine
