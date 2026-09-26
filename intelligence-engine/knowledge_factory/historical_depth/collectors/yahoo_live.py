"""Live Yahoo chart → Historical Depth series (prices, actions, thin financials).

Sync HTTP — no Ask path. Used by KF HD collectors when KF_HD_LIVE_COLLECTORS is on.
Never overwrites existing PIT records (store.put_series append-merges).
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from knowledge_factory.historical_depth import store as hd_store
from knowledge_factory.historical_depth.schema import pit_record
from live_data.qa import qa_price_points

YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
UA = "Mozilla/5.0 (compatible; AGIB-KF-HD/1.0)"


def live_enabled() -> bool:
    return str(os.getenv("KF_HD_LIVE_COLLECTORS", "false")).strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def to_yahoo_symbol(symbol: str) -> str:
    s = str(symbol or "").upper().strip()
    if not s:
        return s
    if s.endswith(".NS") or s.endswith(".BO"):
        return s
    # Default NSE listing for Indian equities in AGIB universe
    return f"{s}.NS"


def collect_entity_live(entity: str, *, sleep_s: float = 0.35) -> dict[str, Any]:
    """Fetch max history for one entity; write into HD store; return coverage stats."""
    e = entity.upper()
    ysym = to_yahoo_symbol(e)
    t0 = time.time()
    errors: list[str] = []
    price_n = 0
    action_n = 0
    annual_n = 0

    try:
        chart = _fetch_chart(ysym, range_="max", interval="1mo")
        prices = _prices_from_chart(chart, entity=e)
        if prices:
            hd_store.put_series("prices", e, prices)
            price_n = len(prices)
        actions = _actions_from_chart(chart, entity=e)
        if actions:
            hd_store.put_series("corporate_actions", e, actions)
            action_n = len(actions)
        # Derive thin annual close proxies from monthly prices (fills years KPI)
        annual = _annual_from_prices(prices, entity=e)
        if annual:
            hd_store.put_series("financials_annual", e, annual)
            annual_n = len(annual)
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc)[:200])

    if sleep_s > 0:
        time.sleep(sleep_s)

    series = hd_store.get_series("prices", e) or {}
    qa = qa_price_points(list(series.get("records") or []))

    years = _years_span(series)
    return {
        "entity": e,
        "yahoo_symbol": ysym,
        "price_points": price_n or len(series.get("records") or []),
        "corporate_actions": action_n,
        "annual_periods": annual_n,
        "history_years": years,
        "qa": qa,
        "errors": errors,
        "latency_ms": int((time.time() - t0) * 1000),
        "status": "ok" if not errors and (price_n or annual_n) else ("degraded" if price_n or annual_n else "error"),
        "source": "yahoo_live",
    }


def _fetch_chart(ysym: str, *, range_: str = "max", interval: str = "1mo") -> dict[str, Any]:
    params = urlencode({"range": range_, "interval": interval, "events": "div|split", "includeAdjustedClose": "true"})
    url = f"{YAHOO_CHART.format(symbol=ysym)}?{params}"
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urlopen(req, timeout=40) as resp:  # noqa: S310 — public market data
            raw = resp.read()
    except HTTPError as exc:
        raise RuntimeError(f"yahoo_http_{exc.code}") from exc
    except URLError as exc:
        raise RuntimeError(f"yahoo_url:{exc.reason}") from exc
    payload = json.loads(raw.decode("utf-8"))
    err = (payload.get("chart") or {}).get("error")
    if err:
        raise RuntimeError(f"yahoo_chart_error:{err}")
    return payload


def _prices_from_chart(payload: dict[str, Any], *, entity: str) -> list[dict[str, Any]]:
    chart = ((payload.get("chart") or {}).get("result") or [None])[0] or {}
    timestamps = chart.get("timestamp") or []
    quote = ((chart.get("indicators") or {}).get("quote") or [{}])[0] or {}
    adj = ((chart.get("indicators") or {}).get("adjclose") or [{}])[0] or {}
    records: list[dict[str, Any]] = []
    for i, ts in enumerate(timestamps):
        try:
            dt = datetime.fromtimestamp(int(ts), tz=timezone.utc).date()
        except Exception:
            continue
        close = _num((quote.get("close") or [None])[i] if i < len(quote.get("close") or []) else None)
        adj_c = _num((adj.get("adjclose") or [None])[i] if i < len(adj.get("adjclose") or []) else None)
        o = _num((quote.get("open") or [None])[i] if i < len(quote.get("open") or []) else None)
        h = _num((quote.get("high") or [None])[i] if i < len(quote.get("high") or []) else None)
        l = _num((quote.get("low") or [None])[i] if i < len(quote.get("low") or []) else None)
        v = _num((quote.get("volume") or [None])[i] if i < len(quote.get("volume") or []) else None)
        px = adj_c if adj_c is not None else close
        if px is None:
            continue
        period = f"{dt.year}-{dt.month:02d}"
        period_end = dt.isoformat()
        records.append(
            pit_record(
                entity=entity,
                kind="price_monthly",
                period=period,
                period_end=period_end,
                available_from=period_end,
                payload={
                    "price": px,
                    "close": close,
                    "adj_close": adj_c,
                    "open": o,
                    "high": h,
                    "low": l,
                    "volume": v,
                },
                source="yahoo_live",
                confidence=0.88,
            )
        )
    return records


def _actions_from_chart(payload: dict[str, Any], *, entity: str) -> list[dict[str, Any]]:
    chart = ((payload.get("chart") or {}).get("result") or [None])[0] or {}
    events = chart.get("events") or {}
    out: list[dict[str, Any]] = []
    for ts, row in (events.get("dividends") or {}).items():
        if not isinstance(row, dict):
            continue
        try:
            d = datetime.fromtimestamp(int(row.get("date") or ts), tz=timezone.utc).date().isoformat()
        except Exception:
            continue
        out.append(
            pit_record(
                entity=entity,
                kind="dividend",
                period=d,
                period_end=d,
                available_from=d,
                payload={"action_type": "dividend", "amount": _num(row.get("amount")), "ex_date": d},
                source="yahoo_live",
            )
        )
    for ts, row in (events.get("splits") or {}).items():
        if not isinstance(row, dict):
            continue
        try:
            d = datetime.fromtimestamp(int(row.get("date") or ts), tz=timezone.utc).date().isoformat()
        except Exception:
            continue
        numer = _num(row.get("numerator"))
        denom = _num(row.get("denominator"))
        out.append(
            pit_record(
                entity=entity,
                kind="split",
                period=d,
                period_end=d,
                available_from=d,
                payload={
                    "action_type": "split",
                    "numerator": numer,
                    "denominator": denom,
                    "ratio": (numer / denom) if numer and denom else None,
                    "ex_date": d,
                },
                source="yahoo_live",
            )
        )
    return out


def _annual_from_prices(prices: list[dict[str, Any]], *, entity: str) -> list[dict[str, Any]]:
    """Year-end price proxy rows so coverage years grow from live OHLCV.

    Full fundamentals still come from FAA/Yahoo quoteSummary when available;
    this ensures Historical Depth years/completeness are not stuck at fixtures.
    """
    by_year: dict[int, dict[str, Any]] = {}
    for r in prices:
        pe = str(r.get("period_end") or "")
        if len(pe) < 4:
            continue
        try:
            y = int(pe[:4])
        except ValueError:
            continue
        # Prefer latest month in calendar year
        prev = by_year.get(y)
        if prev is None or str(r.get("period_end")) >= str(prev.get("period_end")):
            by_year[y] = r
    records = []
    for y in sorted(by_year):
        r = by_year[y]
        payload = dict(r.get("payload") or {})
        fy = f"FY{str(y)[-2:]}"
        period_end = f"{y}-03-31" if y else str(r.get("period_end"))
        # India FY ends Mar — map calendar year-end close into FY label of that year
        records.append(
            pit_record(
                entity=entity,
                kind="financials_annual",
                period=fy,
                period_end=period_end,
                available_from=str(r.get("period_end") or period_end),
                payload={"price": payload.get("price") or payload.get("close")},
                source="yahoo_live_price_proxy",
                confidence=0.7,
            )
        )
    return records


def _years_span(series: dict[str, Any]) -> float:
    records = list(series.get("records") or [])
    if not records:
        return 0.0
    ends = [str(r.get("period_end") or r.get("period") or "")[:10] for r in records]
    ends = [e for e in ends if len(e) >= 4]
    if not ends:
        return 0.0
    try:
        d0 = datetime.fromisoformat(min(ends))
        d1 = datetime.fromisoformat(max(ends))
        return round(max(0.0, (d1 - d0).days / 365.25), 2)
    except Exception:
        years = {e[:4] for e in ends}
        return float(max(0, len(years) - 1))


def _num(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None
