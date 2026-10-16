"""RCI analyse entry — failures → clusters → suggested fixes → top-10."""

from __future__ import annotations

import time
from typing import Any
from uuid import uuid4

from root_cause_intelligence.clustering.engine import cluster_failures
from root_cause_intelligence.failures.extract import extract_failures
from root_cause_intelligence.fixes.suggest import recommend_prs
from root_cause_intelligence.schema import MODULE_CODE, QUALITY_TARGETS, RCI_VERSION
from root_cause_intelligence import store


def analyze_iel_run(
    iel_summary: dict[str, Any],
    *,
    persist: bool = True,
) -> dict[str, Any]:
    """
    Consume an IEL run summary (with scored rows) and produce RCI output.

    Engineering loop step: Judges → RCI → Top 10 Failure Clusters → Recommended PR
    """
    t0 = time.time()
    rows = list(iel_summary.get("rows") or [])
    hard_failures = extract_failures(rows, include_dimension_misses=False)
    failures = extract_failures(rows, include_dimension_misses=True)
    clustered = cluster_failures(failures)
    recommendations = recommend_prs(clustered.get("top_20") or [], top_n=10)

    # Attach suggested_fix onto top clusters
    top10 = []
    rec_by_key = {r["cluster_key"]: r for r in recommendations}
    for c in clustered.get("top_10") or []:
        row = dict(c)
        row["suggested_fix"] = rec_by_key.get(c.get("cluster_key"))
        top10.append(row)

    # Accuracy proxies from IEL dimensions when present
    n = len(rows) or 1
    fw_ok = sum(
        1 for r in rows if ((r.get("dimensions") or {}).get("framework") or {}).get("passed")
    )
    intent_ok = sum(
        1 for r in rows if ((r.get("dimensions") or {}).get("intent") or {}).get("passed")
    )
    hall_fail = sum(
        1
        for r in rows
        if ((r.get("dimensions") or {}).get("hallucinated_evidence") or {}).get("passed") is False
    )
    replay_rows = [r for r in rows if r.get("category") == "historical_replay" or (r.get("dimensions") or {}).get("replay", {}).get("n/a") is not True]
    # simpler: count replay dimension fails among rows that have as_of expectations via root cause
    replay_fail = sum(1 for r in rows if "future_leakage" in (r.get("root_causes") or []) or "as_of_miss" in (r.get("root_causes") or []))

    out = {
        "analysis_id": f"rci-{uuid4().hex[:10]}",
        "module": MODULE_CODE,
        "version": RCI_VERSION,
        "iel_run_id": iel_summary.get("run_id"),
        "iel_suite": iel_summary.get("suite"),
        "iel_commit": iel_summary.get("commit"),
        "iel_pass_pct": (iel_summary.get("aggregate") or {}).get("pass_pct"),
        "iel_mean_score": (iel_summary.get("aggregate") or {}).get("mean_score"),
        "n_questions": len(rows),
        "n_hard_failures": len(hard_failures),
        "n_failures": len(failures),
        "n_dimension_misses": max(0, len(failures) - len(hard_failures)),
        "n_clusters": clustered.get("n_clusters"),
        "top_10_clusters": top10,
        "recommended_prs": recommendations,
        "failures_sample": failures[:30],
        "kpi_proxies": {
            "framework_accuracy_pct": round(100.0 * fw_ok / n, 2),
            "intent_accuracy_pct": round(100.0 * intent_ok / n, 2),
            "hallucinated_evidence_count": hall_fail,
            "replay_leakage_or_asof_fail_count": replay_fail,
        },
        "targets": QUALITY_TARGETS,
        "gaps": {
            "iel_pass_pct": round(
                QUALITY_TARGETS["iel_pass_pct"] - float((iel_summary.get("aggregate") or {}).get("pass_pct") or 0),
                2,
            ),
            "framework_accuracy_pct": round(
                QUALITY_TARGETS["framework_accuracy_pct"] - round(100.0 * fw_ok / n, 2),
                2,
            ),
            "intent_accuracy_pct": round(
                QUALITY_TARGETS["intent_accuracy_pct"] - round(100.0 * intent_ok / n, 2),
                2,
            ),
        },
        "engineering_loop": [
            "Git Commit",
            "1,025 Questions",
            "Judges",
            "RCI",
            "Top 10 Failure Clusters",
            "Recommended PR",
            "Engineer",
            "Benchmark Again",
        ],
        "latency_ms": int((time.time() - t0) * 1000),
        "reasoning_changed": False,
        "fabricated": False,
    }
    # Soft-wire Patch Intelligence briefs (never auto-codes)
    try:
        from patch_intelligence.production import from_rci

        out["patch_intelligence"] = from_rci(out, top_n=10)
    except Exception as exc:
        out["patch_intelligence"] = {"status": "error", "error": str(exc)[:160]}

    if persist:
        store.record(out)
    return out
