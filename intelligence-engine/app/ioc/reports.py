"""IOC operational reports — narrative over monitoring state only."""

from __future__ import annotations

from typing import Any

from app.ioc.models import (
    HealthStatus,
    IocDashboard,
    OpsAlert,
    OpsReport,
    OpsReportType,
    ReadinessReport,
)


def build_report(
    report_type: OpsReportType | str,
    *,
    dashboard: IocDashboard,
    readiness: ReadinessReport,
    alerts: list[OpsAlert],
) -> OpsReport:
    rtype = OpsReportType(report_type) if not isinstance(report_type, OpsReportType) else report_type
    title = {
        OpsReportType.DAILY_OPERATIONS: "Daily Operations Report",
        OpsReportType.MORNING_READINESS: "Morning Readiness Report",
        OpsReportType.MARKET_OPEN: "Market Open Checklist",
        OpsReportType.END_OF_DAY: "End of Day Report",
        OpsReportType.WEEKLY_SUMMARY: "Weekly Operations Summary",
    }[rtype]

    sections: dict[str, Any] = {
        "overall_health": dashboard.overall_health.value,
        "engine_status": {k: v.value for k, v in dashboard.engine_status.items()},
        "platform_status": {k: v.value for k, v in dashboard.platform_status.items()},
        "pipeline_status": {k: v.value for k, v in dashboard.pipeline_status.items()},
        "provider_health": [p.model_dump(mode="json") for p in dashboard.provider_health],
        "data_freshness": dashboard.data_freshness,
        "research_pipeline": dashboard.research_pipeline,
        "publication_queue": dashboard.publication_queue,
        "replay_queue": dashboard.replay_queue,
        "cre_queue": dashboard.cre_queue,
        "latest_failures": [c.model_dump(mode="json") for c in dashboard.latest_failures[:20]],
        "readiness": readiness.model_dump(mode="json"),
    }

    if rtype == OpsReportType.MORNING_READINESS:
        sections["checklist"] = [i.model_dump(mode="json") for i in readiness.checklist]
        sections["blockers"] = readiness.blockers
    elif rtype == OpsReportType.MARKET_OPEN:
        sections["market_open_gate"] = {
            "ready": readiness.ready,
            "required": ["market_data", "features", "orch", "e01", "l4", "e10"],
        }
    elif rtype == OpsReportType.END_OF_DAY:
        sections["eod_focus"] = {
            "publications": dashboard.publication_queue,
            "replay": dashboard.replay_queue,
            "cre": dashboard.cre_queue,
            "failures": len(dashboard.latest_failures),
        }
    elif rtype == OpsReportType.WEEKLY_SUMMARY:
        sections["weekly_focus"] = {
            "alert_count": len(alerts),
            "critical_alerts": sum(1 for a in alerts if a.severity.value == "critical"),
            "engines_unhealthy": [
                k for k, v in dashboard.engine_status.items() if v != HealthStatus.HEALTHY
            ],
            "platforms_unhealthy": [
                k for k, v in dashboard.platform_status.items() if v != HealthStatus.HEALTHY
            ],
        }

    summary = (
        f"{title}: overall={dashboard.overall_health.value}; "
        f"ready={readiness.ready}; "
        f"active_alerts={len(alerts)}; "
        f"failures={len(dashboard.latest_failures)}"
    )
    return OpsReport(
        report_type=rtype,
        title=title,
        overall_status=dashboard.overall_health,
        summary=summary,
        sections=sections,
        alerts=alerts[:50],
    )
