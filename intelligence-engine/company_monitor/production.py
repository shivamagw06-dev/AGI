"""CMS production facade — soft adapters for Ask AGI / Research Writer / admin."""

from __future__ import annotations

from typing import Any

from company_monitor.flags import flag_ask_agi, flag_research_writer, flags_dict, is_enabled
from company_monitor.pipeline import monitor_company, monitor_universe
from company_monitor.schema import CMS_VERSION, DEFAULT_UNIVERSE, MONITOR_CHANNELS, PROGRAMME, PROGRAMME_SHORT
from company_monitor import store as cms_store
from company_monitor.summary import build_change_summary


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": CMS_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "not_an_engine": True,
        "not_a_recommendation_engine": True,
        "never_auto_changes_house_view": True,
        "channels": list(MONITOR_CHANNELS),
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "metrics": cms_store.metrics(),
    }


def dashboard() -> dict[str, Any]:
    m = cms_store.metrics()
    monitored = cms_store.monitored_tickers()
    changes = cms_store.list_changes(limit=25)
    alerts = [a for a in cms_store.list_alerts(40) if a.get("significance") in {"High", "Critical"}]
    reviews = cms_store.list_reviews(40)

    # Coverage / freshness from snapshots
    snaps = [cms_store.get_snapshot(t) for t in monitored]
    snaps = [s for s in snaps if s]
    with_fin = sum(1 for s in snaps if (s.get("channels_seen") or {}).get("financial_statements"))
    coverage = int(round(100 * with_fin / max(1, len(snaps)))) if snaps else 0
    freshness = []
    for s in snaps[:12]:
        freshness.append(
            {
                "ticker": s.get("ticker"),
                "captured_at": s.get("captured_at"),
                "knowledge_age_hint": s.get("knowledge_age_hint"),
                "leo_evidence_count": s.get("leo_evidence_count"),
            }
        )

    return {
        "programme": PROGRAMME,
        "version": CMS_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "enabled": is_enabled(),
        "flags": flags_dict(),
        "metrics": m,
        "companies_monitored": monitored,
        "default_universe": list(DEFAULT_UNIVERSE),
        "latest_changes": changes,
        "companies_needing_review": reviews,
        "critical_alerts": [a for a in alerts if a.get("significance") == "Critical"],
        "high_alerts": [a for a in alerts if a.get("significance") == "High"],
        "coverage": {"financial_channel_pct": coverage, "monitored": len(monitored)},
        "freshness": freshness,
        "knowledge_age": freshness,
    }


def quality_gates() -> dict[str, Any]:
    # Seed two snapshots for HDFC to prove detection
    reset_for_tests()
    t = "HDFCBANK"
    cms_store.put_snapshot(
        t,
        {
            "ticker": t,
            "captured_at": "2026-01-01T00:00:00+00:00",
            "metrics": {
                "revenue_growth": 0.11,
                "operating_margin": 0.20,
                "roe": 0.15,
                "debt": 100.0,
                "cash_flow": 50.0,
                "pe": 16.0,
                "historical_pe": 18.0,
            },
            "leo_evidence_count": 2,
            "house_view_label": "Hold",
            "channels_seen": {"financial_statements": True},
        },
    )
    report = monitor_company(
        t,
        force_pipeline=False,
        layers={
            "cid": {
                "ticker": t,
                "identity": {"company_name": "HDFC Bank", "sector_id": "banks"},
                "financials": {
                    "revenue_growth": 0.18,
                    "operating_margin": 0.223,
                    "roe": 0.17,
                    "debt": 88.0,
                    "fcf": 55.0,
                },
                "valuation": {"pe": 20.0, "historical_pe": 18.0},
            },
            "leo_pkg": {"ticker": t, "evidence_objects": [{"type": "earnings"}, {"type": "news"}, {"type": "news"}]},
            "financial": {},
            "valuation": {"current_pe": 20.0, "historical_pe": 18.0},
            "company_analysis": {"business_quality": {"business_quality_score": 70}},
            "house_view": {"stance": "Hold"},
            "predictions": [],
        },
    )
    summary = report.get("what_changed") or {}
    criteria = {
        "monitors_company": report.get("ok") is True,
        "detects_changes": (summary.get("change_count") or 0) >= 2,
        "significance_assigned": all(c.get("significance") for c in report.get("changes") or []),
        "what_changed_summary": bool(summary.get("rows")),
        "never_auto_changes_house_view": report.get("auto_house_view_changed") is False,
        "house_view_review_optional": True,  # may or may not trigger depending on significance
        "pipeline_stamps_present": bool((report.get("pipeline") or {}).get("knowledge_timeline")),
    }
    passed = all(criteria.values())
    return {
        "programme": PROGRAMME,
        "version": CMS_VERSION,
        "passed": passed,
        "criteria": criteria,
        "sample_ticker": t,
        "sample_change_count": summary.get("change_count"),
        "message": "CMS quality gates passed" if passed else "CMS incomplete",
    }


def package_for_ask_agi(
    query: str = "",
    *,
    ticker: str | None = None,
    run_monitor: bool = True,
    layers: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ask AGI soft entry — include everything that changed since prior snapshot/quarter."""
    if not flag_ask_agi():
        return {"enabled": False, "bypassed": True}

    t = (ticker or "").upper() or None
    report = None
    if t and run_monitor:
        report = monitor_company(t, query=query, layers=layers)
    elif t:
        # Read-only package from store
        snap = cms_store.get_snapshot(t)
        prev = cms_store.get_previous(t)
        changes = cms_store.list_changes(t, limit=20)
        summary = build_change_summary(changes, current=snap, previous=prev)
        report = {
            "enabled": True,
            "ticker": t,
            "what_changed": summary,
            "changes": changes,
            "house_view_review": next(
                (r for r in cms_store.list_reviews(50) if r.get("ticker") == t), None
            ),
            "snapshot": snap,
            "auto_house_view_changed": False,
        }
    else:
        return {"enabled": True, "ticker": None, "reason": "no_ticker", "what_changed": {"rows": [], "narrative": []}}

    summary = (report or {}).get("what_changed") or {}
    hints = []
    for line in (summary.get("narrative") or [])[:5]:
        hints.append(str(line)[:240])
    if (report or {}).get("house_view_review"):
        hints.append("Material changes — Suggested House View Review (not auto-applied).")
    if not hints:
        hints.append("No material monitored changes since prior snapshot.")

    return {
        "enabled": True,
        "programme": PROGRAMME,
        "version": CMS_VERSION,
        "ticker": (report or {}).get("ticker") or t,
        "what_changed": summary,
        "changes": (report or {}).get("changes") or [],
        "house_view_review": (report or {}).get("house_view_review"),
        "since_previous_quarter_or_snapshot": summary.get("since"),
        "ask_agi_hints": hints,
        "answer_policy": "include_what_changed_since_prior_period",
        "never_auto_changes_house_view": True,
        "pipeline": (report or {}).get("pipeline"),
    }


def research_writer_slice(query: str = "", ticker: str | None = None) -> dict[str, Any]:
    """Preload What Changed + timeline for Research Writer."""
    if not flag_research_writer():
        return {"enabled": False, "bypassed": True}

    pkg = package_for_ask_agi(query, ticker=ticker, run_monitor=bool(ticker))
    changes = pkg.get("changes") or []
    return {
        "enabled": True,
        "programme": PROGRAMME,
        "ticker": pkg.get("ticker"),
        "what_changed": pkg.get("what_changed"),
        "historical_timeline": [
            {
                "at": c.get("detected_at"),
                "type": c.get("change_type"),
                "detail": c.get("detail"),
                "significance": c.get("significance"),
            }
            for c in changes[:20]
        ],
        "financial_changes": [c for c in changes if c.get("metric") in {"revenue_growth", "operating_margin", "roe", "debt", "cash_flow"}],
        "management_changes": [c for c in changes if "management" in str(c.get("change_type") or "")],
        "valuation_changes": [c for c in changes if "valuation" in str(c.get("change_type") or "") or c.get("metric") in {"pe", "pe_vs_history", "pb"}],
        "answer_policy": "preload_what_changed_for_research",
    }


def analyse(ticker: str, query: str = "") -> dict[str, Any]:
    return monitor_company(ticker, query=query, force_pipeline=True)


def run_universe(limit: int | None = None) -> dict[str, Any]:
    return monitor_universe(limit=limit)


def reset_for_tests() -> None:
    cms_store.reset_for_tests()
