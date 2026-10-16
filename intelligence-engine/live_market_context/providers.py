"""Live quote provider abstraction — Groww primary, Yahoo failover, fail-closed."""

from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone
from typing import Any, Protocol

# Known index / seed symbols that may legitimately use index seeds
_INDEX_SYMBOLS = frozenset({"NIFTY", "BANKNIFTY", "SENSEX", "INDIAVIX"})
# Groww offline seed table LTP for NIFTY — must never attach to equities
_NIFTY_SEED_LTP = 24850.0


class QuoteProvider(Protocol):
    name: str

    def fetch_quote(self, ticker: str, *, force: bool = False) -> dict[str, Any]:
        ...


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _age_sec(as_of: Any) -> int | None:
    if as_of is None:
        return None
    if isinstance(as_of, str):
        try:
            as_of = datetime.fromisoformat(as_of.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(as_of, datetime):
        return None
    if as_of.tzinfo is None:
        as_of = as_of.replace(tzinfo=timezone.utc)
    return max(0, int((_utc_now() - as_of).total_seconds()))


def is_contaminated_index_seed(ticker: str, ltp: Any, *, source: str | None = None) -> bool:
    """Detect the Phase-1 failure mode: equity ticker receiving NIFTY seed LTP."""
    key = (ticker or "").upper()
    if key in _INDEX_SYMBOLS:
        return False
    try:
        price = float(ltp)
    except (TypeError, ValueError):
        return False
    if abs(price - _NIFTY_SEED_LTP) < 0.01:
        return True
    # Also reject when note/source admits seeded NIFTY fallback for non-index
    if source and "nifty" in str(source).lower() and key not in _INDEX_SYMBOLS:
        return True
    return False


class GrowwQuoteProvider:
    name = "groww"

    def fetch_quote(self, ticker: str, *, force: bool = False) -> dict[str, Any]:
        key = ticker.upper()
        try:
            from forecast_provider_integration.market_snapshot import ensure_fresh_market_snapshot

            pack = ensure_fresh_market_snapshot(key, scope="company", force=force)
            snap = pack.get("snapshot") or {}
            ltp = snap.get("ltp")
            note = str(snap.get("note") or "")
            contaminated = is_contaminated_index_seed(key, ltp) or (
                "seeded" in note.lower() and key not in _SEEDED_EQUITIES and key not in _INDEX_SYMBOLS and ltp is not None
                and abs(float(ltp) - _NIFTY_SEED_LTP) < 0.01
            )
            # Non-seeded unknown equity with NIFTY payload → fail closed
            if contaminated:
                return {
                    "ok": False,
                    "ticker": key,
                    "provider": self.name,
                    "ltp": None,
                    "error": "index_seed_rejected_for_equity",
                    "stale": True,
                    "lineage": [{"source": "groww", "ref": "seed_guard", "detail": note[:160]}],
                }
            # Seeded equity that is intentionally in the seed table is OK for offline
            return {
                "ok": ltp is not None,
                "ticker": key,
                "provider": self.name,
                "ltp": ltp,
                "change_pct": snap.get("change_pct"),
                "open": snap.get("open"),
                "high": snap.get("high"),
                "low": snap.get("low"),
                "close": snap.get("close"),
                "volume": snap.get("volume"),
                "vwap": snap.get("vwap"),
                "as_of": snap.get("as_of") or snap.get("published_at"),
                "age_sec": pack.get("age_sec"),
                "stale": bool(snap.get("stale")) or bool(pack.get("reason") == "snapshot_stale"),
                "market_status": snap.get("market_status"),
                "seeded": "seeded" in note.lower(),
                "refreshed": bool(pack.get("refreshed")),
                "lineage": [
                    {
                        "source": "groww",
                        "ref": pack.get("provider_called") or snap.get("source_provider") or "groww",
                        "retrieved_at": snap.get("as_of"),
                    }
                ],
                "raw_reason": pack.get("reason"),
            }
        except Exception as exc:
            return {
                "ok": False,
                "ticker": key,
                "provider": self.name,
                "ltp": None,
                "error": str(exc)[:200],
                "stale": True,
                "lineage": [{"source": "groww", "ref": "exception"}],
            }


# Equities that have intentional offline seeds in Groww gateway
_SEEDED_EQUITIES = frozenset({"INFY", "TCS", "HDFCBANK", "RELIANCE", "ITC"})


class YahooQuoteProvider:
    name = "yahoo"

    def fetch_quote(self, ticker: str, *, force: bool = False) -> dict[str, Any]:
        key = ticker.upper()
        # Prefer chart API for real LTP; degrade gracefully on failure
        chart = _yahoo_chart_ltp(key)
        if chart.get("ok"):
            return chart
        try:
            from forecast_provider_integration.gateways.yahoo import YahooFinancialGateway

            tip = YahooFinancialGateway().fallback_snapshot_fields(key)
            return {
                "ok": tip.get("ltp") is not None,
                "ticker": key,
                "provider": self.name,
                "ltp": tip.get("ltp"),
                "change_pct": tip.get("change_pct"),
                "as_of": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "stale": tip.get("ltp") is None,
                "seeded": False,
                "lineage": [{"source": "yahoo", "ref": "fallback_snapshot_fields"}],
                "error": None if tip.get("ltp") is not None else "yahoo_ltp_unavailable",
            }
        except Exception as exc:
            return {
                "ok": False,
                "ticker": key,
                "provider": self.name,
                "ltp": None,
                "error": str(exc)[:200],
                "stale": True,
                "lineage": [{"source": "yahoo", "ref": "exception"}],
            }


def _yahoo_chart_ltp(ticker: str) -> dict[str, Any]:
    if (os.environ.get("LMC_YAHOO_CHART") or "1").strip().lower() in {"0", "false", "no"}:
        return {"ok": False, "ticker": ticker, "provider": "yahoo", "ltp": None, "error": "yahoo_chart_disabled"}
    try:
        from app.market_data.providers.yahoo_symbols import to_yahoo_symbol

        symbol = to_yahoo_symbol(ticker)
    except Exception:
        symbol = f"{ticker.upper()}.NS"
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1d&range=5d"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AGIB-LiveMarketContext/1.0"})
        with urllib.request.urlopen(req, timeout=4.0) as resp:  # noqa: S310
            data = json.loads(resp.read().decode("utf-8"))
        result = (data.get("chart") or {}).get("result") or []
        if not result:
            return {"ok": False, "ticker": ticker, "provider": "yahoo", "ltp": None, "error": "yahoo_empty"}
        meta = result[0].get("meta") or {}
        ltp = meta.get("regularMarketPrice")
        # Relative strength vs 52w
        hi = meta.get("fiftyTwoWeekHigh")
        lo = meta.get("fiftyTwoWeekLow")
        rs = None
        if ltp is not None and hi and lo and float(hi) != float(lo):
            rs = round((float(ltp) - float(lo)) / (float(hi) - float(lo)), 4)
        ts = meta.get("regularMarketTime")
        as_of = (
            datetime.fromtimestamp(int(ts), tz=timezone.utc).isoformat().replace("+00:00", "Z")
            if ts
            else datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        )
        return {
            "ok": ltp is not None,
            "ticker": ticker.upper(),
            "provider": "yahoo",
            "ltp": ltp,
            "currency": meta.get("currency"),
            "fifty_two_week_high": hi,
            "fifty_two_week_low": lo,
            "relative_strength_52w": rs,
            "volume": meta.get("regularMarketVolume"),
            "as_of": as_of,
            "age_sec": _age_sec(as_of),
            "stale": False,
            "seeded": False,
            "lineage": [{"source": "yahoo_chart", "ref": symbol, "retrieved_at": as_of}],
        }
    except Exception as exc:
        return {
            "ok": False,
            "ticker": ticker.upper(),
            "provider": "yahoo",
            "ltp": None,
            "error": str(exc)[:200],
            "stale": True,
            "lineage": [{"source": "yahoo_chart", "ref": "exception"}],
        }


def fetch_best_quote(ticker: str, *, force: bool = False) -> dict[str, Any]:
    """Groww → Yahoo chain; fail closed if no honest equity quote."""
    key = ticker.upper()
    groww = GrowwQuoteProvider().fetch_quote(key, force=force)
    if groww.get("ok") and groww.get("ltp") is not None and not is_contaminated_index_seed(key, groww.get("ltp")):
        # Prefer Yahoo enrichment for RS/52w when Groww is seeded offline for known names
        if groww.get("seeded") and key not in _INDEX_SYMBOLS:
            yahoo = YahooQuoteProvider().fetch_quote(key, force=force)
            if yahoo.get("ok") and yahoo.get("ltp") is not None:
                merged = {**groww, **{k: v for k, v in yahoo.items() if v is not None and k != "lineage"}}
                merged["provider"] = "yahoo"
                merged["failover_from"] = "groww_seeded"
                merged["lineage"] = list(groww.get("lineage") or []) + list(yahoo.get("lineage") or [])
                merged["ok"] = True
                return merged
        return groww

    yahoo = YahooQuoteProvider().fetch_quote(key, force=force)
    if yahoo.get("ok") and yahoo.get("ltp") is not None:
        yahoo["failover_from"] = groww.get("error") or "groww_unavailable"
        yahoo["lineage"] = list(groww.get("lineage") or []) + list(yahoo.get("lineage") or [])
        return yahoo

    return {
        "ok": False,
        "ticker": key,
        "provider": None,
        "ltp": None,
        "stale": True,
        "error": groww.get("error") or yahoo.get("error") or "quote_unavailable",
        "lineage": list(groww.get("lineage") or []) + list(yahoo.get("lineage") or []),
        "fail_closed": True,
    }
