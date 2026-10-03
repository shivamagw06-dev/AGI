"""ICC Mission Control / API dashboard."""

from __future__ import annotations

from typing import Any

from institutional_confidence_calibration import store as icc_store
from institutional_confidence_calibration.schema import (
    COMPANY,
    CONFIDENCE_VERSION,
    ICC_VERSION,
    MODULE_CODE,
    PROGRAMME,
)


def build_board() -> dict[str, Any]:
    tel = icc_store.telemetry_snapshot()
    runs = icc_store.latest_runs(limit=5)
    latest = runs[0] if runs else {}
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "programme": PROGRAMME,
        "version": ICC_VERSION,
        "confidence_version": CONFIDENCE_VERSION,
        "average_confidence": tel.get("average_confidence"),
        "confidence_distribution": tel.get("confidence_distribution"),
        "top_uncertainty_drivers": tel.get("top_uncertainty_drivers"),
        "evidence_penalties": {
            "average_missing_penalty": tel.get("average_missing_penalty"),
            "latest_missing_penalty": latest.get("missing_evidence_penalty"),
            "latest_total_penalty": ((latest.get("penalties") or {}).get("total")),
        },
        "committee_agreement": tel.get("average_committee_agreement"),
        "missing_evidence": latest.get("missing_evidence_that_would_raise") or [],
        "historical_analogue_quality": tel.get("average_historical_score"),
        "framework_consistency": tel.get("average_framework_consistency"),
        "latest_confidence": latest.get("overall_confidence"),
        "latest_level": latest.get("confidence_level"),
        "latest_reason": latest.get("confidence_reason"),
        "n_recent_runs": len(runs),
        "llm_used": False,
        "manually_assigned": False,
        "fabricated": False,
    }
