"""IDS-02 production façades — health / calibrate / soft Mission Control slice."""

from __future__ import annotations

from typing import Any, Optional

from institutional_calibration.flags import flags_dict, is_enabled
from institutional_calibration.profile import DEFAULT_PROFILE
from institutional_calibration.schema import (
    CALIBRATION_ENGINE_VERSION,
    CALIBRATION_PROFILE_VERSION,
    CAL_PRODUCT,
    CAL_ROLE,
    CAL_SPEC,
    CAL_VERSION,
    CAL_WORKSTREAM_ID,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": CAL_WORKSTREAM_ID,
        "product": CAL_PRODUCT,
        "version": CAL_VERSION,
        "role": CAL_ROLE,
        "llm": False,
        "confidence_computed": True,
        "calibration_engine_version": CALIBRATION_ENGINE_VERSION,
        "default_profile_version": CALIBRATION_PROFILE_VERSION,
        "default_profile": DEFAULT_PROFILE.to_dict(),
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": CAL_SPEC,
        "brand": "AGI",
        "as_of": now_iso(),
    }


def soft_slice_mission_control() -> dict[str, Any]:
    h = health()
    return {
        "status": h.get("status"),
        "workstream_id": CAL_WORKSTREAM_ID,
        "product": CAL_PRODUCT,
        "version": CAL_VERSION,
        "llm": False,
        "confidence_computed": True,
        "default_profile_version": CALIBRATION_PROFILE_VERSION,
    }


def calibrate_company(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Calibrate a decision for a ticker (fixture) or full payload."""
    if not is_enabled():
        return {
            "ok": False,
            "enabled": False,
            "workstream_id": CAL_WORKSTREAM_ID,
            "rejected": True,
            "validation_errors": ["IDS-02 disabled"],
        }

    body = dict(payload or {})
    include_drift = body.pop("include_drift", True)
    include_calibration = body.pop("include_calibration", True)
    if isinstance(include_drift, str):
        include_drift = include_drift.strip().lower() in {"1", "true", "yes", "on"}
    if isinstance(include_calibration, str):
        include_calibration = include_calibration.strip().lower() in {"1", "true", "yes", "on"}

    from institutional_decision import history as decision_history
    from institutional_decision.production import decide_company
    from institutional_reporting.fixtures import get_fixture
    from institutional_reporting.models import InstitutionalReportInput
    from institutional_reporting.reason_composer import compose_reasons

    ticker = str(body.get("ticker") or "").strip()
    # Ensure a fresh decision path; decide_company already calibrates when wired.
    # Prefer re-running decision with calibration flags.
    result = decide_company(
        {
            **body,
            "ticker": ticker,
            "include_calibration": include_calibration,
            "include_drift": include_drift,
        }
    )
    return result


def get_calibrated_decision(
    ticker: str,
    *,
    include_calibration: bool = True,
    include_drift: bool = True,
) -> dict[str, Any]:
    from institutional_decision.production import get_company_decision

    return get_company_decision(
        ticker,
        include_history=False,
        include_calibration=include_calibration,
        include_drift=include_drift,
    )
