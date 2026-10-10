"""Mission Control — Institutional Coverage Dashboard."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from institutional_coverage_factory.config import load_config
from institutional_coverage_factory.schema import (
    EVIDENCE_CLASSES,
    ICF_PRODUCT,
    ICF_SPEC,
    ICF_VERSION,
    ICF_WORKSTREAM_ID,
    MISSION,
    PIPELINE,
)
from institutional_coverage_factory.universe import top20_tickers, universe_tickers


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def coverage_dashboard(*, scope: str = "TOP20", sample_limit: Optional[int] = None) -> Dict[str, Any]:
    """
    Institutional Coverage board.

    Default scope TOP20 for responsive Mission Control; pass UNIVERSE for broader.
    """
    cfg = load_config()
    scope_u = str(scope or "TOP20").upper()
    if scope_u == "UNIVERSE":
        tickers = universe_tickers()
    elif scope_u == "NIFTY100":
        from institutional_coverage_factory.universe import nifty100_tickers

        tickers = nifty100_tickers()
    elif scope_u == "NIFTY50":
        from institutional_coverage_factory.universe import nifty50_tickers

        tickers = nifty50_tickers()
    else:
        tickers = top20_tickers()

    if sample_limit is not None:
        tickers = tickers[: max(1, int(sample_limit))]

    from institutional_coverage_factory.scorer.score import score_evidence_classes
    from institutional_coverage_factory.validator.icc import evaluate_icc
    from institutional_coverage_factory.scheduler.loop import scheduler_status

    rows: List[Dict[str, Any]] = []
    icc_n = 0
    in_progress = 0
    blocked = 0
    missing_counts: Dict[str, int] = {k: 0 for k in EVIDENCE_CLASSES}
    collector_ok = 0
    collector_total = 0

    for t in tickers:
        try:
            score = score_evidence_classes(t)
            icc = evaluate_icc(t, score=score)
            st = icc.get("status") or "IN_PROGRESS"
            if icc.get("institutional_coverage_complete"):
                icc_n += 1
                st = "ICC_COMPLETE"
            elif st == "BLOCKED":
                blocked += 1
            else:
                in_progress += 1
            for m in score.get("missing_classes") or []:
                if m in missing_counts:
                    missing_counts[m] += 1
            rows.append(
                {
                    "ticker": t,
                    "coverage_pct": score.get("coverage_pct"),
                    "status": st,
                    "missing_classes": score.get("missing_classes"),
                    "icc": bool(icc.get("institutional_coverage_complete")),
                }
            )
        except Exception as exc:
            blocked += 1
            rows.append({"ticker": t, "status": "BLOCKED", "error": str(exc)[:160]})

    # Soft collector health from CGL
    collector_health = None
    try:
        from continuous_gather_learn.production import dashboard as cgl_dash

        d = cgl_dash()
        collector_health = d.get("collector_success_rate")
        if collector_health is not None:
            collector_ok = 1
            collector_total = 1
    except Exception:
        pass

    sch = scheduler_status()
    universe_size = len(universe_tickers())

    return {
        "ok": True,
        "board": "Institutional Coverage",
        "workstream_id": ICF_WORKSTREAM_ID,
        "product": ICF_PRODUCT,
        "version": ICF_VERSION,
        "spec": ICF_SPEC,
        "mission": MISSION,
        "pipeline": list(PIPELINE),
        "generated_at": _now(),
        "scope": scope_u,
        "metrics": {
            "universe": universe_size,
            "scoped_companies": len(tickers),
            "icc_complete": icc_n,
            "in_progress": in_progress,
            "blocked": blocked,
            "missing_presentations": missing_counts.get("earnings_presentations", 0),
            "missing_transcripts": missing_counts.get("earnings_call_transcripts", 0),
            "missing_shareholding": missing_counts.get("shareholding", 0),
            "missing_segment_kpis": missing_counts.get("segment_kpis", 0),
            "missing_annual_reports": missing_counts.get("annual_reports", 0),
            "missing_financial_statements": missing_counts.get("financial_statements", 0),
            "collector_health_pct": collector_health,
            "icc_entered_today": sch.get("icc_entered_today"),
            "max_companies_per_day": cfg["max_companies_per_day"],
            "daily_icc_target": cfg["max_companies_per_day"],
        },
        "missing_by_class": missing_counts,
        "scheduler": sch,
        "config": {
            "enabled": cfg["enabled"],
            "max_companies_per_day": cfg["max_companies_per_day"],
            "max_parallel_collectors": cfg["max_parallel_collectors"],
            "priority": cfg["priority"],
            "coverage_threshold": cfg["coverage_threshold"],
            "institutional_coverage_threshold": cfg["institutional_coverage_threshold"],
        },
        "companies": rows,
        "north_star": "Companies entering Institutional Coverage Complete per day",
        "milestone_focus": "Top 20 → >90% coverage before scaling ICC throughput / universe",
    }
