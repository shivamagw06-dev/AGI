"""P5.10 Operational Metrics — platform health from orchestration outputs."""

from __future__ import annotations

from typing import Any

from investment_operations.util import as_float, now_iso


def build_operational_metrics(
    company_packs: list[dict[str, Any]],
    *,
    morning: dict[str, Any] | None = None,
    research_queue: dict[str, Any] | None = None,
    alerts: dict[str, Any] | None = None,
    catalysts: dict[str, Any] | None = None,
    portfolio: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ok_n = sum(1 for p in company_packs if p.get("ok"))
    total = len(company_packs)
    opp_changes = 0
    stale = 0
    for p in company_packs:
        oie = p.get("opportunity") or {}
        kd = {}
        if isinstance(oie.get("opportunity"), dict):
            kd = oie["opportunity"].get("knowledge_delta") or {}
        if not kd:
            kd = p.get("memory_delta") or {}
        if kd.get("status") and kd.get("status") != "UNCHANGED":
            opp_changes += 1
        mem = p.get("memory") or {}
        if p.get("ok") and not mem.get("memory_version") and not (oie.get("freshness") or {}).get("memory_version"):
            # Soft stale heuristic: missing version metadata
            stale += 1

    return {
        "as_of": now_iso(),
        "operations_metrics": {
            "monitored_companies": ok_n,
            "coverage_universe": total,
            "compilation_success_rate": round(100.0 * ok_n / max(1, total), 1),
            "overnight_updates": len((morning or {}).get("overnight_changes") or []),
            "opportunity_changes": opp_changes,
            "contradiction_events": len((morning or {}).get("new_contradictions") or []),
            "portfolio_alerts": len((portfolio or {}).get("research_required") or []),
            "catalyst_count": (catalysts or {}).get("n") or len((morning or {}).get("catalysts") or []),
            "research_queue_size": (research_queue or {}).get("n") or 0,
            "alert_count": (alerts or {}).get("n") or 0,
            "stale_company_memory": stale,
            "avg_opportunity_score": _avg_score(company_packs),
        },
        "health": "ok" if ok_n == total and total > 0 else ("degraded" if ok_n else "empty"),
    }


def _avg_score(packs: list[dict[str, Any]]) -> float | None:
    vals = []
    for p in packs:
        sc = as_float((p.get("opportunity") or {}).get("score"))
        if sc is not None:
            vals.append(sc)
    if not vals:
        return None
    return round(sum(vals) / len(vals), 1)
