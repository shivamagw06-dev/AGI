"""Observability — track research quality, not just infrastructure."""

from __future__ import annotations

from typing import Any, Dict, List

from ..schema import PHASE1_TOP20, PHASE1_ACCEPTANCE_CRITERIA, RESEARCH_READY_THRESHOLD


def research_quality_metrics(*, sample_limit: int = 5) -> Dict[str, Any]:
    """
    Mission Control metrics:
    Evidence Coverage, Companies Ready, Research Block Rate, Average Freshness,
    Unsupported Claims, Recommendation Overrides, Analyst Corrections, Evidence Latency.
    """
    from ..production import get_research_pack
    from ..phase1_acceptance import evaluate_institutional_coverage

    rows: List[Dict[str, Any]] = []
    ready = 0
    blocked = 0
    freshness_vals: List[float] = []
    unsupported = 0
    coverage_complete = 0
    # Sample first N for cheap MC slice; full scan via /iep/phase1
    sample = list(PHASE1_TOP20)[: max(1, min(sample_limit, len(PHASE1_TOP20)))]
    for c in sample:
        t = c["ticker"]
        try:
            pack = get_research_pack(t, auto_acquire=True)
            rr = bool(pack.get("research_ready"))
            if rr:
                ready += 1
            else:
                blocked += 1
            items = ((pack.get("evidence") or {}).get("registry") or {}).get("items") or []
            for i in items:
                if i.get("freshness_days") is not None:
                    freshness_vals.append(float(i["freshness_days"]))
            cov = evaluate_institutional_coverage(t, pack=pack)
            if cov.get("institutional_coverage_complete"):
                coverage_complete += 1
            rows.append(
                {
                    "ticker": t,
                    "research_ready": rr,
                    "claim_safe": pack.get("claim_safe"),
                    "score": (pack.get("research_readiness") or {}).get("score"),
                    "coverage_complete": cov.get("institutional_coverage_complete"),
                }
            )
        except Exception as exc:
            blocked += 1
            rows.append({"ticker": t, "error": str(exc)[:120]})

    n = max(1, len(sample))
    avg_fresh = round(sum(freshness_vals) / len(freshness_vals), 2) if freshness_vals else None
    return {
        "ok": True,
        "metrics": {
            "evidence_coverage_sample": rows,
            "companies_ready": ready,
            "companies_sampled": len(sample),
            "phase1_total": len(PHASE1_TOP20),
            "research_block_rate_pct": round(100.0 * blocked / n, 2),
            "average_freshness_days": avg_fresh,
            "unsupported_claims": unsupported,
            "recommendation_overrides": None,  # filled when analyst override ledger lands
            "analyst_corrections": None,
            "evidence_latency_hours": None,
            "institutional_coverage_complete_count": coverage_complete,
            "research_ready_threshold": RESEARCH_READY_THRESHOLD,
        },
        "acceptance_criteria": list(PHASE1_ACCEPTANCE_CRITERIA),
        "tracked": [
            "Evidence Coverage",
            "Companies Ready",
            "Research Block Rate",
            "Average Freshness",
            "Unsupported Claims",
            "Recommendation Overrides",
            "Analyst Corrections",
            "Evidence Latency",
        ],
        "note": "Sampled metrics for Mission Control; full universe via /iep/phase1",
    }
