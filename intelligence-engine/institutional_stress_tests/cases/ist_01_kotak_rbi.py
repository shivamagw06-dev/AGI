"""IST-01 — Kotak Mahindra Bank post-RBI restrictions (April 2024).

Deliberately difficult: no obvious Buy/Don't Buy. Forces full-stack orchestration.
"""

from __future__ import annotations

from institutional_stress_tests.schema import (
    FINAL_VIEW_KEYS,
    IST01_CASE_ID,
    IST01_SPEC,
    IST01_WORKSTREAM_ID,
    OPTIONAL_MODULES,
    REQUIRED_MODULES,
    REQUIRED_QUESTIONS,
    RUBRIC_WEIGHTS,
)

IST_01_CASE = {
    "case_id": IST01_CASE_ID,
    "workstream_id": IST01_WORKSTREAM_ID,
    "title": "Kotak Mahindra Bank — RBI restrictions (April 2024)",
    "spec": IST01_SPEC,
    "question": (
        "Should an Indian institutional investor have bought Kotak Mahindra Bank "
        "immediately after the RBI restrictions (April 2024), or waited?"
    ),
    "primary_ticker": "KOTAKBANK",
    "peer_tickers": ("HDFCBANK", "ICICIBANK", "AXISBANK"),
    "event": {
        "name": "RBI business restrictions on Kotak Mahindra Bank",
        "anchor_period": "2024-04",
        "jurisdiction": "India",
        "regulator": "RBI",
    },
    "difficulty": "hard",
    "no_obvious_answer": True,
    "forbids_simple_verdict": True,
    "required_modules": list(REQUIRED_MODULES),
    "optional_modules": list(OPTIONAL_MODULES),
    "required_questions": [dict(q) for q in REQUIRED_QUESTIONS],
    "final_view_keys": list(FINAL_VIEW_KEYS),
    "rubric_weights": dict(RUBRIC_WEIGHTS),
    "layer_contributions": {
        "FSE": "Financial statements before/after RBI action",
        "FIL": "Regulatory filings and disclosures",
        "FIRE-01": "What changed financially?",
        "FIRE-02": "Which drivers changed?",
        "FIRE-03": "Management explanations",
        "FIRE-04": "Did management explanations match financial evidence?",
        "FIRE-05": "Did management execute on promised remediation?",
        "FIRE-06": "Did business quality improve or deteriorate?",
        "CIO-01": "Compare Kotak with HDFC, ICICI, Axis",
        "PO-01": "(Optional) Portfolio exposure implications",
        "WO-01": "Monitoring timeline",
        "AskAGI": "Produce final institutional answer",
        "CW-01": "Company workspace assembly surface",
        "IO-01": "Institutional research package orchestration",
    },
    "gold_standard": {
        "style": [
            "Goldman Sachs Equity Research",
            "Morgan Stanley Research",
            "Bain Capital investment committee",
            "Capital Group internal memo",
        ],
        "must_not_sound_like": ["chatbot", "blog post"],
        "must": [
            "trace every conclusion to evidence",
            "distinguish facts from interpretations",
            "surface counterarguments",
            "identify what still needs monitoring",
        ],
        "final_view_shape": list(FINAL_VIEW_KEYS),
        "not_buy_sell": True,
    },
    "automatic_failures": [
        "Says Buy/Sell without evidence",
        "Ignores contradictory evidence",
        "Hallucinates facts",
        "Uses outside info without identifying it",
        "Loses provenance",
        "Mixes opinions with facts",
        "Doesn't identify unknowns",
        "Passes with only one module contributing",
    ],
}
