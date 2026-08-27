"""IHE Mission Control / API dashboard."""

from __future__ import annotations

from typing import Any

from institutional_hypothesis_evaluation import store as ihe_store
from institutional_hypothesis_evaluation.schema import COMPANY, EVALUATION_VERSION, IHE_VERSION, MODULE_CODE, PROGRAMME


def build_board() -> dict[str, Any]:
    tel = ihe_store.telemetry_snapshot()
    runs = ihe_store.latest_runs(limit=5)
    latest = runs[0] if runs else {}
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "programme": PROGRAMME,
        "version": IHE_VERSION,
        "evaluation_version": EVALUATION_VERSION,
        "preferred_hypotheses": latest.get("preferred_ids") or [],
        "rejected_hypotheses": latest.get("rejected_ids") or [],
        "average_support": tel.get("average_support"),
        "average_conflict": tel.get("average_conflict"),
        "coverage": latest.get("average_coverage"),
        "missing_evidence_frequency": tel.get("missing_evidence_frequency"),
        "confidence_distribution": latest.get("confidence_distribution") or {},
        "outcome": latest.get("outcome"),
        "plural": latest.get("plural"),
        "forced_single_winner": False,
        "telemetry": tel,
        "n_recent_runs": len(runs),
        "fabricated": False,
        "llm_used": False,
    }
