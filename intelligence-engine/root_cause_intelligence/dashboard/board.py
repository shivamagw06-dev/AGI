"""RCI Mission Control board."""

from __future__ import annotations

from typing import Any

from root_cause_intelligence.schema import MODULE_CODE, QUALITY_TARGETS, RCI_VERSION
from root_cause_intelligence import store


def build_board() -> dict[str, Any]:
    latest = store.latest() or {}
    return {
        "module": MODULE_CODE,
        "version": RCI_VERSION,
        "latest_analysis_id": latest.get("analysis_id"),
        "iel_run_id": latest.get("iel_run_id"),
        "iel_pass_pct": latest.get("iel_pass_pct"),
        "n_failures": latest.get("n_failures"),
        "n_clusters": latest.get("n_clusters"),
        "top_10": latest.get("top_10_clusters") or [],
        "recommended_prs": (latest.get("recommended_prs") or [])[:5],
        "kpi_proxies": latest.get("kpi_proxies"),
        "gaps": latest.get("gaps"),
        "quality_targets": QUALITY_TARGETS,
        "engineering_loop": latest.get("engineering_loop")
        or [
            "Git Commit",
            "Questions",
            "Judges",
            "RCI",
            "Top 10 Clusters",
            "Recommended PR",
        ],
        "freeze": {
            "reasoning_engine": "frozen",
            "selectors_not_patched_by_rci": True,
            "measurement_driven": True,
        },
    }
