"""IOC P0 — Investment Operations Centre (monitor only)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.cre.service import CREService
from app.features.service import FeatureRegistryService
from app.ioc.flags import IocFlags
from app.ioc.models import HealthStatus, OpsReportType
from app.ioc.service import IocService
from app.kip.service import KipService
from app.main import app
from app.market_data.client import MarketDataClient
from app.orch.l2.executor import L2FeatureBuildService
from app.orch.ledger import OrchLedger
from app.rms.service import RmsService
from app.rsp.service import RspService
from app.validation.service import ValidationService
from app.aws.service import AwsService
from app.core.config import get_settings


def _svc() -> IocService:
    features = FeatureRegistryService()
    ledger = OrchLedger()
    l2 = L2FeatureBuildService(features, orch_ledger=ledger)
    kip = KipService()
    rsp = RspService(kip=kip)
    rms = RmsService(kip=kip, rsp=rsp)
    cre = CREService()
    validation = ValidationService()
    md = MarketDataClient.from_settings(get_settings())
    aws = AwsService(kip=kip, rsp=rsp, rms=rms, cre=cre, validation=validation)
    return IocService(
        market_data=md,
        features=features,
        orch_l2=l2,
        orch_ledger=ledger,
        validation=validation,
        cre=cre,
        kip=kip,
        rsp=rsp,
        rms=rms,
        aws=aws,
    )


def test_probe_and_dashboard_monitor_only():
    svc = _svc()
    checks = svc.probe()
    assert checks
    names = {c.name for c in checks}
    assert "provider_freshness" in names or any(c.category == "provider" for c in checks)
    assert "feature_freshness" in names
    assert "engine_completion" in names or any(c.category == "engine" for c in checks)

    dash = svc.dashboard()
    assert dash.monitors_only is True
    assert isinstance(dash.overall_health, HealthStatus)
    assert "e01" in dash.engine_status
    assert "l4" in dash.engine_status
    assert "kip" in dash.platform_status
    assert "aws" in dash.platform_status
    assert "market_data" in dash.platform_status
    assert dash.data_freshness
    assert dash.ioc_version.startswith("ioc-")


def test_alerts_and_readiness():
    svc = _svc()
    alerts = svc.alerts()
    assert isinstance(alerts, list)
    # With empty kip store, prediction/knowledge may warn — still structured
    for a in alerts:
        assert a.kind
        assert a.severity
        assert a.component

    ready = svc.readiness()
    assert ready.checklist
    items = {i.item for i in ready.checklist}
    assert "market_data" in items
    assert "e10_portfolio" in items
    assert "kip_memory" in items


def test_reports():
    svc = _svc()
    for rtype in (
        "daily_operations",
        "morning_readiness",
        "market_open",
        "end_of_day",
        "weekly_operations",
    ):
        rpt = svc.report(rtype)
        assert rpt.report_type == OpsReportType(rtype)
        assert rpt.title
        assert rpt.summary
        assert rpt.sections
        assert rpt.overall_status in HealthStatus


def test_flags_and_contract():
    disabled = IocService(flags=IocFlags(ioc=False))
    with pytest.raises(RuntimeError, match="IOC is disabled"):
        disabled.dashboard()

    no_alerts = IocService(flags=IocFlags(ioc_alerts=False), features=FeatureRegistryService())
    with pytest.raises(RuntimeError, match="IOC_ALERTS"):
        no_alerts.alerts()

    no_reports = IocService(flags=IocFlags(ioc_reports=False), features=FeatureRegistryService())
    with pytest.raises(RuntimeError, match="IOC_REPORTS"):
        no_reports.report()

    h = _svc().health()
    assert h["monitors_only"] is True
    assert h["creates_opinions"] is False
    assert h["performs_research"] is False
    assert "trading" in h["out_of_scope"]
    assert "research" in h["out_of_scope"]


def test_no_research_logic_surface():
    import app.engines as engines
    import app.ioc as ioc

    assert hasattr(ioc, "IocService")
    assert not hasattr(engines, "ioc")


@pytest.mark.asyncio
async def test_ioc_http_apis():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/v1/ioc/health")
        assert health.status_code == 200
        body = health.json()
        assert body["platform"] == "IOC"
        assert body["flags"]["IOC"] is True
        assert body["monitors_only"] is True

        dash = await client.get("/v1/ioc/dashboard")
        assert dash.status_code == 200
        assert dash.json()["overall_health"]
        assert dash.json()["engine_status"]

        alerts = await client.get("/v1/ioc/alerts")
        assert alerts.status_code == 200
        assert "alerts" in alerts.json()

        providers = await client.get("/v1/ioc/providers")
        assert providers.status_code == 200
        assert "providers" in providers.json()

        readiness = await client.get("/v1/ioc/readiness")
        assert readiness.status_code == 200
        assert readiness.json()["checklist"]

        report = await client.get("/v1/ioc/report", params={"type": "morning_readiness"})
        assert report.status_code == 200
        assert report.json()["report_type"] == "morning_readiness"
