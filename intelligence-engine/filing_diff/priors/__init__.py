from __future__ import annotations

from typing import Any

from filing_diff.priors.hdfc_q4fy26 import prior_snapshot as hdfc_prior


def prior_for(ticker: str) -> dict[str, Any] | None:
    t = ticker.upper().replace(".NS", "").replace(".BO", "")
    if t in {"HDFC", "HDFCBANK"}:
        return hdfc_prior()
    return None
