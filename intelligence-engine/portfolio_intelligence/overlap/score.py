"""Overlap engine — candidate vs existing book."""

from __future__ import annotations

from typing import Any


def overlap_analysis(
    holdings: list[dict[str, Any]],
    *,
    candidate_ticker: str | None,
    candidate_sector: str | None,
) -> dict[str, Any]:
    tickers = {str(h.get("ticker")).upper() for h in holdings}
    t = (candidate_ticker or "").upper()
    already = t in tickers
    sector = candidate_sector or ""
    sector_w = sum(float(h.get("weight") or 0) for h in holdings if h.get("sector") == sector)
    same_sector_names = [h.get("ticker") for h in holdings if h.get("sector") == sector]

    return {
        "already_held": already,
        "candidate": t or None,
        "candidate_sector": sector or None,
        "sector_weight_ex_cash": round(sector_w, 4),
        "same_sector_holdings": same_sector_names,
        "overlap_flag": "name_duplicate"
        if already
        else "sector_cluster"
        if sector_w >= 0.20 and sector
        else "low",
    }
