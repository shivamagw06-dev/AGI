"""Knowledge Health — Mission Control knowledge-aware metrics (not infra-only)."""

from __future__ import annotations

from typing import Any, Dict, List

from ..schema import (
    COLLECTOR_SUCCESS_TARGET,
    KIL_PHASE1_DEMO,
    KNOWLEDGE_LATENCY_TARGET_MINUTES,
    KIL_VERSION,
    KIL_WORKSTREAM_ID,
)


def knowledge_health_board(*, demo_only: bool = True, live_integrate: bool = False) -> Dict[str, Any]:
    """Mission Control Knowledge Health.

    Default uses persisted / in-memory KIL state (fast). Set live_integrate=True
    only for explicit deep refresh — integrating five companies is too slow for MC.
    """
    from ..layer import get_integrated_company, integrate_company, kil_status
    from ..versioning.snapshots import get_latest_snapshot
    from ..schema import EXPANSION_NEXT_UNIVERSE, EXPANSION_NEXT_SIZE

    tickers = list(KIL_PHASE1_DEMO) if demo_only else list(KIL_PHASE1_DEMO)
    rows: List[Dict[str, Any]] = []
    ready_n = 0
    knowledge_ready_n = 0
    confidences: List[float] = []
    freshness_vals: List[float] = []
    missing_statements = 0
    missing_transcripts = 0
    unsupported = 0

    for t in tickers:
        try:
            integ = get_integrated_company(t)
            if integ is None and live_integrate:
                integ = integrate_company(t, trigger_repair=False)
            if integ is None:
                rows.append(
                    {
                        "ticker": t,
                        "coverage_state": "PENDING_INTEGRATION",
                        "research_ready": False,
                        "note": "Awaiting KIL integrate (CGL cycle or POST /iep/kil/integrate)",
                    }
                )
                missing_statements += 1
                continue
            st = integ.get("coverage_state") or {}
            kc = integ.get("knowledge_confidence") or {}
            if integ.get("research_ready"):
                ready_n += 1
            if st.get("coverage_state") in {
                "KNOWLEDGE READY",
                "RESEARCH READY",
                "INSTITUTIONAL COVERAGE COMPLETE",
                "CONTINUOUS MONITORING",
            }:
                knowledge_ready_n += 1
            if kc.get("knowledge_confidence") is not None:
                confidences.append(float(kc["knowledge_confidence"]))
            if not integ.get("financials_published"):
                missing_statements += 1
            rows.append(
                {
                    "ticker": t,
                    "entity_id": integ.get("entity_id"),
                    "coverage_state": st.get("coverage_state"),
                    "knowledge_confidence": kc.get("knowledge_confidence"),
                    "research_ready": integ.get("research_ready"),
                    "claim_safe": integ.get("claim_safe"),
                    "period_count": integ.get("period_count"),
                }
            )
        except Exception as exc:
            rows.append({"ticker": t, "error": str(exc)[:160]})
            missing_statements += 1

    # Soft CGL metrics
    cgl = {}
    try:
        from continuous_gather_learn.production import dashboard as cgl_dash, health as cgl_health

        cgl = {"health": cgl_health(), "dashboard": cgl_dash()}
    except Exception as exc:
        cgl = {"error": str(exc)[:160]}

    dash = (cgl.get("dashboard") or {}) if isinstance(cgl, dict) else {}
    collector_success = dash.get("collector_success_rate")
    scheduler_status = None
    try:
        from institutional_scheduler.production import health as sch_health

        scheduler_status = (sch_health() or {}).get("state")
    except Exception:
        pass

    snap = get_latest_snapshot()
    n = max(1, len(tickers))
    avg_conf = round(sum(confidences) / len(confidences), 2) if confidences else None
    avg_ready = None
    ready_scores = [
        r.get("knowledge_confidence")
        for r in rows
        if isinstance(r.get("knowledge_confidence"), (int, float))
    ]
    if ready_scores:
        avg_ready = round(sum(float(x) for x in ready_scores) / len(ready_scores), 2)

    return {
        "ok": True,
        "board": "Knowledge Health",
        "workstream_id": KIL_WORKSTREAM_ID,
        "version": KIL_VERSION,
        "kil": kil_status(),
        "metrics": {
            "coverage_complete_demo": sum(
                1
                for r in rows
                if r.get("coverage_state")
                in {"INSTITUTIONAL COVERAGE COMPLETE", "CONTINUOUS MONITORING"}
            ),
            "research_ready": ready_n,
            "knowledge_ready": knowledge_ready_n,
            "knowledge_confidence_avg": avg_conf,
            "companies_updated": len([r for r in rows if r.get("period_count")]),
            "evidence_added": (snap or {}).get("evidence_added"),
            "broken_evidence_links": None,
            "unsupported_claims": unsupported,
            "average_freshness": None,
            "missing_transcripts": missing_transcripts,
            "missing_statements": missing_statements,
            "average_research_readiness": avg_ready,
            "average_knowledge_confidence": avg_conf,
            "knowledge_latency_target_minutes": KNOWLEDGE_LATENCY_TARGET_MINUTES,
            "scheduler_status": scheduler_status,
            "collector_success": collector_success,
            "collector_success_target": COLLECTOR_SUCCESS_TARGET,
            "demo_sample_size": n,
        },
        "companies": rows,
        "latest_knowledge_snapshot": snap,
        "cgl": {
            "enabled": (cgl.get("health") or {}).get("enabled"),
            "hard_coverage_pct": dash.get("hard_coverage_pct"),
            "covered_companies": dash.get("covered_companies"),
            "total_companies": dash.get("total_companies"),
            "companies_remaining": dash.get("companies_remaining"),
            "latest_run": dash.get("latest_run"),
        },
        "expansion": {
            "next_universe": EXPANSION_NEXT_UNIVERSE,
            "next_size": EXPANSION_NEXT_SIZE,
            "gate": "Unlock only after Phase-1 demo + Top-20 Institutional Coverage Complete",
        },
        "tracked": [
            "Coverage Complete",
            "Research Ready",
            "Knowledge Confidence",
            "Companies Updated",
            "Evidence Added",
            "Broken Evidence Links",
            "Unsupported Claims",
            "Average Freshness",
            "Missing Transcripts",
            "Missing Statements",
            "Average Research Readiness",
            "Average Knowledge Confidence",
            "Knowledge Latency",
            "Scheduler Status",
            "Collector Success",
        ],
        "rule": "No infrastructure-only dashboards — Mission Control is knowledge-aware",
    }
