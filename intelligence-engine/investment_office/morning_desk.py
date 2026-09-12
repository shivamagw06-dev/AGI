"""V1.3 Morning Desk aggregate — soft-wires IO desk + IOL + CGL/KIL/ICF knowledge signals."""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional

from investment_office.v13_schema import (
    IO_V13_PLATFORM,
    IO_V13_PRODUCT,
    IO_V13_SPEC,
    IO_V13_VERSION,
    IO_V13_WORKSTREAM_ID,
    MISSION,
    POLICY,
    RESEARCH_QUEUE_STAGES,
    ROLE,
    SECTORS,
)

# Soft-aggregate can be slow on cold engine; keep a short TTL cache for the desk UI.
_OVERVIEW_CACHE_LOCK = Lock()
_OVERVIEW_CACHE: Dict[str, Any] = {"at": 0.0, "payload": None}
_OVERVIEW_CACHE_TTL_S = 90.0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _soft(fn, default=None):
    try:
        return fn()
    except Exception as exc:
        if default is not None:
            return default
        return {"_ok": False, "error": str(exc)[:200]}


def _soft_timeout(fn, default=None, timeout_s: float = 8.0):
    """Run soft dependency with a hard wall-clock bound (cold engines / heavy IOL).

    Important: on timeout we must not block in ThreadPoolExecutor.__exit__
    (default shutdown waits for the hung worker).
    """
    pool = ThreadPoolExecutor(max_workers=1)
    try:
        fut = pool.submit(fn)
        return fut.result(timeout=timeout_s)
    except FuturesTimeout:
        if default is not None:
            return default
        return {"_ok": False, "error": f"soft_timeout_{timeout_s}s"}
    except Exception as exc:
        if default is not None:
            return default
        return {"_ok": False, "error": str(exc)[:200]}
    finally:
        pool.shutdown(wait=False, cancel_futures=True)


def _weekday_date(dt: Optional[datetime] = None) -> Dict[str, str]:
    d = dt or datetime.now(timezone.utc)
    # Display in a friendly institutional form (UTC date; UI can localize)
    return {
        "weekday": d.strftime("%A"),
        "day": d.strftime("%d"),
        "month": d.strftime("%B"),
        "year": d.strftime("%Y"),
        "iso_date": d.date().isoformat(),
        "display": d.strftime("%A · %d %B %Y"),
    }


def _io_desk() -> Dict[str, Any]:
    from investment_office.production import cached_desk, dashboard

    cached = cached_desk()
    if isinstance(cached, dict) and cached.get("enabled"):
        return cached
    # Bound desk rebuild — overview must stay interactive on cold start.
    desk = _soft_timeout(lambda: dashboard() or {}, default={}, timeout_s=12.0)
    return desk if isinstance(desk, dict) else {}


def _iol_morning() -> Dict[str, Any]:
    """Soft Investment Operations morning — may be slower; never hard-fail."""

    def _run():
        from investment_operations.production import morning_office

        return morning_office(include_soft_reasoning=False) or {}

    return _soft_timeout(_run, default={"_ok": False, "error": "iol_unavailable"}, timeout_s=10.0)


def _cgl() -> Dict[str, Any]:
    return _soft_timeout(
        lambda: __import__(
            "continuous_gather_learn.production", fromlist=["dashboard"]
        ).dashboard(),
        default={},
        timeout_s=8.0,
    )


def _knowledge_kpis() -> Dict[str, Any]:
    def _run() -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        try:
            from institutional_coverage_factory.production import coverage_dashboard, scheduler_status

            dash = coverage_dashboard(scope="TOP20")
            m = dash.get("metrics") or {}
            out["icc_complete"] = m.get("icc_complete")
            out["scoped_companies"] = m.get("scoped_companies")
            out["icc_entered_today"] = (scheduler_status() or {}).get("icc_entered_today")
        except Exception:
            pass
        try:
            from institutional_evidence.production import soft_slice_knowledge_health

            kh = soft_slice_knowledge_health()
            out["knowledge_health"] = kh
        except Exception:
            pass
        try:
            from knowledge_operations.production import get_missing_inbox

            inbox = get_missing_inbox(scope="TOP20", limit=10)
            out["missing_inbox_count"] = inbox.get("count")
            out["critical_gaps"] = (inbox.get("by_priority") or {}).get("Critical")
        except Exception:
            pass
        return out

    result = _soft_timeout(_run, default={}, timeout_s=10.0)
    return result if isinstance(result, dict) else {}


def _overnight_timeline(cgl: Dict[str, Any], iol: Dict[str, Any], desk: Dict[str, Any]) -> List[Dict[str, Any]]:
    events: List[Dict[str, Any]] = []
    # From IOL morning overnight changes
    mo = iol.get("morning_office") or {}
    for row in (mo.get("overnight_changes") or [])[:20]:
        events.append(
            {
                "time": None,
                "timestamp": mo.get("as_of"),
                "ticker": row.get("ticker") or row.get("entity"),
                "kind": "Company",
                "title": row.get("delta_status") or "Change",
                "detail": row.get("summary"),
                "status": "Detected",
                "research_invalidated": row.get("delta_status") not in {None, "UNCHANGED"},
            }
        )
    # CMS / IO desk changes
    for ch in (desk.get("overnight_changes") or desk.get("material_changes") or [])[:15]:
        if not isinstance(ch, dict):
            continue
        events.append(
            {
                "time": (str(ch.get("at") or ch.get("timestamp") or ""))[11:16] or None,
                "timestamp": ch.get("at") or ch.get("timestamp"),
                "ticker": ch.get("ticker"),
                "kind": ch.get("type") or "Change",
                "title": ch.get("title") or ch.get("field") or "Update",
                "detail": ch.get("summary") or ch.get("message"),
                "status": ch.get("status") or "Updated",
            }
        )
    # CGL latest run as macro/knowledge signal
    latest = cgl.get("latest_run") if isinstance(cgl, dict) else None
    if isinstance(latest, dict) and latest.get("run_id"):
        events.append(
            {
                "time": (str(latest.get("generated_at") or ""))[11:16] or None,
                "timestamp": latest.get("generated_at"),
                "ticker": None,
                "kind": "Knowledge",
                "title": f"CGL {latest.get('slot') or 'cycle'}",
                "detail": f"extracts={(latest.get('volumes') or {}).get('knowledge_extracts')} collectors_ok={(latest.get('volumes') or {}).get('collectors_ok')}",
                "status": "Collected" if latest.get("ok") else "Failed",
                "run_id": latest.get("run_id"),
            }
        )
    events.sort(key=lambda e: e.get("timestamp") or "", reverse=True)
    return events[:30]


def _priorities(desk: Dict[str, Any], iol: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    mo = iol.get("morning_office") or {}
    for p in (mo.get("analyst_priorities") or [])[:15]:
        rows.append(
            {
                "ticker": p.get("ticker") or p.get("entity"),
                "company": p.get("entity") or p.get("ticker"),
                "priority": p.get("priority") or "High",
                "reason": p.get("reason") or p.get("why_now") or "Requires attention",
                "expected_impact": "Research Refresh" if "refresh" in str(p.get("reason") or "").lower() else "Monitor",
                "eta_minutes": 8 if str(p.get("priority")).lower() == "critical" else 15,
                "owner": "AI",
            }
        )
    for a in (desk.get("companies_requiring_attention") or [])[:15]:
        t = a.get("ticker")
        if any(r.get("ticker") == t for r in rows):
            continue
        rows.append(
            {
                "ticker": t,
                "company": a.get("company") or t,
                "priority": a.get("priority") or "Medium",
                "reason": ", ".join(a.get("reasons") or []) or a.get("reason") or "Attention",
                "expected_impact": "Monitor",
                "eta_minutes": 20,
                "owner": "Analyst",
            }
        )
    order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    rows.sort(key=lambda r: (order.get(str(r.get("priority")), 9), r.get("ticker") or ""))
    return rows[:20]


def _opportunities(desk: Dict[str, Any], iol: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Monitoring opportunities — NOT recommendations."""
    out: List[Dict[str, Any]] = []
    mo = iol.get("morning_office") or {}
    for o in (mo.get("top_opportunities") or [])[:12]:
        out.append(
            {
                "ticker": o.get("ticker") or o.get("display") or o.get("entity"),
                "reason": o.get("why_now") or o.get("reason") or "Requires monitoring",
                "confidence": o.get("opportunity_score") or o.get("score"),
                "affected_research": o.get("research_priority"),
                "note": "Monitoring only — not a recommendation",
            }
        )
    for a in (desk.get("companies_requiring_attention") or [])[:8]:
        t = a.get("ticker")
        if any(x.get("ticker") == t for x in out):
            continue
        out.append(
            {
                "ticker": t,
                "reason": ", ".join(a.get("reasons") or []) or "New evidence / change",
                "confidence": None,
                "affected_research": a.get("priority"),
                "note": "Monitoring only — not a recommendation",
            }
        )
    return out[:15]


def _research_queue(desk: Dict[str, Any], iol: Dict[str, Any]) -> Dict[str, Any]:
    items = list(desk.get("todays_research_queue") or [])
    mo_q = (iol.get("morning_office") or {}).get("research_queue") or {}
    if isinstance(mo_q, dict) and mo_q.get("items"):
        items = list(mo_q.get("items") or items)
    # Also from IOL research_queue endpoint shape inside morning
    stages = {s: 0 for s in RESEARCH_QUEUE_STAGES}
    normalized = []
    for it in items[:40]:
        status = str(it.get("status") or it.get("stage") or "Waiting Review")
        # Map soft statuses
        key = status
        if "valid" in status.lower():
            key = "Waiting Validation"
        elif "publish" in status.lower():
            key = "Waiting Publication"
        elif "refresh" in status.lower() or "stale" in status.lower():
            key = "Waiting Refresh"
        elif "evidence" in status.lower():
            key = "Waiting Evidence"
        elif "claim" in status.lower():
            key = "Waiting Claim Safety"
        elif "review" in status.lower() or key not in stages:
            key = "Waiting Review"
        stages[key] = stages.get(key, 0) + 1
        normalized.append(
            {
                "ticker": it.get("ticker") or it.get("entity"),
                "title": it.get("title") or it.get("task") or it.get("reason") or "Research item",
                "status": key,
                "priority": it.get("priority") or "Medium",
                "reason": it.get("reason") or it.get("why") or it.get("summary"),
                "eta_minutes": it.get("eta_minutes") or 15,
            }
        )
    return {"count": len(normalized), "stages": stages, "items": normalized}


def _executive_brief(
    *,
    cgl: Dict[str, Any],
    desk: Dict[str, Any],
    priorities: List[Dict[str, Any]],
    overnight: List[Dict[str, Any]],
    knowledge: Dict[str, Any],
    queue: Dict[str, Any],
) -> Dict[str, Any]:
    brief = desk.get("morning_executive_brief") or {}
    companies_updated = (
        cgl.get("companies_processed_today")
        if isinstance(cgl, dict)
        else None
    ) or len(overnight) or brief.get("companies_updated")
    critical = sum(1 for p in priorities if str(p.get("priority")).lower() == "critical")
    workload = round(max(0.5, (queue.get("count") or 0) * 0.18 + critical * 0.25), 1)
    lines = []
    if isinstance(cgl, dict) and cgl.get("latest_run", {}).get("ok"):
        lines.append(
            f"Overnight knowledge cycle ({(cgl.get('latest_run') or {}).get('slot') or 'CGL'}) completed successfully."
        )
    if companies_updated:
        lines.append(f"{companies_updated} companies were touched by overnight gathering or desk monitoring.")
    if knowledge.get("missing_inbox_count"):
        lines.append(
            f"{knowledge.get('missing_inbox_count')} high-impact knowledge gaps remain in the Missing Knowledge Inbox."
        )
    if critical:
        lines.append(f"{critical} critical analyst priorities require attention before the open.")
    if queue.get("count"):
        lines.append(f"Research queue has {queue.get('count')} items awaiting action.")
    if not lines:
        lines.append("Desk is quiet — monitor markets, macro calendar, and coverage freshness.")
    lines.append(f"Estimated analyst workload ≈ {workload} hours.")
    narrative = " ".join(lines)
    return {
        "title": "Morning Executive Brief",
        "generated_at": _now(),
        "market_regime": brief.get("market_regime") or brief.get("regime") or "Neutral",
        "risk_level": brief.get("risk_level") or brief.get("global_risk") or "Moderate",
        "narrative": narrative,
        "bullets": lines,
        "estimated_workload_hours": workload,
        "source": "soft_aggregate",
    }


def _ai_summary(exec_brief: Dict[str, Any], priorities: List[Dict[str, Any]], knowledge: Dict[str, Any]) -> Dict[str, Any]:
    top = ", ".join(
        f"{p.get('ticker')} ({p.get('reason')})"
        for p in priorities[:3]
        if p.get("ticker")
    ) or "no critical company alerts"
    text = (
        f"Good morning. {exec_brief.get('narrative')} "
        f"Highest-impact names to monitor: {top}. "
        f"Institutional Coverage Complete (scoped): {knowledge.get('icc_complete', '—')}. "
        "This briefing issues no buy or sell recommendations."
    )
    return {
        "title": "Daily AI Summary",
        "text": text,
        "market_summary": exec_brief.get("narrative"),
        "top_risks": [p for p in priorities if str(p.get("priority")).lower() in {"critical", "high"}][:5],
        "top_opportunities_to_monitor": priorities[:5],
        "research_priorities": priorities[:8],
        "knowledge_improvements_overnight": {
            "icc_complete": knowledge.get("icc_complete"),
            "missing_inbox_count": knowledge.get("missing_inbox_count"),
            "critical_gaps": knowledge.get("critical_gaps"),
        },
        "suggested_analyst_workflow": [
            "Clear Critical priorities",
            "Review overnight evidence invalidations",
            "Check macro calendar before open",
            "Refresh stale research in queue",
            "Open Knowledge Operations for missing evidence uploads",
        ],
        "estimated_workload_hours": exec_brief.get("estimated_workload_hours"),
        "issues_recommendations": False,
    }


def _market_summary(desk: Dict[str, Any], iol: Dict[str, Any]) -> Dict[str, Any]:
    mo = iol.get("morning_office") or {}
    ms = mo.get("market_summary") or desk.get("market_dashboard") or {}
    # Soft live board from IO desk if present
    return {
        "india": ms.get("india") or desk.get("india_markets") or {},
        "global": ms.get("global") or desk.get("global_markets") or {},
        "commodities": ms.get("commodities") or {},
        "currencies": ms.get("currencies") or {},
        "desk": ms.get("desk") if isinstance(ms.get("desk"), dict) else ms,
        "note": "Soft market snapshot — monitoring only",
        "auto_updates": True,
    }


def _macro(desk: Dict[str, Any], iol: Dict[str, Any]) -> Dict[str, Any]:
    mo = iol.get("morning_office") or {}
    events = list(mo.get("macro_updates") or desk.get("macro_events") or [])[:20]
    return {
        "todays_events": events,
        "calendar": desk.get("economic_calendar") or [],
        "sources": ["RBI", "Government", "Inflation", "GDP", "Employment", "Fed", "ECB", "BoJ"],
    }


def _calendar(desk: Dict[str, Any], iol: Dict[str, Any]) -> Dict[str, Any]:
    mo = iol.get("morning_office") or {}
    return {
        "earnings_today": mo.get("earnings_today") or desk.get("earnings_today") or [],
        "upcoming_earnings": desk.get("upcoming_earnings") or [],
        "corporate_actions": mo.get("catalysts") or desk.get("corporate_actions") or [],
        "agms": desk.get("agms") or [],
        "investor_days": desk.get("investor_days") or [],
        "dividends": desk.get("dividends") or [],
    }


def _portfolio(desk: Dict[str, Any], iol: Dict[str, Any]) -> Dict[str, Any]:
    mo = iol.get("morning_office") or {}
    return {
        "watchlists": desk.get("watchlists") or [],
        "companies_requiring_review": mo.get("portfolio_alerts")
        or desk.get("companies_requiring_attention")
        or [],
        "stale_research": desk.get("stale_research") or [],
        "large_moves": desk.get("large_price_moves") or [],
        "note": "Portfolio monitoring only — no recommendations",
        "issues_recommendations": False,
    }


def _sectors(desk: Dict[str, Any], iol: Dict[str, Any]) -> List[Dict[str, Any]]:
    mo = iol.get("morning_office") or {}
    rotation = mo.get("sector_rotation") or desk.get("sector_rotation") or []
    if rotation:
        return list(rotation)[:12]
    return [
        {
            "sector": s,
            "performance": None,
            "major_news": None,
            "research_updates": None,
            "coverage": None,
            "companies_updated": None,
        }
        for s in SECTORS
    ]


def _metrics(desk: Dict[str, Any], knowledge: Dict[str, Any], queue: Dict[str, Any], cgl: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "reports_published": desk.get("reports_published"),
        "reports_refreshed": desk.get("reports_refreshed"),
        "reports_waiting": queue.get("count"),
        "research_ready": knowledge.get("research_ready")
        or (desk.get("coverage_dashboard") or {}).get("research_ready"),
        "claim_safe": knowledge.get("claim_safe"),
        "avg_knowledge_confidence": knowledge.get("knowledge_confidence")
        or ((knowledge.get("knowledge_health") or {}).get("cgl") or {}).get("hard_coverage_pct"),
        "avg_institutional_coverage": knowledge.get("icc_complete"),
        "research_latency": (cgl.get("latest_run") or {}).get("latency_ms") if isinstance(cgl, dict) else None,
        "collector_success_pct": cgl.get("collector_success_rate") if isinstance(cgl, dict) else None,
    }


def build_morning_overview(
    *,
    force: bool = False,
    persist_snapshot: bool = True,
    allow_live_rebuild: bool = False,
) -> Dict[str, Any]:
    """Morning Office aggregate.

    Hot path (force=False): return durable/warm precomputed snapshot only.
    Cold first-boot without a snapshot: optional soft live rebuild (allow_live_rebuild)
    or a lightweight building placeholder — never block the UI on ICF/IEP/CGL.
    """
    if not force:
        try:
            from investment_office.morning_snapshot import get_snapshot

            snap = get_snapshot()
            if isinstance(snap, dict) and snap.get("ok"):
                out = deepcopy(snap)
                out["cache"] = {
                    "hit": True,
                    "source": "morning_snapshot",
                    "ttl_s": _OVERVIEW_CACHE_TTL_S,
                }
                out["delivery"] = out.get("delivery") or {
                    "mode": "snapshot",
                    "class": "morning_brief",
                }
                return out
        except Exception:
            pass
        with _OVERVIEW_CACHE_LOCK:
            payload = _OVERVIEW_CACHE.get("payload")
            at = float(_OVERVIEW_CACHE.get("at") or 0.0)
            if isinstance(payload, dict) and (time.time() - at) < _OVERVIEW_CACHE_TTL_S:
                cached = deepcopy(payload)
                cached["cache"] = {
                    "hit": True,
                    "age_s": round(time.time() - at, 2),
                    "ttl_s": _OVERVIEW_CACHE_TTL_S,
                    "source": "process_ttl",
                }
                return cached
        if not allow_live_rebuild:
            # Kick an async rebuild and return a fast placeholder for first paint.
            # Skip auto-enqueue under pytest to keep unit tests deterministic/fast.
            if not os.getenv("PYTEST_CURRENT_TEST") and os.getenv("IO_AUTO_SNAPSHOT", "1") != "0":
                try:
                    from investment_office.morning_snapshot import enqueue_refresh

                    enqueue_refresh(trigger="overview_miss", wait=False)
                except Exception:
                    pass
            date_info = _weekday_date()
            return {
                "ok": True,
                "enabled": True,
                "admin_only": True,
                "building": True,
                "workstream_id": IO_V13_WORKSTREAM_ID,
                "product": IO_V13_PRODUCT,
                "platform": IO_V13_PLATFORM,
                "version": IO_V13_VERSION,
                "spec": IO_V13_SPEC,
                "mission": MISSION,
                "role": ROLE,
                "policy": POLICY,
                "generated_at": _now(),
                "header": {
                    "greeting": "Good Morning",
                    "date": date_info,
                    "title": "Investment Office",
                    "subtitle": "Institutional Daily Briefing",
                    "current_time": _now(),
                    "market_countdown": None,
                    "next_event": None,
                    "research_queue_count": 0,
                },
                "top_summary": {
                    "market_mood": "—",
                    "global_risk": "—",
                    "research_queue": 0,
                    "companies_updated_overnight": 0,
                    "reports_refreshed": 0,
                    "critical_alerts": 0,
                    "macro_events_today": 0,
                    "earnings_today": 0,
                    "research_ready": None,
                    "institutional_coverage_complete": None,
                },
                "executive_brief": {
                    "title": "Morning Executive Brief",
                    "narrative": "Preparing institutional morning snapshot — overnight pipeline may still be warming.",
                    "bullets": [
                        "Snapshot rebuild queued.",
                        "Heavy ICF/IEP/CGL scans run off the request path.",
                    ],
                    "estimated_workload_hours": None,
                },
                "priorities": [],
                "overnight_activity": [],
                "research_queue": {"count": 0, "stages": {s: 0 for s in RESEARCH_QUEUE_STAGES}, "items": []},
                "opportunities": [],
                "market_summary": {},
                "macro": {"todays_events": [], "sources": []},
                "calendar": {"earnings_today": []},
                "portfolio_monitor": {"issues_recommendations": False},
                "sector_monitor": [],
                "metrics": {},
                "analyst_workspace": {"assigned_companies": [], "pending_reviews": []},
                "investment_calendar": {"today": [], "this_week": [], "macro": []},
                "ai_summary": {
                    "text": "Morning snapshot is building. Refresh in a moment.",
                    "issues_recommendations": False,
                },
                "actions": [
                    "refresh_morning_office",
                    "open_knowledge_operations",
                ],
                "links": {
                    "knowledge_operations": "/admin/knowledge-operations",
                    "research_queue": "/admin/investment-office#research-queue",
                    "macro": "/macro-intelligence",
                    "portfolio": "/portfolio",
                },
                "delivery": {"mode": "building_placeholder", "class": "morning_brief"},
                "cache": {"hit": False, "source": "placeholder"},
            }

    desk = _soft(_io_desk, default={})
    if not isinstance(desk, dict):
        desk = {}
    # Parallelize the three slow soft deps (builder / force path only).
    # Do not wait on hung workers at shutdown — same contract as _soft_timeout.
    pool = ThreadPoolExecutor(max_workers=3)
    try:
        fut_iol = pool.submit(_iol_morning)
        fut_cgl = pool.submit(_cgl)
        fut_knowledge = pool.submit(_knowledge_kpis)
        iol = fut_iol.result()
        cgl = fut_cgl.result()
        knowledge = fut_knowledge.result()
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
    if not isinstance(iol, dict):
        iol = {}
    if not isinstance(cgl, dict):
        cgl = {}
    if not isinstance(knowledge, dict):
        knowledge = {}
    overnight = _overnight_timeline(cgl, iol, desk)
    priorities = _priorities(desk, iol)
    opportunities = _opportunities(desk, iol)
    queue = _research_queue(desk, iol)
    exec_brief = _executive_brief(
        cgl=cgl,
        desk=desk,
        priorities=priorities,
        overnight=overnight,
        knowledge=knowledge,
        queue=queue,
    )
    ai = _ai_summary(exec_brief, priorities, knowledge)
    date_info = _weekday_date()
    macro = _macro(desk, iol)
    calendar = _calendar(desk, iol)
    metrics = _metrics(desk, knowledge, queue, cgl)
    market = _market_summary(desk, iol)
    portfolio = _portfolio(desk, iol)
    sectors = _sectors(desk, iol)

    critical_alerts = sum(
        1
        for a in (desk.get("notifications") or desk.get("alerts") or [])
        if str((a or {}).get("severity") or (a or {}).get("priority") or "").lower()
        in {"critical", "high"}
    )
    if not critical_alerts:
        critical_alerts = sum(1 for p in priorities if str(p.get("priority")).lower() == "critical")

    todays_events = list(macro.get("todays_events") or [])
    top = {
        "market_mood": exec_brief.get("market_regime") or "Neutral",
        "global_risk": exec_brief.get("risk_level") or "Moderate",
        "research_queue": queue.get("count") or 0,
        "companies_updated_overnight": cgl.get("companies_processed_today")
        or len(overnight)
        or 0,
        "reports_refreshed": (desk.get("knowledge_growth") or {}).get("reports_refreshed")
        or len([e for e in overnight if e.get("research_invalidated")]),
        "critical_alerts": critical_alerts,
        "macro_events_today": len(todays_events),
        "earnings_today": len(calendar.get("earnings_today") or []),
        "research_ready": metrics.get("research_ready"),
        "institutional_coverage_complete": knowledge.get("icc_complete"),
    }

    out = {
        "ok": True,
        "enabled": True,
        "admin_only": True,
        "workstream_id": IO_V13_WORKSTREAM_ID,
        "product": IO_V13_PRODUCT,
        "platform": IO_V13_PLATFORM,
        "version": IO_V13_VERSION,
        "spec": IO_V13_SPEC,
        "mission": MISSION,
        "role": ROLE,
        "policy": POLICY,
        "generated_at": _now(),
        "header": {
            "greeting": "Good Morning",
            "date": date_info,
            "title": "Investment Office",
            "subtitle": "Institutional Daily Briefing",
            "current_time": _now(),
            "market_countdown": None,
            "next_event": todays_events[0] if todays_events else None,
            "research_queue_count": queue.get("count") or 0,
        },
        "top_summary": top,
        "executive_brief": exec_brief,
        "priorities": priorities,
        "overnight_activity": overnight,
        "research_queue": queue,
        "opportunities": opportunities,
        "market_summary": market,
        "macro": macro,
        "calendar": calendar,
        "portfolio_monitor": portfolio,
        "sector_monitor": sectors,
        "metrics": metrics,
        "analyst_workspace": {
            "assigned_companies": [p.get("ticker") for p in priorities[:8]],
            "pending_reviews": queue.get("items") or [],
            "notes": [],
            "bookmarks": [],
            "draft_reports": [],
        },
        "investment_calendar": {
            "today": calendar.get("earnings_today") or [],
            "tomorrow": [],
            "this_week": calendar.get("upcoming_earnings") or [],
            "macro": todays_events,
        },
        "ai_summary": ai,
        "actions": [
            "refresh_morning_office",
            "generate_morning_brief",
            "open_knowledge_operations",
            "open_research_queue",
            "open_macro",
            "open_portfolio",
            "download_pdf",
            "export_excel",
        ],
        "links": {
            "knowledge_operations": "/admin/knowledge-operations",
            "research_queue": "/admin/investment-office#research-queue",
            "macro": "/macro-intelligence",
            "portfolio": "/portfolio",
        },
        "iol_available": not bool(iol.get("error")),
        "desk_enabled": bool(desk.get("enabled")),
        "building": False,
        "delivery": {"mode": "live_rebuild", "class": "morning_brief"},
        "cache": {"hit": False, "ttl_s": _OVERVIEW_CACHE_TTL_S, "source": "live_rebuild"},
    }

    with _OVERVIEW_CACHE_LOCK:
        _OVERVIEW_CACHE["at"] = time.time()
        _OVERVIEW_CACHE["payload"] = deepcopy(out)
    if persist_snapshot:
        try:
            from investment_office.morning_snapshot import put_snapshot

            put_snapshot(out, trigger="live_rebuild" if force else "cold_bootstrap")
        except Exception:
            pass
    return out


def slice_overview(key: str) -> Dict[str, Any]:
    """Return a named slice of the morning overview for focused API endpoints."""
    overview = build_morning_overview()
    mapping = {
        "morning-office": {
            "ok": True,
            "header": overview.get("header"),
            "top_summary": overview.get("top_summary"),
            "executive_brief": overview.get("executive_brief"),
            "priorities": overview.get("priorities"),
            "overnight_activity": overview.get("overnight_activity"),
            "ai_summary": overview.get("ai_summary"),
            "generated_at": overview.get("generated_at"),
            "version": overview.get("version"),
        },
        "daily-brief": {
            "ok": True,
            "executive_brief": overview.get("executive_brief"),
            "ai_summary": overview.get("ai_summary"),
            "generated_at": overview.get("generated_at"),
            "version": overview.get("version"),
            "policy": POLICY,
        },
        "research-queue": {
            "ok": True,
            **(overview.get("research_queue") or {}),
            "generated_at": overview.get("generated_at"),
        },
        "opportunities": {
            "ok": True,
            "items": overview.get("opportunities") or [],
            "note": "Monitoring only — not recommendations",
            "issues_recommendations": False,
            "generated_at": overview.get("generated_at"),
        },
        "market-summary": {
            "ok": True,
            **(overview.get("market_summary") or {}),
            "generated_at": overview.get("generated_at"),
        },
        "macro": {
            "ok": True,
            **(overview.get("macro") or {}),
            "generated_at": overview.get("generated_at"),
        },
        "calendar": {
            "ok": True,
            **(overview.get("calendar") or {}),
            "investment_calendar": overview.get("investment_calendar"),
            "generated_at": overview.get("generated_at"),
        },
        "portfolio-monitor": {
            "ok": True,
            **(overview.get("portfolio_monitor") or {}),
            "generated_at": overview.get("generated_at"),
        },
        "sector-monitor": {
            "ok": True,
            "sectors": overview.get("sector_monitor") or [],
            "generated_at": overview.get("generated_at"),
        },
        "metrics": {
            "ok": True,
            **(overview.get("metrics") or {}),
            "top_summary": overview.get("top_summary"),
            "generated_at": overview.get("generated_at"),
        },
    }
    if key not in mapping:
        return {"ok": False, "error": f"unknown slice: {key}"}
    return mapping[key]


def refresh_morning_office(*, wait: bool = False) -> Dict[str, Any]:
    """Queue (default) or wait for morning snapshot rebuild — never blocks UI by default.

    Does not run IO desk / ICF / IEP / CGL on the request path. The snapshot builder
    pulls those soft deps when the background job (or wait=True) runs.
    """
    from investment_office.morning_snapshot import enqueue_refresh, get_snapshot

    result = enqueue_refresh(trigger="admin_refresh", wait=wait)
    return {
        **result,
        "refreshed_at": _now(),
        "overview": get_snapshot() if not wait else result.get("overview") or get_snapshot(),
        "message": result.get("message")
        or ("Morning snapshot rebuilt" if wait else "Morning snapshot rebuild queued"),
    }


def generate_morning_brief() -> Dict[str, Any]:
    """Regenerate executive + AI morning brief into a new snapshot (async-friendly)."""
    from investment_office.morning_snapshot import enqueue_refresh, get_snapshot

    result = enqueue_refresh(trigger="generate_morning_brief", wait=False)
    snap = get_snapshot() or {}
    return {
        "ok": True,
        "generated_at": _now(),
        "status": result.get("status"),
        "job_id": result.get("job_id"),
        "executive_brief": snap.get("executive_brief"),
        "ai_summary": snap.get("ai_summary"),
        "priorities": snap.get("priorities"),
        "top_summary": snap.get("top_summary"),
        "policy": POLICY,
        "issues_recommendations": False,
        "message": "Brief regeneration queued against morning snapshot pipeline",
    }
