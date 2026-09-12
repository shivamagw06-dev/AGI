"""IDS-02 — Decision Calibration & Explainability constants."""

from __future__ import annotations


CAL_WORKSTREAM_ID = "IDS-02"
CAL_PRODUCT = "Decision Calibration & Explainability"
CAL_VERSION = "ids-02-v1.0.0"
CAL_SPEC = "docs/AGI_IDS_02_DECISION_CALIBRATION.md"
CAL_ROLE = "deterministic_decision_calibration"
CALIBRATION_ENGINE_VERSION = "ids-02-calibration-engine-v1"
CALIBRATION_PROFILE_VERSION = "ids-02-profile-default-v1"
EXPLAINABILITY_VERSION = "ids-02-explainability-v1"
DRIFT_VERSION = "ids-02-drift-v1"
SCORECARD_VERSION = "ids-02-scorecard-v1"


def clamp_int(value: float | int, lo: int = 0, hi: int = 100) -> int:
    try:
        n = int(round(float(value)))
    except (TypeError, ValueError):
        n = lo
    return max(lo, min(hi, n))
