"""Mission Control / API dashboard for IEW."""

from __future__ import annotations

from typing import Any

from institutional_evidence_weighting import store as iew_store
from institutional_evidence_weighting.config import active_weight_version, list_profiles
from institutional_evidence_weighting.schema import COMPANY, IEW_VERSION, MODULE_CODE, PROGRAMME


def build_board() -> dict[str, Any]:
    tel = iew_store.telemetry_snapshot()
    runs = iew_store.latest_runs(limit=5)
    top: list[dict[str, Any]] = []
    weak: list[dict[str, Any]] = []
    conflicts: list[dict[str, Any]] = []
    if runs:
        latest = runs[0]
        top = list(latest.get("top_weighted") or [])[:10]
        weak = list(latest.get("weak_evidence") or [])[:10]
        conflicts = list(latest.get("conflicts") or [])[:10]
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "programme": PROGRAMME,
        "version": IEW_VERSION,
        "weight_version": active_weight_version(),
        "profiles": list_profiles(),
        "top_weighted_evidence": top,
        "evidence_distribution": tel.get("source_counts") or {},
        "average_weight": tel.get("average_weight"),
        "dominant_sources": tel.get("dominant_sources") or [],
        "weak_evidence": weak,
        "conflicting_evidence": conflicts,
        "replay_status": "replay_safe_inputs_only",
        "telemetry": tel,
        "n_recent_runs": len(runs),
        "fabricated": False,
        "llm_used": False,
    }
