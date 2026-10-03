"""Analyst drift — mandate violations."""

from __future__ import annotations

from typing import Any

from academy.regression.schema import DriftFinding

# Forbidden topic markers by analyst mandate
_FORBIDDEN: dict[str, list[str]] = {
    "business": ["deep dcf", "terminal value wacc", "macro forecast gdp next year", "full financial model"],
    "valuation": ["brand moat analysis", "porter rivalry deep", "competitive strategy war"],
    "financial": ["macro outlook rates next year", "sector demand forecast 2030"],
    "risk": ["intrinsic value equals", "management integrity scorecard deep"],
    "committee": ["new primary evidence invented", "i collected fresh filings"],
    "macro": ["company moat width", "brand pricing power deep dive"],
    "management": ["reverse dcf implied growth 24%"],
    "sector": ["cio portfolio weight recommendation"],
    "portfolio": ["single-stock dcf rebuild from scratch"],
}


def detect_drift(analyst: str, question_id: str, text: str) -> list[DriftFinding]:
    blob = (text or "").lower()
    findings: list[DriftFinding] = []
    for i, marker in enumerate(_FORBIDDEN.get(analyst, []), start=1):
        if marker in blob:
            findings.append(
                DriftFinding(
                    finding_id=f"drift_{question_id}_{i}",
                    analyst=analyst,
                    violation=marker,
                    detail=f"{analyst} drifted into forbidden mandate area: {marker}",
                    question_id=question_id,
                )
            )
    # Committee must not create new evidence
    if analyst == "committee" and "i found new unpublished evidence" in blob:
        findings.append(
            DriftFinding(
                finding_id=f"drift_{question_id}_ev",
                analyst=analyst,
                violation="create_new_evidence",
                detail="Committee created new evidence instead of evaluating",
                question_id=question_id,
            )
        )
    return findings


def summarize(findings: list[DriftFinding]) -> dict[str, Any]:
    return {
        "total": len(findings),
        "by_analyst": _by_analyst(findings),
        "findings": [f.to_dict() for f in findings],
    }


def _by_analyst(findings: list[DriftFinding]) -> dict[str, int]:
    out: dict[str, int] = {}
    for f in findings:
        out[f.analyst] = out.get(f.analyst, 0) + 1
    return out
