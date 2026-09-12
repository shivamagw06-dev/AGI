"""Groww gateway — primary live Indian market data (Knowledge Platform side).

Forecast Intelligence must not import this module for reasoning.
Only the controlled market-snapshot refresh path may invoke it.
"""

from __future__ import annotations

import os
import time
from typing import Any

from forecast_provider_integration.schema import MarketSnapshot, utc_now

# Deterministic seeded LTPs for offline / unconfigured environments
_SEEDED: dict[str, dict[str, Any]] = {
    "INFY": {
        "ltp": 1582.4,
        "change_pct": 0.85,
        "open": 1570.0,
        "high": 1591.0,
        "low": 1565.5,
        "close": 1569.0,
        "volume": 4_250_000,
        "vwap": 1578.2,
        "bid": 1582.0,
        "ask": 1582.6,
        "market_depth": {"bids": 5, "asks": 5},
    },
    "TCS": {
        "ltp": 3925.0,
        "change_pct": 0.42,
        "open": 3910.0,
        "high": 3940.0,
        "low": 3902.0,
        "close": 3908.5,
        "volume": 2_100_000,
        "vwap": 3920.1,
        "bid": 3924.5,
        "ask": 3925.5,
        "market_depth": {"bids": 5, "asks": 5},
    },
    "HDFCBANK": {
        "ltp": 1688.0,
        "change_pct": 1.15,
        "open": 1670.0,
        "high": 1695.0,
        "low": 1668.0,
        "close": 1668.8,
        "volume": 6_800_000,
        "vwap": 1682.0,
        "bid": 1687.5,
        "ask": 1688.2,
        "market_depth": {"bids": 5, "asks": 5},
    },
    "RELIANCE": {
        "ltp": 2920.0,
        "change_pct": -0.55,
        "open": 2940.0,
        "high": 2948.0,
        "low": 2912.0,
        "close": 2936.0,
        "volume": 5_500_000,
        "vwap": 2928.0,
        "bid": 2919.5,
        "ask": 2920.5,
        "market_depth": {"bids": 5, "asks": 5},
    },
    "NIFTY": {
        "ltp": 24850.0,
        "change_pct": 0.35,
        "open": 24780.0,
        "high": 24890.0,
        "low": 24760.0,
        "close": 24762.0,
        "volume": None,
        "vwap": None,
        "bid": None,
        "ask": None,
        "market_depth": {},
        "index_move_pct": 0.35,
    },
    "ITC": {
        "ltp": 468.5,
        "change_pct": 0.22,
        "open": 467.0,
        "high": 470.0,
        "low": 466.2,
        "close": 467.5,
        "volume": 8_000_000,
        "vwap": 468.0,
        "bid": 468.4,
        "ask": 468.6,
        "market_depth": {"bids": 4, "asks": 4},
    },
}


def _configured() -> bool:
    return bool(
        (os.environ.get("GROWW_ACCESS_TOKEN") or "").strip()
        or (os.environ.get("GROWW_API_KEY") or "").strip()
    )


def _market_status() -> str:
    # Soft institutional clock — tests don't depend on real IST hours
    force = (os.environ.get("FPI_MARKET_STATUS") or "").strip().lower()
    if force in {"open", "closed", "pre", "post"}:
        return force
    return "open" if _configured() else "seeded"


class GrowwMarketGateway:
    """Primary live market provider for India."""

    provider = "groww"
    supports_websocket = True

    def health(self) -> dict[str, Any]:
        configured = _configured()
        return {
            "provider": self.provider,
            "configured": configured,
            "connection": "ready" if configured else "seeded_offline",
            "websocket": self.supports_websocket,
            "role": "primary_live_market",
            "status": "healthy" if configured else "degraded",
            "detail": (
                "Groww credentials present — live REST/WS path available via Node/collector"
                if configured
                else "Using AGI seeded Groww-shaped snapshots (no uncontrolled live calls)"
            ),
        }

    def fetch_snapshot(self, entity: str, *, scope: str = "company") -> MarketSnapshot:
        """Return a market snapshot. Prefer seeded AGI knowledge; soft-live only if forced.

        Fail-closed for unknown equities: never attach the NIFTY seed LTP to a
        non-index ticker (Phase 2.1 / P2.6 honesty rule).
        """
        key = entity.upper()
        t0 = time.perf_counter()
        live_forced = (os.environ.get("FPI_GROWW_LIVE") or "").strip() in {"1", "true", "yes"}
        used_live = False
        index_symbols = {"NIFTY", "BANKNIFTY", "SENSEX", "INDIAVIX"}
        seeded = _SEEDED.get(key)
        if seeded is not None:
            payload = dict(seeded)
            missing_equity_seed = False
        elif key in index_symbols:
            payload = dict(_SEEDED.get("NIFTY") or {})
            missing_equity_seed = False
        else:
            # Unknown equity — do NOT fall back to NIFTY LTP
            payload = {}
            missing_equity_seed = True

        if live_forced and _configured():
            # Soft attempt via Agib Node ticker — never raise into forecast path
            try:
                live = self._soft_node_ticker(key)
                if live and live.get("ltp") is not None:
                    payload = {**payload, **live}
                    used_live = True
                    missing_equity_seed = False
            except Exception:
                used_live = False

        latency = round((time.perf_counter() - t0) * 1000, 2)
        now = utc_now()
        ltp = payload.get("ltp")
        # Fail closed: no honest quote available
        no_quote = ltp is None and missing_equity_seed and not used_live
        return MarketSnapshot(
            entity=key,
            scope=scope if key != "NIFTY" else "market",
            ltp=ltp,
            change_pct=payload.get("change_pct"),
            open=payload.get("open"),
            high=payload.get("high"),
            low=payload.get("low"),
            close=payload.get("close"),
            volume=payload.get("volume"),
            vwap=payload.get("vwap"),
            bid=payload.get("bid"),
            ask=payload.get("ask"),
            market_depth=dict(payload.get("market_depth") or {}),
            index_move_pct=payload.get("index_move_pct") or payload.get("change_pct"),
            market_status=_market_status(),
            source_provider="groww",
            fallback_used=False,
            published_at=now,
            as_of=now,
            freshness_sec=0,
            stale=bool(no_quote),
            websocket=bool(used_live and self.supports_websocket),
            note=(
                "Live Groww refresh via controlled gateway"
                if used_live
                else (
                    "No Groww seed for equity — fail closed (no NIFTY LTP attach)"
                    if no_quote
                    else "AGI seeded Groww-shaped market snapshot"
                )
            ),
        )

    def _soft_node_ticker(self, symbol: str) -> dict[str, Any] | None:
        """Optional soft call to Node Groww ticker — Knowledge Platform only."""
        base = (os.environ.get("AGIB_NODE_BASE_URL") or os.environ.get("AGI_NODE_URL") or "").rstrip("/")
        if not base:
            return None
        try:
            import urllib.request
            import json

            url = f"{base}/api/market/ticker"
            with urllib.request.urlopen(url, timeout=2.5) as resp:  # noqa: S310
                data = json.loads(resp.read().decode("utf-8"))
            # Best-effort extract
            rows = data.get("indices") or data.get("stocks") or data.get("ticker") or []
            if isinstance(rows, dict):
                row = rows.get(symbol) or rows.get(symbol.upper())
                if isinstance(row, dict):
                    return {
                        "ltp": row.get("ltp") or row.get("last_price"),
                        "change_pct": row.get("change_pct") or row.get("day_change_perc"),
                        "volume": row.get("volume"),
                    }
            return None
        except Exception:
            return None
