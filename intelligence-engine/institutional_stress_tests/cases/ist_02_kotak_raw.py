"""IST-02 case definition — Kotak / RBI raw-evidence validation."""

from __future__ import annotations

from institutional_stress_tests.schema_ist02 import (
    IST02_ALLOWED_MODULES,
    IST02_CASE_ID,
    IST02_FAILURE_CODES,
    IST02_PASS_SCORE,
    IST02_REPORT_SECTIONS,
    IST02_RUBRIC_WEIGHTS,
    IST02_SPEC,
    IST02_WORKSTREAM_ID,
)

IST_02_CASE = {
    "case_id": IST02_CASE_ID,
    "workstream_id": IST02_WORKSTREAM_ID,
    "title": "Kotak Mahindra Bank — Raw Evidence Research Validation (RBI Apr 2024)",
    "spec": IST02_SPEC,
    "question": (
        "From raw disclosures only: reconstruct an institutional research view of Kotak "
        "Mahindra Bank after the April 2024 RBI restrictions."
    ),
    "primary_ticker": "KOTAKBANK",
    "peer_tickers": ("HDFCBANK", "ICICIBANK", "AXISBANK"),
    "raw_evidence_only": True,
    "fixture_answers_forbidden": True,
    "allowed_modules": list(IST02_ALLOWED_MODULES),
    "report_sections": list(IST02_REPORT_SECTIONS),
    "rubric_weights": dict(IST02_RUBRIC_WEIGHTS),
    "pass_score": IST02_PASS_SCORE,
    "failure_codes": list(IST02_FAILURE_CODES),
    "process": [
        "Load raw evidence",
        "Build evidence graph",
        "Run existing FIRE modules",
        "Assemble institutional report",
        "Evaluate report quality",
    ],
}
