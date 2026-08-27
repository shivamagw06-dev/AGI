"""Deterministic verification filing payloads (JSON financial packs).

These are *real* FSE-ingestible documents (document_type=json) used to prove the
production pipeline without live NSE downloads. They do not change parser logic.
"""

from __future__ import annotations

import json
from typing import Any


def verification_filing_bytes(*, ticker: str, period_end: str = "2025-03-31") -> bytes:
    """Rich balanced pack that passes parse → validate → warehouse → DME."""
    # Slight per-ticker variance so document hashes differ across universe.
    seed = sum(ord(c) for c in ticker.upper()) % 17
    rev = 100.0 + seed
    pat = 20.0 + (seed % 5)
    assets = 200.0 + seed
    equity = 120.0 + (seed % 7)
    liabilities = assets - equity
    pack = {
        "ticker": ticker.upper(),
        "period_end": period_end,
        "period_type": "annual",
        "fields": {
            "Revenue From Operations": {"value": rev, "unit_scale": "crores"},
            "PAT": {"value": pat, "unit_scale": "crores"},
            "PBT": {"value": pat + 8.0, "unit_scale": "crores"},
            "TaxExpense": {"value": 8.0, "unit_scale": "crores"},
            "Finance Costs": {"value": 2.0, "unit_scale": "crores"},
            "CashAndCashEquivalents": {"value": 30.0 + seed, "unit_scale": "crores"},
            "TotalAssets": {"value": assets, "unit_scale": "crores"},
            "TotalEquity": {"value": equity, "unit_scale": "crores"},
            "TotalLiabilities": {"value": liabilities, "unit_scale": "crores"},
            "CurrentAssets": {"value": 90.0, "unit_scale": "crores"},
            "NonCurrentAssets": {"value": assets - 90.0, "unit_scale": "crores"},
            "CurrentLiabilities": {"value": round(liabilities / 2, 2), "unit_scale": "crores"},
            "NonCurrentLiabilities": {"value": round(liabilities / 2, 2), "unit_scale": "crores"},
            "NetCashFlowsFromUsedInOperatingActivities": {"value": 25.0, "unit_scale": "crores"},
            "CashFlowsFromUsedInInvestingActivities": {"value": -10.0, "unit_scale": "crores"},
            "CashFlowsFromUsedInFinancingActivities": {"value": -5.0, "unit_scale": "crores"},
            "IncreaseDecreaseInCashAndCashEquivalents": {"value": 10.0, "unit_scale": "crores"},
            "EBIT": {"value": pat + 10.0, "unit_scale": "crores"},
            "Inventory": {"value": 10.0, "unit_scale": "crores"},
            "TotalDebt": {"value": 40.0, "unit_scale": "crores"},
            "Capex": {"value": 5.0, "unit_scale": "crores"},
        },
    }
    return json.dumps(pack, sort_keys=True).encode("utf-8")


def filing_meta(ticker: str, *, period_end: str = "2025-03-31") -> dict[str, Any]:
    return {
        "ticker": ticker.upper().strip(),
        "period_end": period_end,
        "period_type": "annual",
        "filing_type": "annual",
        "document_type": "json",
        "source": "fse_02_2_verification_fixture",
    }
