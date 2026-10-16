"""Coverage Planner — find non-ICC companies, rank, queue collectors."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from institutional_coverage_factory.config import load_config
from institutional_coverage_factory.flags import is_icf_dispatch_enabled, is_icf_enabled
from institutional_coverage_factory.schema import ICF_VERSION, ICF_WORKSTREAM_ID, PriorityTier
from institutional_coverage_factory.universe import ordered_universe, top20_tickers


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _tier_rank(tier: str, priority: List[str]) -> int:
    try:
        return priority.index(tier)
    except ValueError:
        return len(priority)


def plan_coverage(
    *,
    limit: Optional[int] = None,
    scope: str = "TOP20",
    skip_icc: bool = True,
) -> Dict[str, Any]:
    """
    Rank companies not yet ICC by priority tier then ascending coverage %.

    scope:
      TOP20 | NIFTY50 | NIFTY100 | UNIVERSE | ALL
    """
    if not is_icf_enabled():
        return {"ok": False, "enabled": False, "queue": []}

    cfg = load_config()
    priority = list(cfg.get("priority") or [t.value for t in PriorityTier])
    n = int(limit if limit is not None else cfg.get("companies_per_tick") or 8)

    scope_u = str(scope or "TOP20").upper()
    if scope_u == "TOP20":
        candidates = [{"ticker": t, "priority_tier": PriorityTier.TOP20.value} for t in top20_tickers()]
    elif scope_u in {"NIFTY50", "NIFTY100", "UNIVERSE", "ALL"}:
        allowed = set(priority)
        if scope_u == "NIFTY50":
            allowed = {PriorityTier.TOP20.value, PriorityTier.NIFTY50.value}
        elif scope_u == "NIFTY100":
            allowed = {
                PriorityTier.TOP20.value,
                PriorityTier.NIFTY50.value,
                PriorityTier.NIFTY100.value,
            }
        candidates = [
            c for c in ordered_universe(priority) if c["priority_tier"] in allowed or scope_u == "ALL"
        ]
        if scope_u == "ALL":
            candidates = ordered_universe(priority)
    else:
        candidates = [{"ticker": t, "priority_tier": PriorityTier.TOP20.value} for t in top20_tickers()]

    from institutional_coverage_factory.scorer.score import score_evidence_classes
    from institutional_coverage_factory.validator.icc import evaluate_icc

    ranked: List[Dict[str, Any]] = []
    icc_complete = 0
    for c in candidates:
        t = c["ticker"]
        try:
            score = score_evidence_classes(t)
            icc = evaluate_icc(t, score=score)
        except Exception as exc:
            ranked.append(
                {
                    "ticker": t,
                    "priority_tier": c["priority_tier"],
                    "coverage_pct": 0.0,
                    "status": "BLOCKED",
                    "missing_classes": [],
                    "error": str(exc)[:160],
                    "collectors": [],
                }
            )
            continue

        if icc.get("institutional_coverage_complete"):
            icc_complete += 1
            if skip_icc:
                # Already complete — only refresh changed classes (none queued here)
                continue

        missing = list(score.get("missing_classes") or [])
        from institutional_coverage_factory.collectors.dispatch import collectors_for_missing

        ranked.append(
            {
                "ticker": t,
                "priority_tier": c["priority_tier"],
                "tier_rank": _tier_rank(c["priority_tier"], priority),
                "coverage_pct": float(score.get("coverage_pct") or 0),
                "status": icc.get("status"),
                "missing_classes": missing,
                "collectors": collectors_for_missing(missing),
                "icc": {
                    "complete": bool(icc.get("institutional_coverage_complete")),
                    "failed": icc.get("failed"),
                },
            }
        )

    ranked.sort(key=lambda r: (r.get("tier_rank", 99), r.get("coverage_pct", 0.0), r.get("ticker")))
    queue = ranked[:n]

    return {
        "ok": True,
        "workstream_id": ICF_WORKSTREAM_ID,
        "version": ICF_VERSION,
        "generated_at": _now(),
        "scope": scope_u,
        "config": {
            "max_companies_per_day": cfg["max_companies_per_day"],
            "companies_per_tick": cfg["companies_per_tick"],
            "priority": priority,
            "coverage_threshold": cfg["coverage_threshold"],
        },
        "candidates_scanned": len(candidates),
        "icc_complete_in_scope": icc_complete,
        "non_icc": len(ranked),
        "queue": queue,
        "metric": "companies_entering_icc_per_day",
        "note": "Daily target is ICC completions, not crawl count.",
    }


def plan_and_dispatch(
    *,
    limit: Optional[int] = None,
    scope: str = "TOP20",
    dispatch: Optional[bool] = None,
) -> Dict[str, Any]:
    plan = plan_coverage(limit=limit, scope=scope, skip_icc=True)
    do_dispatch = is_icf_dispatch_enabled() if dispatch is None else bool(dispatch)
    results: List[Dict[str, Any]] = []
    if do_dispatch:
        from institutional_coverage_factory.collectors.dispatch import dispatch_collectors

        for item in plan.get("queue") or []:
            try:
                results.append(
                    dispatch_collectors(
                        item["ticker"],
                        missing_classes=item.get("missing_classes"),
                        integrate=True,
                    )
                )
            except Exception as exc:
                results.append(
                    {"ok": False, "ticker": item.get("ticker"), "error": str(exc)[:200]}
                )
    return {
        **plan,
        "dispatch_enabled": do_dispatch,
        "dispatch_results": results,
        "dispatched": len(results),
        "icc_entered": sum(
            1
            for r in results
            if (r.get("icc") or {}).get("institutional_coverage_complete")
        ),
    }
