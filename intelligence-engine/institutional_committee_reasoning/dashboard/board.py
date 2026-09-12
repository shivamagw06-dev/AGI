"""ICR Mission Control / API dashboard."""

from __future__ import annotations

from typing import Any

from institutional_committee_reasoning import store as icr_store
from institutional_committee_reasoning.schema import COMMITTEE_VERSION, COMPANY, ICR_VERSION, MODULE_CODE, PROGRAMME


def build_board() -> dict[str, Any]:
    tel = icr_store.telemetry_snapshot()
    runs = icr_store.latest_runs(limit=5)
    latest = runs[0] if runs else {}
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "programme": PROGRAMME,
        "version": ICR_VERSION,
        "committee_version": COMMITTEE_VERSION,
        "bull_base_bear_distribution": {
            "bull": tel.get("n_bull"),
            "base": tel.get("n_base"),
            "bear": tel.get("n_bear"),
        },
        "average_confidence": tel.get("average_confidence"),
        "probability_distribution": latest.get("probability_distribution") or {},
        "unresolved_disagreements": tel.get("unresolved_disagreements"),
        "missing_evidence": tel.get("missing_evidence"),
        "dominant_assumptions": latest.get("dominant_assumptions") or [],
        "historical_analogue_usage": latest.get("n_analogues") or 0,
        "preferred_case": latest.get("preferred_case"),
        "n_recent_runs": len(runs),
        "voting_engine": False,
        "fabricated": False,
        "llm_used": False,
    }
