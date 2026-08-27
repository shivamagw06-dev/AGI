"""Recommend charts when supporting data/structure exists — never invent series."""

from __future__ import annotations

from typing import Any


def recommend_charts(opinions: dict[str, dict[str, Any]], *, pack: dict[str, Any] | None = None) -> list[dict[str, str]]:
    recs: list[dict[str, str]] = []
    fin = (opinions or {}).get("financial") or {}
    fin_sec = fin.get("sections") if isinstance(fin.get("sections"), dict) else {}
    if fin_sec.get("revenue") not in (None, "", "n/a"):
        recs.append({"id": "revenue_trend", "title": "Revenue trend", "reason": "Financial file includes revenue context."})
    if fin_sec.get("margins") not in (None, "", "n/a"):
        recs.append({"id": "margin_trend", "title": "Margin trend", "reason": "Operating margin trajectory is part of the file."})
    if fin_sec.get("roe") not in (None, "", "n/a"):
        recs.append({"id": "roe_trend", "title": "ROE trend", "reason": "Return on equity is available for interpretation."})
    if fin_sec.get("cash_flow") not in (None, "", "n/a"):
        recs.append({"id": "cash_flow", "title": "Cash flow", "reason": "Cash conversion is a monitored financial variable."})

    val = (opinions or {}).get("valuation") or {}
    val_sec = val.get("sections") if isinstance(val.get("sections"), dict) else {}
    multiples = val_sec.get("current_multiples") if isinstance(val_sec.get("current_multiples"), dict) else {}
    if any(multiples.get(k) not in (None, "", "n/a") for k in ("pe", "pb", "forward_pe")):
        recs.append({"id": "valuation_history", "title": "Valuation history", "reason": "Current multiples support a history overlay."})

    mkt = (opinions or {}).get("market") or {}
    mkt_sec = mkt.get("sections") if isinstance(mkt.get("sections"), dict) else {}
    if mkt_sec.get("price_trend") or mkt_sec.get("range_52w"):
        recs.append({"id": "price_history", "title": "Price history", "reason": "Market tape context is present."})

    biz = (opinions or {}).get("business") or {}
    biz_sec = biz.get("sections") if isinstance(biz.get("sections"), dict) else {}
    if biz_sec.get("competitive_position") or biz_sec.get("competitive_advantages"):
        recs.append({"id": "market_share", "title": "Market share / competitive position", "reason": "Business competitive context is available."})

    # Deduplicate by id
    seen = set()
    out = []
    for r in recs:
        if r["id"] in seen:
            continue
        seen.add(r["id"])
        out.append(r)
    return out[:8]
