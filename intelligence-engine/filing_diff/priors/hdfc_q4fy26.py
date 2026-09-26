"""FDI prior-period qualitative snapshot for HDFC Q4FY26.

Not a FIL redesign — FDI-local prior context used when FIL corpus has
richer current-period docs than prior-period qualitative extracts.
"""

from __future__ import annotations

from typing import Any

PRIOR = {
    "ticker": "HDFCBANK",
    "period": "Q4FY26",
    "as_of": "2026-04-20",
    "doc_id": "fdi_prior_hdfc_q4fy26",
    "evidence_tier": 2,
    "financials": {
        "NIM": 3.40,
        "CASA": 33.5,
        "CET1": 17.5,
        "ROE": 14.0,
        "GNPA": 1.18,
        "Deposits_YoY": 15.0,
    },
    "guidance_status": "maintained",
    "management": {
        "Key_Priorities": "Rebuild liability franchise; calibrate loan growth; preserve CET1 buffer",
        "Margin_Commentary": "NIM near prior-quarter levels; deposit costs elevated but manageable",
        "Growth_Drivers": "Granular deposits and retail loan growth",
        "outlook_tone": "constructive",
    },
    "risks": [
        "Financial_Risk",
        "Competition_Risk",
        "Execution_Risk",
    ],
    "notes": ["Goodwill"],
    "capital": ["Capital_Buffer", "Organic_Investment", "Dividends"],
    "segments": ["retail", "wholesale", "treasury"],
    "governance": ["Dividend_Policy"],
    "ownership": [],
    "text_markers": {
        "optimism": "constructive",
        "warnings": ["deposit costs elevated"],
    },
}


def prior_snapshot() -> dict[str, Any]:
    return dict(PRIOR)
