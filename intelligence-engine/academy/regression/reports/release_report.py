"""AGIB Institutional Regression Report generator."""

from __future__ import annotations

from typing import Any

from academy.regression.schema import IRS_VERSION


def build_report(
    *,
    release: str,
    benchmark: dict[str, Any],
    delta: dict[str, Any],
    gate: dict[str, Any],
    certification: dict[str, Any] | None = None,
) -> dict[str, Any]:
    iq = delta.get("overall_institutional_iq") or {}
    analysts = delta.get("analysts") or {}
    hall = benchmark.get("hallucinations") or {}
    by_sev = hall.get("by_severity") or {}

    lines = [
        "AGIB Institutional Regression Report",
        f"Release: {release}",
        f"IRS: {IRS_VERSION}",
        f"Golden set: {benchmark.get('golden_set_version')}",
        "",
        f"Institutional IQ: {iq.get('current')}  Previous: {iq.get('previous')}  Delta: {iq.get('delta')} {iq.get('arrow')}",
        "",
    ]
    for name, row in analysts.items():
        lines.append(
            f"{name.replace('_', ' ').title():<22} {row.get('current'):>6}  {row.get('arrow')} {row.get('delta')}"
        )
    lines += [
        "",
        "Hallucinations",
        f"  Critical {by_sev.get('critical', 0)}",
        f"  High     {by_sev.get('high', 0)}",
        f"  Medium   {by_sev.get('medium', 0)}",
        f"  Low      {by_sev.get('low', 0)}",
        f"Analyst Drift: {(benchmark.get('analyst_drift') or {}).get('total', 0)}",
        f"Certification: {(certification or {}).get('status', 'N/A')}",
        f"Regression: {'PASS' if gate.get('regression_pass') else 'FAIL'}",
        f"Recommendation Policy: {'PASS' if gate.get('recommendation_policy_pass') else 'FAIL'}",
        f"Merge Status: {gate.get('merge_status')}",
    ]

    return {
        "title": "AGIB Institutional Regression Report",
        "release": release,
        "irs_version": IRS_VERSION,
        "institutional_iq": iq,
        "analysts": analysts,
        "hallucinations": by_sev,
        "analyst_drift": (benchmark.get("analyst_drift") or {}).get("total", 0),
        "certification": certification or {},
        "gate": gate,
        "text": "\n".join(lines),
        "knowledge_retention": benchmark.get("knowledge_retention"),
        "case_transfer": benchmark.get("case_transfer"),
        "confidence_calibration": {
            k: (benchmark.get("confidence_calibration") or {}).get(k)
            for k in ("overconfidence", "underconfidence", "calibrated")
        },
    }
