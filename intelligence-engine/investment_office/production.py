"""Investment Office production facade — aggregate soft adapters only.

IO-01 adds Institutional Research Package orchestration (additive; never redesigns desk).
"""

from __future__ import annotations

from typing import Any

from investment_office.aggregate import build_desk
from investment_office.flags import flags_dict, is_enabled
from investment_office.schema import (
    IO01_PRODUCT,
    IO01_RECOMMENDATION_POLICY,
    IO01_SPEC,
    IO01_SUBSYSTEM,
    IO01_VERSION,
    IO01_WORKSTREAM_ID,
    IO_VERSION,
    PACKAGE_TYPES,
    PROGRAMME,
    PROGRAMME_SHORT,
)
from investment_office import store as io_store


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IO_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "not_an_engine": True,
        "not_a_recommendation_engine": True,
        "not_portfolio_management": True,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        # IO-01 additive fields (desk unchanged)
        "io01": {
            "workstream_id": IO01_WORKSTREAM_ID,
            "product": IO01_PRODUCT,
            "version": IO01_VERSION,
            "subsystem": IO01_SUBSYSTEM,
            "role": "orchestration_layer",
            "orchestrates_only": True,
            "never_recalculates": True,
            "never_rescores": True,
            "never_invents_conclusions": True,
            "buy_sell": False,
            "valuation": False,
            "package_types": list(PACKAGE_TYPES),
            "recommendation_policy": IO01_RECOMMENDATION_POLICY,
            "spec": IO01_SPEC,
            "consumes": [
                "financial_warehouse",
                "derived_metrics",
                "FIRE-01",
                "FIRE-02",
                "FIRE-03",
                "FIRE-04",
                "FIRE-05",
                "FIRE-06",
                "FKB",
            ],
        },
    }


def dashboard(*, ui_home: dict[str, Any] | None = None, ioc_service: Any | None = None) -> dict[str, Any]:
    desk = build_desk(ui_home=ui_home, ioc_service=ioc_service)
    if desk.get("enabled"):
        io_store.put_desk(desk)
    return desk


def cached_desk() -> dict[str, Any] | None:
    return io_store.get_desk()


def package_for_home(*, ui_home: dict[str, Any] | None = None, ioc_service: Any | None = None) -> dict[str, Any]:
    """Soft package for UiService.home — never empty when enabled."""
    desk = dashboard(ui_home=ui_home, ioc_service=ioc_service)
    if not desk.get("enabled"):
        return desk
    return {
        **desk,
        "home_strip": {
            "attention_count": len(desk.get("companies_requiring_attention") or []),
            "queue_count": len(desk.get("todays_research_queue") or []),
            "notifications": len(desk.get("notifications") or []),
            "coverage_pct": (desk.get("coverage_dashboard") or {}).get("coverage_pct"),
            "regime": (desk.get("morning_executive_brief") or {}).get("market_regime"),
            "risk": (desk.get("morning_executive_brief") or {}).get("risk_level"),
        },
    }


def package_for_ask_agi(query: str = "", *, ticker: str | None = None) -> dict[str, Any]:
    desk = cached_desk() or dashboard()
    attention = desk.get("companies_requiring_attention") or []
    hints = []
    if ticker:
        t = ticker.upper()
        hit = next((a for a in attention if a.get("ticker") == t), None)
        if hit:
            hints.append(
                f"Investment Office attention for {t}: {hit.get('priority')} — "
                f"{', '.join(hit.get('reasons') or [])}"
            )
    hints.append(
        f"IO desk: {len(attention)} companies needing attention; "
        f"{len(desk.get('todays_research_queue') or [])} research tasks queued."
    )
    for n in (desk.get("notifications") or [])[:3]:
        if n.get("message"):
            hints.append(str(n["message"])[:200])
    return {
        "enabled": bool(desk.get("enabled")),
        "programme": PROGRAMME,
        "version": IO_VERSION,
        "query": query,
        "ticker": ticker,
        "attention": [a for a in attention if not ticker or a.get("ticker") == (ticker or "").upper()][:8],
        "research_queue": (desk.get("todays_research_queue") or [])[:6],
        "executive_copilot": desk.get("executive_copilot") or {},
        "ask_agi_hints": hints[:8],
        "answer_policy": "investment_office_context_before_answer",
    }


def company(
    ticker: str,
    *,
    question: str | None = None,
    package_type: str | None = None,
    series_map: dict[str, list[dict[str, Any]]] | None = None,
    documents: list[dict[str, Any]] | None = None,
    prebuilt: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """IO-01: assemble Institutional Research Package for a company (orchestration only)."""
    if not is_enabled():
        return {
            "ok": False,
            "enabled": False,
            "workstream_id": IO01_WORKSTREAM_ID,
            "version": IO01_VERSION,
        }
    from investment_office.irp.coordinator import coordinate

    irp = coordinate(
        ticker=ticker,
        question=question,
        package_type=package_type,
        series_map=series_map,
        documents=documents,
        prebuilt=prebuilt,
    )
    io_store.record_irp(irp)
    pack = {
        "ok": True,
        "enabled": True,
        "workstream_id": IO01_WORKSTREAM_ID,
        "product": IO01_PRODUCT,
        "version": IO01_VERSION,
        "orchestrates_only": True,
        "buy_sell": False,
        "valuation": False,
        "irp": irp,
        "ticker": irp.get("ticker"),
        "package_type": irp.get("package_type"),
        "modules_invoked": irp.get("modules_invoked"),
        "sections": irp.get("sections"),
        "confidence": irp.get("confidence"),
        "evidence_references": irp.get("evidence_references"),
        "assembly_ms": irp.get("assembly_ms"),
        "routing": irp.get("routing"),
        "guardrails": irp.get("guardrails"),
    }
    # Optional PEB-01 soft publish — never fails the office workflow
    try:
        from platform_event_bus.publisher import soft_publish
        from platform_event_bus.schema import EVENT_COMPANY_RESEARCH_COMPLETED

        soft_publish(
            EVENT_COMPANY_RESEARCH_COMPLETED,
            producer="io-01",
            payload={
                "ticker": irp.get("ticker"),
                "package_type": irp.get("package_type"),
                "modules_invoked": irp.get("modules_invoked"),
                "assembly_ms": irp.get("assembly_ms"),
            },
        )
    except Exception:
        pass
    return pack


def query(
    *,
    ticker: str,
    question: str = "",
    package_type: str | None = None,
    series_map: dict[str, list[dict[str, Any]]] | None = None,
    documents: list[dict[str, Any]] | None = None,
    prebuilt: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """IO-01: route a natural-language investment question and assemble IRP."""
    return company(
        ticker,
        question=question,
        package_type=package_type,
        series_map=series_map,
        documents=documents,
        prebuilt=prebuilt,
    )


def as_office_response(
    pack: dict[str, Any],
    *,
    request: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Wrap a native IO pack in the shared OfficeResponse contract."""
    from office_sdk.adapters import wrap_io_response

    return wrap_io_response(pack, request=request)


def soft_slice_mission_control(ticker: str | None = None) -> dict[str, Any]:
    """Mission Control soft board for IO-01 orchestration metrics (additive)."""
    metrics = io_store.irp_metrics()
    base = {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": IO01_WORKSTREAM_ID,
        "product": IO01_PRODUCT,
        "version": IO01_VERSION,
        "orchestrates_only": True,
        "buy_sell": False,
        "panels": {
            "requests_served": metrics.get("requests_served"),
            "modules_invoked": metrics.get("modules_invoked_total"),
            "average_assembly_time": metrics.get("average_assembly_time_ms"),
            "evidence_reuse": metrics.get("evidence_reuse"),
            "coverage": metrics.get("coverage"),
            "confidence": metrics.get("confidence"),
        },
        "metrics": metrics,
    }
    if ticker:
        pack = company(ticker)
        irp = pack.get("irp") if isinstance(pack.get("irp"), dict) else {}
        base["ticker"] = (ticker or "").upper()
        base["last_package_type"] = irp.get("package_type")
        base["last_modules"] = irp.get("modules_invoked")
        base["last_mean_confidence"] = (irp.get("confidence") or {}).get("mean_confidence")
        base["panels"] = {
            **base["panels"],
            **io_store.irp_metrics().get("confidence", {}),
        }
        # refresh panels from updated metrics
        m2 = io_store.irp_metrics()
        base["panels"] = {
            "requests_served": m2.get("requests_served"),
            "modules_invoked": m2.get("modules_invoked_total"),
            "average_assembly_time": m2.get("average_assembly_time_ms"),
            "evidence_reuse": m2.get("evidence_reuse"),
            "coverage": m2.get("coverage"),
            "confidence": m2.get("confidence"),
        }
        base["metrics"] = m2
    return base


def quality_gates() -> dict[str, Any]:
    # Seed CMS signals so desk is non-empty
    try:
        from company_monitor import store as cms_store
        from company_monitor.significance import annotate

        cms_store.reset_for_tests()
        cms_store.put_snapshot(
            "HDFCBANK",
            {
                "ticker": "HDFCBANK",
                "metrics": {"revenue_growth": 0.11, "operating_margin": 0.20, "roe": 0.15, "debt": 100, "pe": 16, "historical_pe": 18},
                "leo_evidence_count": 1,
                "channels_seen": {"financial_statements": True},
            },
        )
        from company_monitor.pipeline import monitor_company

        monitor_company(
            "HDFCBANK",
            force_pipeline=False,
            layers={
                "cid": {
                    "ticker": "HDFCBANK",
                    "financials": {"revenue_growth": 0.18, "operating_margin": 0.17, "roe": 0.14, "debt": 120},
                    "valuation": {"pe": 22, "historical_pe": 18},
                },
                "leo_pkg": {"evidence_objects": [{"type": "earnings"}]},
            },
        )
        _ = annotate
    except Exception:
        pass

    desk = dashboard(ui_home={
        "hero": {
            "house_view": "Cautious constructive — selective.",
            "market_regime": "Cautious Constructive",
            "risk_level": "Medium",
            "research_published_today": 2,
        },
        "morning_intelligence": {
            "greeting_line": "Here's what the AGI Investment Office believes today.",
            "cards": [{"id": "house_view", "label": "Today's House View", "value": "Selective"}],
        },
        "calendar": [{"title": "RBI", "type": "macro"}],
    })
    criteria = {
        "desk_enabled": desk.get("enabled") is True,
        "not_empty": desk.get("empty_state") is False,
        "morning_brief_present": bool(desk.get("morning_executive_brief")),
        "attention_ranked": isinstance(desk.get("companies_requiring_attention"), list),
        "research_queue_present": len(desk.get("todays_research_queue") or []) >= 1,
        "knowledge_growth_present": bool(desk.get("knowledge_growth")),
        "coverage_present": bool(desk.get("coverage_dashboard")),
        "risk_centre_present": bool(desk.get("risk_centre")),
        "executive_copilot_present": bool((desk.get("executive_copilot") or {}).get("prompts")),
        "ioc_system_health": (desk.get("system_health") or {}).get("ioc_only") is True,
        "notifications_present": len(desk.get("notifications") or []) >= 1,
    }
    passed = all(criteria.values())
    return {
        "programme": PROGRAMME,
        "version": IO_VERSION,
        "passed": passed,
        "criteria": criteria,
        "message": "Investment Office quality gates passed" if passed else "Investment Office incomplete",
    }


def reset_for_tests() -> None:
    io_store.reset_for_tests()


# --- AGI V1.3 Institutional Morning Office (additive façades) ---


def morning_overview() -> dict[str, Any]:
    """Hot path: precomputed morning snapshot (ICF/IEP/CGL off the request)."""
    from investment_office.morning_desk import build_morning_overview

    return build_morning_overview(force=False, allow_live_rebuild=False)


def morning_office() -> dict[str, Any]:
    from investment_office.morning_desk import slice_overview

    return slice_overview("morning-office")


def daily_brief() -> dict[str, Any]:
    from investment_office.morning_desk import slice_overview

    return slice_overview("daily-brief")


def research_queue_v13() -> dict[str, Any]:
    from investment_office.morning_desk import slice_overview

    return slice_overview("research-queue")


def opportunities_v13() -> dict[str, Any]:
    from investment_office.morning_desk import slice_overview

    return slice_overview("opportunities")


def market_summary_v13() -> dict[str, Any]:
    from investment_office.morning_desk import slice_overview

    return slice_overview("market-summary")


def macro_v13() -> dict[str, Any]:
    from investment_office.morning_desk import slice_overview

    return slice_overview("macro")


def calendar_v13() -> dict[str, Any]:
    from investment_office.morning_desk import slice_overview

    return slice_overview("calendar")


def portfolio_monitor_v13() -> dict[str, Any]:
    from investment_office.morning_desk import slice_overview

    return slice_overview("portfolio-monitor")


def sector_monitor_v13() -> dict[str, Any]:
    from investment_office.morning_desk import slice_overview

    return slice_overview("sector-monitor")


def metrics_v13() -> dict[str, Any]:
    from investment_office.morning_desk import slice_overview

    return slice_overview("metrics")


def snapshot_status() -> dict[str, Any]:
    from investment_office.morning_snapshot import snapshot_meta

    return {"ok": True, **snapshot_meta()}


def system_health_v13() -> dict[str, Any]:
    """Live operational status — seconds freshness, no heavy scans."""
    from investment_office.morning_snapshot import live_system_health

    return live_system_health()


def refresh_morning_office(wait: bool = False) -> dict[str, Any]:
    from investment_office.morning_desk import refresh_morning_office as _refresh

    return _refresh(wait=wait)


def generate_morning_brief() -> dict[str, Any]:
    from investment_office.morning_desk import generate_morning_brief as _gen

    return _gen()


def soft_slice_morning_office() -> dict[str, Any]:
    """Mission Control / homepage soft board — snapshot only."""
    try:
        from investment_office.morning_snapshot import get_snapshot, snapshot_meta

        overview = get_snapshot() or morning_overview()
        top = (overview or {}).get("top_summary") or {}
        return {
            "status": "ok",
            "workstream_id": overview.get("workstream_id"),
            "product": overview.get("product"),
            "version": overview.get("version"),
            "admin_only": True,
            "buy_sell": False,
            "delivery": (overview or {}).get("delivery"),
            "snapshot": snapshot_meta(),
            "panels": {
                "market_mood": top.get("market_mood"),
                "global_risk": top.get("global_risk"),
                "research_queue": top.get("research_queue"),
                "critical_alerts": top.get("critical_alerts"),
                "companies_updated_overnight": top.get("companies_updated_overnight"),
                "institutional_coverage_complete": top.get("institutional_coverage_complete"),
            },
            "route": "/admin/investment-office",
            "complements": "Knowledge Operations",
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:200], "admin_only": True}
