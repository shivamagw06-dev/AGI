"""IOC service — Investment Operations Centre mission control (monitor only)."""

from __future__ import annotations

from typing import Any

from app.core.config import get_settings
from app.ioc.alerts import alerts_from_checks
from app.ioc.checks import (
    check_component,
    check_latency,
    check_provider_snapshot,
    rollup,
    soft_health,
    worst_status,
)
from app.ioc.flags import IocFlags
from app.ioc.models import (
    IOC_VERSION,
    ComponentCheck,
    HealthStatus,
    IocDashboard,
    OpsAlert,
    OpsReport,
    ProviderStatus,
    ReadinessItem,
    ReadinessReport,
)
from app.ioc.reports import build_report


class IocService:
    """Operational mission control. No research, no opinions, no portfolio logic."""

    def __init__(
        self,
        flags: IocFlags | None = None,
        *,
        market_data: Any | None = None,
        features: Any | None = None,
        orch_l2: Any | None = None,
        orch_ledger: Any | None = None,
        e01: Any | None = None,
        e02: Any | None = None,
        e03: Any | None = None,
        e04: Any | None = None,
        e05: Any | None = None,
        e08: Any | None = None,
        e09: Any | None = None,
        e10: Any | None = None,
        e11: Any | None = None,
        e13: Any | None = None,
        e14: Any | None = None,
        l4: Any | None = None,
        validation: Any | None = None,
        cre: Any | None = None,
        kip: Any | None = None,
        rsp: Any | None = None,
        rms: Any | None = None,
        aws: Any | None = None,
    ) -> None:
        self.flags = flags or IocFlags.from_settings(get_settings())
        self.market_data = market_data
        self.features = features
        self.orch_l2 = orch_l2
        self.orch_ledger = orch_ledger
        self.engines = {
            "e01": e01,
            "e02": e02,
            "e03": e03,
            "e04": e04,
            "e05": e05,
            "e08": e08,
            "e09": e09,
            "e10": e10,
            "e11": e11,
            "e13": e13,
            "e14": e14,
            "l4": l4,
        }
        self.validation = validation
        self.cre = cre
        self.kip = kip
        self.rsp = rsp
        self.rms = rms
        self.aws = aws
        self._last_checks: list[ComponentCheck] = []
        self._last_alerts: list[OpsAlert] = []

    def probe(self) -> list[ComponentCheck]:
        self._require()
        checks: list[ComponentCheck] = []

        # Market data / providers
        md_fn = None
        if self.market_data is not None:
            health_obj = getattr(self.market_data, "health", None)
            if callable(health_obj):
                md_fn = health_obj
            elif health_obj is not None and hasattr(health_obj, "snapshot"):
                md_fn = health_obj.snapshot
        md_payload, md_ms, md_err = soft_health(md_fn)
        checks.extend(check_provider_snapshot(md_payload, latency_ms=md_ms))
        if md_err:
            checks.append(
                check_component("market_data", "provider", "provider_freshness", None, latency_ms=md_ms, error=md_err)
            )
        checks.append(check_latency("api_latency_market_data", "market_data", md_ms))

        # Feature registry
        feat_payload, feat_ms, feat_err = soft_health(getattr(self.features, "health", None) if self.features else None)
        checks.append(check_component("features", "feature", "feature_freshness", feat_payload, latency_ms=feat_ms, error=feat_err))
        checks.append(check_latency("api_latency_features", "features", feat_ms))

        # ORCH
        orch_payload, orch_ms, orch_err = soft_health(getattr(self.orch_l2, "health", None) if self.orch_l2 else None)
        checks.append(check_component("orch_l2", "orch", "orch_queue", orch_payload, latency_ms=orch_ms, error=orch_err))
        if self.orch_ledger is not None:
            ledger_payload, ledger_ms, ledger_err = soft_health(getattr(self.orch_ledger, "status_summary", None))
            checks.append(
                check_component("orch_ledger", "orch", "engine_completion", ledger_payload, latency_ms=ledger_ms, error=ledger_err)
            )

        # Engines + L4 + E10
        for name, svc in self.engines.items():
            payload, ms, err = soft_health(getattr(svc, "health", None) if svc else None)
            extra = None
            if name == "e10" and svc is not None:
                port = None
                try:
                    port = svc.get_portfolio()
                except Exception:
                    port = None
                if port is None and (payload or {}).get("ok") is True:
                    # portfolio readiness warning — still monitoring only
                    extra = HealthStatus.WARNING
                    if payload is not None:
                        payload = {**payload, "portfolio_present": False}
            checks.append(
                check_component(name, "engine", "engine_completion", payload, latency_ms=ms, error=err, extra_status=extra)
            )
            checks.append(check_latency(f"api_latency_{name}", name, ms))

        # Platforms
        for name, svc in (
            ("replay", self.validation),
            ("cre", self.cre),
            ("kip", self.kip),
            ("rsp", self.rsp),
            ("rms", self.rms),
            ("aws", self.aws),
        ):
            payload, ms, err = soft_health(getattr(svc, "health", None) if svc else None)
            check_name = {
                "replay": "replay_success",
                "cre": "cre_success",
                "kip": "knowledge_ingestion",
                "rsp": "research_publication",
                "rms": "research_publication",
                "aws": "engine_completion",
            }[name]
            # prediction tracking via kip stats
            extra = None
            if name == "kip" and isinstance(payload, dict):
                stats = payload.get("stats") or {}
                if stats.get("documents", 0) == 0:
                    extra = HealthStatus.STALE
                checks.append(
                    check_component(
                        "kip_predictions",
                        "platform",
                        "prediction_tracking",
                        {"predictions": stats.get("predictions", 0)},
                        extra_status=HealthStatus.WARNING if stats.get("predictions", 0) == 0 else HealthStatus.HEALTHY,
                    )
                )
            if name == "rms" and svc is not None:
                dash = None
                try:
                    dash = svc.dashboard()
                except Exception:
                    dash = None
                if dash is not None:
                    pub_q = list(getattr(dash, "draft_queue", []) or [])
                    rev_q = list(getattr(dash, "review_queue", []) or [])
                    checks.append(
                        check_component(
                            "rms_queues",
                            "pipeline",
                            "research_publication",
                            {
                                "draft_queue": len(pub_q),
                                "review_queue": len(rev_q),
                                "published": getattr(getattr(dash, "research_pipeline", None), "published", None),
                            },
                        )
                    )
            checks.append(check_component(name, "platform", check_name, payload, latency_ms=ms, error=err, extra_status=extra))
            checks.append(check_latency(f"api_latency_{name}", name, ms))

        # Database latency proxy — feature cache / store stats if present
        if isinstance(feat_payload, dict):
            cache = feat_payload.get("cache") or {}
            db_status = HealthStatus.HEALTHY if cache else HealthStatus.WARNING
            checks.append(
                ComponentCheck(
                    component="database",
                    category="pipeline",
                    name="database_latency",
                    status=db_status,
                    message="feature cache stats present" if cache else "database/cache stats unavailable",
                    details={"cache": cache},
                    latency_ms=feat_ms,
                )
            )

        # Portfolio generation explicit check
        e10 = self.engines.get("e10")
        if e10 is not None:
            try:
                port = e10.get_portfolio()
                st = HealthStatus.HEALTHY if port is not None else HealthStatus.WARNING
                msg = "portfolio generated" if port is not None else "portfolio not generated"
            except Exception as exc:
                st = HealthStatus.CRITICAL
                msg = str(exc)
                port = None
            checks.append(
                ComponentCheck(
                    component="e10_portfolio",
                    category="pipeline",
                    name="portfolio_generation",
                    status=st,
                    message=msg,
                    details={"present": port is not None},
                )
            )

        self._last_checks = checks
        return checks

    def dashboard(self) -> IocDashboard:
        self._require()
        checks = self.probe()
        alerts = self.alerts(refresh=False)

        # Group components
        by_comp: dict[str, list[ComponentCheck]] = {}
        for c in checks:
            by_comp.setdefault(c.component, []).append(c)
        components = [rollup(name, items) for name, items in sorted(by_comp.items())]

        engine_status = {
            name: rollup(name, by_comp.get(name, [])).status
            for name in ["e01", "e02", "e03", "e04", "e05", "e08", "e09", "e10", "e11", "e13", "e14", "l4"]
        }
        platform_status = {
            name: rollup(name, by_comp.get(name, [])).status
            for name in ["market_data", "features", "orch_l2", "replay", "cre", "kip", "rsp", "rms", "aws"]
        }
        pipeline_status = {
            "orch_queue": rollup("orch_l2", by_comp.get("orch_l2", [])).status,
            "research_publication": rollup("rms", by_comp.get("rms", [])).status,
            "knowledge_ingestion": rollup("kip", by_comp.get("kip", [])).status,
            "portfolio_generation": rollup("e10_portfolio", by_comp.get("e10_portfolio", [])).status,
            "replay": rollup("replay", by_comp.get("replay", [])).status,
            "cre": rollup("cre", by_comp.get("cre", [])).status,
        }

        providers: list[ProviderStatus] = []
        for c in checks:
            if c.category == "provider" and c.component.startswith("provider:"):
                d = c.details or {}
                providers.append(
                    ProviderStatus(
                        provider_id=str(d.get("provider_id") or c.component.split(":", 1)[-1]),
                        status=c.status,
                        configured=bool(d.get("configured")),
                        circuit_state=str(d.get("circuit_state") or ""),
                        ok=bool(d.get("ok")),
                        last_error=d.get("last_error"),
                        capabilities=list(d.get("capabilities") or []),
                    )
                )

        latest_failures = [c for c in checks if c.status in {HealthStatus.CRITICAL, HealthStatus.OFFLINE, HealthStatus.WARNING, HealthStatus.STALE}]
        latest_failures.sort(key=lambda c: (0 if c.status in {HealthStatus.CRITICAL, HealthStatus.OFFLINE} else 1, c.component))

        # Research / publication queues from RMS
        research_pipeline: dict[str, Any] = {}
        publication_queue: list[str] = []
        if self.rms is not None:
            try:
                dash = self.rms.dashboard()
                research_pipeline = dash.research_pipeline.model_dump(mode="json") if hasattr(dash.research_pipeline, "model_dump") else {}
                publication_queue = list(dash.draft_queue or []) + list(dash.review_queue or [])
            except Exception as exc:
                research_pipeline = {"error": str(exc)}

        replay_queue: dict[str, Any] = {}
        if self.validation is not None:
            try:
                runs = self.validation.list_runs(limit=5)
                replay_queue = {
                    "recent_runs": len(runs),
                    "run_ids": [getattr(r, "run_id", None) for r in runs[:5]],
                }
            except Exception as exc:
                replay_queue = {"error": str(exc)}

        cre_queue: dict[str, Any] = {}
        if self.cre is not None:
            try:
                h = self.cre.health()
                cre_queue = {"health": h, "scorecards": len(self.cre.list_scorecards() or [])}
            except Exception as exc:
                cre_queue = {"error": str(exc)}

        data_freshness = {
            "market_data": platform_status.get("market_data", HealthStatus.OFFLINE).value,
            "features": platform_status.get("features", HealthStatus.OFFLINE).value,
            "kip": platform_status.get("kip", HealthStatus.OFFLINE).value,
            "provider_count": len(providers),
            "providers_ok": sum(1 for p in providers if p.status == HealthStatus.HEALTHY),
        }

        overall = worst_status(
            *(engine_status.values()),
            *(platform_status.values()),
            *(pipeline_status.values()),
        )

        return IocDashboard(
            overall_health=overall,
            pipeline_status=pipeline_status,
            engine_status=engine_status,
            platform_status=platform_status,
            latest_failures=latest_failures[:30],
            provider_health=providers,
            data_freshness=data_freshness,
            research_pipeline=research_pipeline,
            publication_queue=publication_queue[:50],
            replay_queue=replay_queue,
            cre_queue=cre_queue,
            alerts=alerts[:50],
            components=components,
        )

    def health(self) -> dict[str, Any]:
        if not self.flags.ioc:
            return {
                "status": "disabled",
                "platform": "IOC",
                "ioc_version": IOC_VERSION,
                "flags": self.flags.as_dict(),
            }
        dash = self.dashboard()
        return {
            "status": "ok",
            "platform": "IOC",
            "name": "Investment Operations Centre",
            "ioc_version": IOC_VERSION,
            "overall_health": dash.overall_health.value,
            "flags": self.flags.as_dict(),
            "monitors_only": True,
            "creates_opinions": False,
            "performs_research": False,
            "monitored": [
                "MarketData",
                "FeatureRegistry",
                "ORCH",
                "Engines",
                "L4",
                "E10",
                "Replay",
                "CRE",
                "KIP",
                "RSP",
                "RMS",
                "AWS",
            ],
            "out_of_scope": ["trading", "research", "portfolio_logic", "architecture_changes"],
            "component_counts": {
                "checks": len(self._last_checks),
                "alerts": len(self._last_alerts),
                "engines": len(dash.engine_status),
                "platforms": len(dash.platform_status),
            },
        }

    def alerts(self, *, refresh: bool = True) -> list[OpsAlert]:
        self._require()
        if not self.flags.ioc_alerts:
            raise RuntimeError("IOC_ALERTS is disabled")
        checks = self.probe() if refresh or not self._last_checks else self._last_checks
        alerts = alerts_from_checks(checks)
        self._last_alerts = alerts
        return alerts

    def providers(self) -> dict[str, Any]:
        self._require()
        dash = self.dashboard()
        return {
            "providers": [p.model_dump(mode="json") for p in dash.provider_health],
            "data_freshness": dash.data_freshness,
            "overall_health": dash.overall_health.value,
            "ioc_version": IOC_VERSION,
        }

    def readiness(self) -> ReadinessReport:
        self._require()
        dash = self.dashboard()
        checklist: list[ReadinessItem] = []

        def add(item: str, status: HealthStatus, message: str = "") -> None:
            checklist.append(
                ReadinessItem(
                    item=item,
                    ready=status in {HealthStatus.HEALTHY, HealthStatus.RECOVERING},
                    status=status,
                    message=message or status.value,
                )
            )

        add("market_data", dash.platform_status.get("market_data", HealthStatus.OFFLINE))
        add("feature_registry", dash.platform_status.get("features", HealthStatus.OFFLINE))
        add("orch_l2", dash.platform_status.get("orch_l2", HealthStatus.OFFLINE))
        add("e01_macro", dash.engine_status.get("e01", HealthStatus.OFFLINE))
        add("l4_opinion", dash.engine_status.get("l4", HealthStatus.OFFLINE))
        add("e10_portfolio", dash.pipeline_status.get("portfolio_generation", HealthStatus.OFFLINE))
        add("kip_memory", dash.platform_status.get("kip", HealthStatus.OFFLINE))
        add("rms_research", dash.platform_status.get("rms", HealthStatus.OFFLINE))
        add("cre_evaluation", dash.platform_status.get("cre", HealthStatus.OFFLINE))
        add("replay_validation", dash.platform_status.get("replay", HealthStatus.OFFLINE))

        blockers = [i.item for i in checklist if not i.ready and i.status in {HealthStatus.CRITICAL, HealthStatus.OFFLINE}]
        ready = len(blockers) == 0
        return ReadinessReport(ready=ready, checklist=checklist, blockers=blockers)

    def report(self, report_type: str = "daily_operations") -> OpsReport:
        self._require()
        if not self.flags.ioc_reports:
            raise RuntimeError("IOC_REPORTS is disabled")
        dash = self.dashboard()
        readiness = self.readiness()
        alerts = self._last_alerts or self.alerts(refresh=False)
        return build_report(report_type, dashboard=dash, readiness=readiness, alerts=alerts)

    def _require(self) -> None:
        if not self.flags.ioc:
            raise RuntimeError("IOC is disabled")
