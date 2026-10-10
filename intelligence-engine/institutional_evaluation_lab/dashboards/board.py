"""IEL Mission Control board."""

from __future__ import annotations

from typing import Any

from institutional_evaluation_lab.datasets.catalog import catalog_stats
from institutional_evaluation_lab.schema import IEL_VERSION, MODULE_CODE, QUALITY_TARGETS
from institutional_evaluation_lab import store


def build_board() -> dict[str, Any]:
    stats = catalog_stats()
    runs = store.list_runs(limit=10)
    baseline = store.load_baseline()
    latest = runs[0] if runs else None
    return {
        "module": MODULE_CODE,
        "version": IEL_VERSION,
        "catalogue": stats,
        "quality_targets": QUALITY_TARGETS,
        "baseline": baseline,
        "latest_run": {
            "run_id": (latest or {}).get("run_id"),
            "suite": (latest or {}).get("suite"),
            "pass_pct": ((latest or {}).get("aggregate") or {}).get("pass_pct"),
            "mean_score": ((latest or {}).get("aggregate") or {}).get("mean_score"),
            "n": ((latest or {}).get("aggregate") or {}).get("n"),
            "hypothesis_quality_score": (latest or {}).get("hypothesis_quality_score")
            or ((latest or {}).get("aggregate") or {}).get("hypothesis_quality"),
            "committee_quality_score": (latest or {}).get("committee_quality_score")
            or ((latest or {}).get("aggregate") or {}).get("committee_quality"),
            "confidence_quality_score": (latest or {}).get("confidence_quality_score")
            or ((latest or {}).get("aggregate") or {}).get("confidence_quality"),
            "thesis_quality_score": (latest or {}).get("thesis_quality_score")
            or ((latest or {}).get("aggregate") or {}).get("thesis_quality"),
            "decision_quality_score": (latest or {}).get("decision_quality_score")
            or ((latest or {}).get("aggregate") or {}).get("decision_quality"),
            "portfolio_quality_score": (latest or {}).get("portfolio_quality_score")
            or ((latest or {}).get("aggregate") or {}).get("portfolio_quality"),
            "monitoring_quality_score": (latest or {}).get("monitoring_quality_score")
            or ((latest or {}).get("aggregate") or {}).get("monitoring_quality"),
            "learning_quality_score": (latest or {}).get("learning_quality_score")
            or ((latest or {}).get("aggregate") or {}).get("learning_quality"),
            "regression": (latest or {}).get("regression"),
            "top_root_causes": ((latest or {}).get("aggregate") or {}).get("top_root_causes"),
        }
        if latest
        else None,
        "recent_runs": [
            {
                "run_id": r.get("run_id"),
                "suite": r.get("suite"),
                "pass_pct": (r.get("aggregate") or {}).get("pass_pct"),
                "mean_score": (r.get("aggregate") or {}).get("mean_score"),
                "mean_hqs": (
                    ((r.get("hypothesis_quality_score") or {}).get("mean_hqs"))
                    or ((r.get("aggregate") or {}).get("hypothesis_quality") or {}).get("mean_hqs")
                ),
                "mean_cqs": (
                    ((r.get("committee_quality_score") or {}).get("mean_cqs"))
                    or ((r.get("aggregate") or {}).get("committee_quality") or {}).get("mean_cqs")
                ),
                "mean_cfqs": (
                    ((r.get("confidence_quality_score") or {}).get("mean_cfqs"))
                    or ((r.get("aggregate") or {}).get("confidence_quality") or {}).get("mean_cfqs")
                ),
                "mean_itqs": (
                    ((r.get("thesis_quality_score") or {}).get("mean_itqs"))
                    or ((r.get("aggregate") or {}).get("thesis_quality") or {}).get("mean_itqs")
                ),
                "mean_dqs": (
                    ((r.get("decision_quality_score") or {}).get("mean_dqs"))
                    or ((r.get("aggregate") or {}).get("decision_quality") or {}).get("mean_dqs")
                ),
                "mean_pqs": (
                    ((r.get("portfolio_quality_score") or {}).get("mean_pqs"))
                    or ((r.get("aggregate") or {}).get("portfolio_quality") or {}).get("mean_pqs")
                ),
                "mean_mqs": (
                    ((r.get("monitoring_quality_score") or {}).get("mean_mqs"))
                    or ((r.get("aggregate") or {}).get("monitoring_quality") or {}).get("mean_mqs")
                ),
                "mean_lqs": (
                    ((r.get("learning_quality_score") or {}).get("mean_lqs"))
                    or ((r.get("aggregate") or {}).get("learning_quality") or {}).get("mean_lqs")
                ),
                "commit": r.get("commit"),
            }
            for r in runs[:8]
        ],
        "nightly_pipeline": [
            "GitHub Commit",
            "1000 Questions",
            "AGIB soft probe",
            "Deterministic Judge",
            "Score",
            "Hypothesis Quality Score",
            "Committee Quality Score",
            "Confidence Quality Score",
            "Investment Thesis Quality Score",
            "Decision Quality Score",
            "Portfolio Quality Score",
            "Root Cause",
            "Dashboard",
        ],
        "freeze": {
            "reasoning_engine": "frozen",
            "knowledge_factory": "frozen",
            "iew_v1": "frozen",
            "ihg_v1": "frozen",
            "measurement_only": True,
        },
    }
