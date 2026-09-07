"""Confidence calibration aggregates — expected vs realised accuracy."""

from __future__ import annotations

from typing import Any

from decision_quality import store as idq_store
from decision_quality.metrics.compute import compute_decision_metrics


def _avg(xs: list[float]) -> float:
    return round(sum(xs) / len(xs), 4) if xs else 0.0


def calibrate_slice(decisions: list[dict[str, Any]], *, key: str, value: str) -> dict[str, Any]:
    rows = [d for d in decisions if str(d.get(key) or "") == value]
    expected: list[float] = []
    realised: list[float] = []
    errors: list[float] = []
    skipped = 0
    for d in rows:
        m = compute_decision_metrics(d)
        if m.get("insufficient"):
            skipped += 1
            continue
        metrics = m["metrics"]
        expected.append(float(metrics["expected_confidence"]))
        realised.append(float(metrics["realised_accuracy"]))
        errors.append(float(metrics["calibration_error"]))
    return {
        "slice_key": key,
        "slice_value": value,
        "n": len(rows),
        "n_with_outcome": len(expected),
        "skipped_no_outcome": skipped,
        "expected_confidence": _avg(expected),
        "realised_accuracy": _avg(realised),
        "calibration_error": _avg(errors),
        "well_calibrated": _avg(errors) <= 0.25 if expected else False,
        "fabricated": False,
    }


def build_calibration_report(decisions: list[dict[str, Any]]) -> dict[str, Any]:
    overall = {
        "expected_confidence": 0.0,
        "realised_accuracy": 0.0,
        "calibration_error": 0.0,
        "n_with_outcome": 0,
    }
    expected: list[float] = []
    realised: list[float] = []
    errors: list[float] = []
    for d in decisions:
        m = compute_decision_metrics(d)
        if m.get("insufficient"):
            continue
        metrics = m["metrics"]
        expected.append(float(metrics["expected_confidence"]))
        realised.append(float(metrics["realised_accuracy"]))
        errors.append(float(metrics["calibration_error"]))
    if expected:
        overall = {
            "expected_confidence": _avg(expected),
            "realised_accuracy": _avg(realised),
            "calibration_error": _avg(errors),
            "n_with_outcome": len(expected),
            "well_calibrated": _avg(errors) <= 0.25,
        }

    by_sector = {}
    for s in sorted({str(d.get("sector")) for d in decisions if d.get("sector")}):
        by_sector[s] = calibrate_slice(decisions, key="sector", value=s)

    by_framework = {}
    for fw in sorted({str(d.get("primary_framework")) for d in decisions if d.get("primary_framework")}):
        by_framework[fw] = calibrate_slice(decisions, key="primary_framework", value=fw)

    by_regime = {}
    for r in sorted({str(d.get("macro_regime")) for d in decisions if d.get("macro_regime")}):
        by_regime[r] = calibrate_slice(decisions, key="macro_regime", value=r)

    by_company = {}
    for c in sorted({str(d.get("entity")) for d in decisions if d.get("entity")}):
        by_company[c] = calibrate_slice(decisions, key="entity", value=c)

    report = {
        "report_type": "confidence_calibration",
        "overall": overall,
        "by_sector": by_sector,
        "by_framework": by_framework,
        "by_macro_regime": by_regime,
        "by_company": by_company,
        "fabricated": False,
        "observability_only": True,
    }
    idq_store.put_calibration("latest", report)
    return report
