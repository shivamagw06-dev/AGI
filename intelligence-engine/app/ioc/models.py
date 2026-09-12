"""IOC monitoring models — health, checks, alerts, reports."""

from __future__ import annotations

import datetime as _dt
from enum import Enum
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


IOC_VERSION = "ioc-v1.0.1"


def _utcnow() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    OFFLINE = "offline"
    STALE = "stale"
    RECOVERING = "recovering"


STATUS_RANK = {
    HealthStatus.HEALTHY: 0,
    HealthStatus.RECOVERING: 1,
    HealthStatus.STALE: 2,
    HealthStatus.WARNING: 3,
    HealthStatus.CRITICAL: 4,
    HealthStatus.OFFLINE: 5,
}


class ComponentCheck(BaseModel):
    check_id: str = Field(default_factory=lambda: _new_id("chk"))
    component: str
    category: str  # provider | feature | orch | engine | platform | pipeline
    name: str
    status: HealthStatus = HealthStatus.HEALTHY
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float | None = None
    checked_at: _dt.datetime = Field(default_factory=_utcnow)


class ComponentHealth(BaseModel):
    component: str
    status: HealthStatus
    checks: list[ComponentCheck] = Field(default_factory=list)
    summary: str = ""


class AlertSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class OpsAlert(BaseModel):
    alert_id: str = Field(default_factory=lambda: _new_id("alt"))
    kind: str
    severity: AlertSeverity = AlertSeverity.WARNING
    component: str
    message: str
    status: HealthStatus | None = None
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: _dt.datetime = Field(default_factory=_utcnow)
    active: bool = True


class ProviderStatus(BaseModel):
    provider_id: str
    status: HealthStatus
    configured: bool = False
    circuit_state: str = ""
    ok: bool = False
    last_error: str | None = None
    capabilities: list[str] = Field(default_factory=list)


class ReadinessItem(BaseModel):
    item: str
    ready: bool
    status: HealthStatus
    message: str = ""


class ReadinessReport(BaseModel):
    ready: bool
    as_of: _dt.datetime = Field(default_factory=_utcnow)
    checklist: list[ReadinessItem] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    ioc_version: str = IOC_VERSION


class OpsReportType(str, Enum):
    DAILY_OPERATIONS = "daily_operations"
    MORNING_READINESS = "morning_readiness"
    MARKET_OPEN = "market_open"
    END_OF_DAY = "end_of_day"
    WEEKLY_SUMMARY = "weekly_operations"


class OpsReport(BaseModel):
    report_id: str = Field(default_factory=lambda: _new_id("rpt"))
    report_type: OpsReportType
    title: str
    overall_status: HealthStatus
    summary: str
    sections: dict[str, Any] = Field(default_factory=dict)
    alerts: list[OpsAlert] = Field(default_factory=list)
    generated_at: _dt.datetime = Field(default_factory=_utcnow)
    ioc_version: str = IOC_VERSION


class IocDashboard(BaseModel):
    overall_health: HealthStatus
    pipeline_status: dict[str, HealthStatus] = Field(default_factory=dict)
    engine_status: dict[str, HealthStatus] = Field(default_factory=dict)
    platform_status: dict[str, HealthStatus] = Field(default_factory=dict)
    latest_failures: list[ComponentCheck] = Field(default_factory=list)
    provider_health: list[ProviderStatus] = Field(default_factory=list)
    data_freshness: dict[str, Any] = Field(default_factory=dict)
    research_pipeline: dict[str, Any] = Field(default_factory=dict)
    publication_queue: list[str] = Field(default_factory=list)
    replay_queue: dict[str, Any] = Field(default_factory=dict)
    cre_queue: dict[str, Any] = Field(default_factory=dict)
    alerts: list[OpsAlert] = Field(default_factory=list)
    components: list[ComponentHealth] = Field(default_factory=list)
    checked_at: _dt.datetime = Field(default_factory=_utcnow)
    ioc_version: str = IOC_VERSION
    monitors_only: Literal[True] = True
