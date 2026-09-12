"""ICF-01 production façades."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from institutional_coverage_factory.config import as_yaml_dict, load_config
from institutional_coverage_factory.flags import is_icf_enabled
from institutional_coverage_factory.schema import (
    EVIDENCE_CLASSES,
    ICF_PRODUCT,
    ICF_SPEC,
    ICF_VERSION,
    ICF_WORKSTREAM_ID,
    ICC_EXIT_CRITERIA,
    MISSION,
    PIPELINE,
    PRIORITY_TIERS,
)


def health() -> Dict[str, Any]:
    cfg = load_config()
    return {
        "ok": True,
        "enabled": is_icf_enabled() and bool(cfg.get("enabled")),
        "workstream_id": ICF_WORKSTREAM_ID,
        "product": ICF_PRODUCT,
        "version": ICF_VERSION,
        "spec": ICF_SPEC,
    }


def get_icf_status() -> Dict[str, Any]:
    cfg = load_config()
    return {
        "ok": True,
        "workstream_id": ICF_WORKSTREAM_ID,
        "product": ICF_PRODUCT,
        "version": ICF_VERSION,
        "spec": ICF_SPEC,
        "mission": MISSION,
        "pipeline": list(PIPELINE),
        "priority_tiers": list(PRIORITY_TIERS),
        "evidence_classes": {
            k: {"required": v["required"], "weight": v["weight"], "collector": v["collector"]}
            for k, v in EVIDENCE_CLASSES.items()
        },
        "icc_exit_criteria": list(ICC_EXIT_CRITERIA),
        "config": cfg,
        "config_yaml": as_yaml_dict(),
        "north_star": "Companies entering Institutional Coverage Complete per day",
        "rule": "Do not hard-code crawl throughput — measure ICC entries; scale via config.",
    }


def coverage_score_for(ticker: str) -> Dict[str, Any]:
    from institutional_coverage_factory.scorer.score import coverage_score_for as _score

    return _score(ticker)


def icc_status_for(ticker: str) -> Dict[str, Any]:
    from institutional_coverage_factory.validator.icc import icc_status_for as _icc

    return _icc(ticker)


def plan_coverage(*, limit: Optional[int] = None, scope: str = "TOP20") -> Dict[str, Any]:
    from institutional_coverage_factory.planner.plan import plan_coverage as _plan

    return _plan(limit=limit, scope=scope)


def plan_and_dispatch(
    *,
    limit: Optional[int] = None,
    scope: str = "TOP20",
    dispatch: Optional[bool] = None,
) -> Dict[str, Any]:
    from institutional_coverage_factory.planner.plan import plan_and_dispatch as _pad

    return _pad(limit=limit, scope=scope, dispatch=dispatch)


def run_coverage_tick(
    *,
    scope: str = "TOP20",
    limit: Optional[int] = None,
    dispatch: Optional[bool] = None,
) -> Dict[str, Any]:
    from institutional_coverage_factory.scheduler.loop import run_coverage_tick as _tick

    return _tick(scope=scope, limit=limit, dispatch=dispatch)


def coverage_dashboard(*, scope: str = "TOP20", sample_limit: Optional[int] = None) -> Dict[str, Any]:
    from institutional_coverage_factory.dashboards.coverage import coverage_dashboard as _dash

    return _dash(scope=scope, sample_limit=sample_limit)


def dispatch_company(
    ticker: str,
    *,
    missing_classes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    from institutional_coverage_factory.collectors.dispatch import dispatch_collectors

    return dispatch_collectors(ticker, missing_classes=missing_classes, integrate=True)


def scheduler_status() -> Dict[str, Any]:
    from institutional_coverage_factory.scheduler.loop import scheduler_status as _st

    return _st()


def soft_slice_mission_control() -> Dict[str, Any]:
    """Cheap Mission Control Coverage Dashboard slice (Top-20 soft)."""
    try:
        from institutional_coverage_factory.scheduler.loop import scheduler_status
        from institutional_coverage_factory.universe import top20_tickers

        cfg = load_config()
        sch = scheduler_status()
        # Lightweight: do not score all companies on every MC poll
        return {
            "status": "ok",
            "board": "Institutional Coverage",
            "workstream_id": ICF_WORKSTREAM_ID,
            "version": ICF_VERSION,
            "product": ICF_PRODUCT,
            "mission": MISSION,
            "pipeline": list(PIPELINE),
            "top20_size": len(top20_tickers()),
            "max_companies_per_day": cfg["max_companies_per_day"],
            "icc_entered_today": sch.get("icc_entered_today"),
            "daily_icc_target": cfg["max_companies_per_day"],
            "remaining_capacity_today": sch.get("remaining_capacity_today"),
            "tick_interval_minutes": cfg["tick_interval_minutes"],
            "priority": cfg["priority"],
            "coverage_threshold": cfg["coverage_threshold"],
            "institutional_coverage_threshold": cfg["institutional_coverage_threshold"],
            "north_star": "Companies entering ICC / day",
            "note": "Call /api/intelligence/icf/dashboard for live Top-20 coverage metrics",
        }
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:240]}
