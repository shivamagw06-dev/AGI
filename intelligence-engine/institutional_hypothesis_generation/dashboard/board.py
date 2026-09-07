"""Hypothesis dashboard for Mission Control / API."""

from __future__ import annotations

from typing import Any

from institutional_hypothesis_generation import store as ihg_store
from institutional_hypothesis_generation.catalog import active_catalog_id
from institutional_hypothesis_generation.schema import COMPANY, HYPOTHESIS_VERSION, IHG_VERSION, MODULE_CODE, PROGRAMME


def build_board() -> dict[str, Any]:
    tel = ihg_store.telemetry_snapshot()
    runs = ihg_store.latest_runs(limit=5)
    latest = runs[0] if runs else {}
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "programme": PROGRAMME,
        "version": IHG_VERSION,
        "hypothesis_version": active_catalog_id() or HYPOTHESIS_VERSION,
        "average_hypotheses": tel.get("average_hypotheses"),
        "rejected_hypotheses": tel.get("n_rejected"),
        "contested_runs": tel.get("n_contested"),
        "insufficient_runs": tel.get("n_insufficient"),
        "winning_hypothesis": (latest.get("winning_hypothesis_ids") or [None])[0],
        "winning_hypothesis_ids": latest.get("winning_hypothesis_ids") or [],
        "hypothesis_confidence": latest.get("average_confidence") or tel.get("average_confidence"),
        "evidence_support": latest.get("top_support_score"),
        "conflict_score": latest.get("top_conflict_score"),
        "outcome": latest.get("outcome"),
        "plural": latest.get("plural"),
        "forced_single_winner": False,
        "telemetry": tel,
        "n_recent_runs": len(runs),
        "fabricated": False,
        "llm_used": False,
    }
