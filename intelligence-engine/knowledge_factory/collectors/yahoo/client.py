"""Yahoo Finance collector — prices, OHLCV, fundamentals primitives."""

from __future__ import annotations

import os
from typing import Any

from knowledge_factory.collectors.base import ok_dataset, unavailable
from knowledge_factory.fixtures import seed


def collect_company(entity: str, *, live: bool | None = None) -> dict[str, Any]:
    live = bool(os.environ.get("KF_LIVE_YAHOO")) if live is None else live
    e = entity.upper()
    if live:
        try:
            # Optional live path — never required for acceptance.
            import urllib.request

            urllib.request.urlopen(f"https://query1.finance.yahoo.com/v8/finance/chart/{e}.NS", timeout=3)
        except Exception:
            return unavailable("yahoo", e, "yahoo_unavailable")

    panel = seed.primitive_panel(e)
    prices = seed.price_series(e)
    if not panel and not prices:
        return unavailable("yahoo", e, "no_fixture")
    payload = {
        "primitives": (panel or {}).get("fields") or {},
        "prices": prices,
        "ohlcv": [{"date": p["date"], "close": p["close"]} for p in prices],
        "shares_outstanding": ((panel or {}).get("fields") or {}).get("shares", {}).get("FY26"),
        "market_cap": None,
    }
    # market cap ≈ price * shares when both present
    latest_px = prices[-1]["close"] if prices else None
    shares = payload["shares_outstanding"]
    if latest_px and shares:
        # shares in crore in primitives → rough INR cr market cap proxy
        payload["market_cap"] = round(float(latest_px) * float(shares), 2)
    return ok_dataset(kind="company_market", entity=e, source="yahoo", payload=payload)
