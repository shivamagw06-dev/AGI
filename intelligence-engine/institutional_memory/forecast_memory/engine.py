"""Forecast memory — versioned scenarios with calibration learning."""

from __future__ import annotations

from typing import Any

from institutional_memory.store.corpus import get_company
from institutional_memory.versioning.rules import assert_append_only


def forecast_history(ticker: str) -> dict[str, Any]:
    company = get_company(ticker)
    if not company:
        return {"found": False, "ticker": (ticker or "").upper(), "forecasts": []}
    forecasts = list(company.get("forecasts") or [])
    gate = assert_append_only(forecasts)
    calibrated = [f for f in forecasts if f.get("calibration") is not None]
    mean_cal = (
        round(sum(float(f["calibration"]) for f in calibrated) / len(calibrated), 3) if calibrated else None
    )
    return {
        "found": True,
        "ticker": company["ticker"],
        "forecasts": forecasts,
        "append_only": gate.get("append_only"),
        "every_forecast_versioned": gate.get("append_only"),
        "mean_calibration": mean_cal,
        "history": [
            {
                "version": f.get("version"),
                "date": f.get("date"),
                "distribution": f.get("distribution"),
                "most_likely": f.get("most_likely"),
                "actual_outcome": f.get("actual_outcome"),
                "calibration": f.get("calibration"),
                "learning": f.get("learning"),
            }
            for f in forecasts
        ],
        "rule": "Every forecast versioned — never deterministic overwrites",
    }
