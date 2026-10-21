"""Yahoo historical loader — decades of daily prices, dividends, splits and statements.

Worker-only. Ask must never trigger this: a universe pass is thousands of HTTP
calls. The fetcher is injectable so the engine is testable without the network,
and the parsing is deliberately separate from the transport so a recorded
payload exercises exactly the code that runs in production.

Two transports, tried in order:
  1. the chart API over stdlib http (no dependency, returns everything we need)
  2. yfinance, when installed, for statements the chart API does not carry
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from institutional_warehouse.values import to_number

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
USER_AGENT = "Mozilla/5.0 (compatible; AGIB-Backfill/1.0)"
SOURCE = "yahoo_finance_history"

# NSE tickers carry a suffix on Yahoo; a few names only resolve on BSE.
SUFFIXES = (".NS", ".BO")


def yahoo_symbols(symbol: str) -> list[str]:
    ticker = str(symbol or "").strip().upper()
    if not ticker:
        return []
    if "." in ticker:
        return [ticker]
    return [f"{ticker}{suffix}" for suffix in SUFFIXES]


def _http_get(url: str, *, timeout: int = 30) -> bytes:
    import urllib.request

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def chart_url(symbol: str, *, range_: str = "max", interval: str = "1d") -> str:
    return (
        f"{CHART_URL.format(symbol=symbol)}"
        f"?range={range_}&interval={interval}&events=div%2Csplit&includeAdjustedClose=true"
    )


def parse_chart(payload: dict[str, Any], *, symbol: str) -> dict[str, Any]:
    """Yahoo chart JSON into warehouse rows. Pure: no network, no clock."""
    result = (((payload or {}).get("chart") or {}).get("result") or [None])[0]
    if not result:
        error = ((payload or {}).get("chart") or {}).get("error")
        return {"ok": False, "symbol": symbol, "error": str(error or "no_result")[:200],
                "prices": [], "dividends": [], "splits": []}

    stamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0] or {}
    adj = (((result.get("indicators") or {}).get("adjclose") or [{}])[0] or {}).get("adjclose") or []
    opens, highs = quote.get("open") or [], quote.get("high") or []
    lows, closes = quote.get("low") or [], quote.get("close") or []
    volumes = quote.get("volume") or []

    def _at(series: list[Any], index: int) -> Any:
        return series[index] if index < len(series) else None

    prices: list[dict[str, Any]] = []
    for index, stamp in enumerate(stamps):
        close = to_number(_at(closes, index))
        if close is None:
            continue
        prices.append(
            {
                "date": datetime.fromtimestamp(int(stamp), tz=timezone.utc).date().isoformat(),
                "open": to_number(_at(opens, index)),
                "high": to_number(_at(highs, index)),
                "low": to_number(_at(lows, index)),
                "close": close,
                "adjusted_close": to_number(_at(adj, index)),
                "volume": to_number(_at(volumes, index)),
            }
        )

    events = result.get("events") or {}
    dividends = [
        {
            "date": datetime.fromtimestamp(int(item.get("date")), tz=timezone.utc).date().isoformat(),
            "amount": to_number(item.get("amount")),
        }
        for item in (events.get("dividends") or {}).values()
        if item.get("date") is not None
    ]
    splits = [
        {
            "date": datetime.fromtimestamp(int(item.get("date")), tz=timezone.utc).date().isoformat(),
            "ratio": str(item.get("splitRatio") or "").strip() or None,
            "numerator": to_number(item.get("numerator")),
            "denominator": to_number(item.get("denominator")),
        }
        for item in (events.get("splits") or {}).values()
        if item.get("date") is not None
    ]

    meta = result.get("meta") or {}
    return {
        "ok": bool(prices),
        "symbol": symbol,
        "yahoo_symbol": meta.get("symbol") or symbol,
        "currency": meta.get("currency"),
        "prices": sorted(prices, key=lambda r: r["date"]),
        "dividends": sorted(dividends, key=lambda r: r["date"]),
        "splits": sorted(splits, key=lambda r: r["date"]),
        "first": prices[0]["date"] if prices else None,
        "last": prices[-1]["date"] if prices else None,
    }


def fetch_history(
    symbol: str,
    *,
    range_: str = "max",
    interval: str = "1d",
    fetch: Optional[Callable[[str], bytes]] = None,
    pause_seconds: float = 0.0,
) -> dict[str, Any]:
    """Full available daily history for one company."""
    getter = fetch or _http_get
    errors: list[str] = []
    for candidate in yahoo_symbols(symbol):
        url = chart_url(candidate, range_=range_, interval=interval)
        try:
            raw = getter(url)
        except Exception as exc:
            errors.append(f"{candidate}:{type(exc).__name__}")
            continue
        try:
            payload = json.loads(raw.decode("utf-8") if isinstance(raw, bytes) else raw)
        except Exception as exc:
            errors.append(f"{candidate}:bad_json:{type(exc).__name__}")
            continue
        parsed = parse_chart(payload, symbol=symbol)
        if parsed.get("ok"):
            if pause_seconds:
                time.sleep(pause_seconds)
            return parsed
        errors.append(f"{candidate}:{parsed.get('error') or 'empty'}")
        if pause_seconds:
            time.sleep(pause_seconds)
    return {"ok": False, "symbol": symbol, "error": "; ".join(errors)[:300],
            "prices": [], "dividends": [], "splits": []}


# --------------------------------------------------------------------------
# Statements
# --------------------------------------------------------------------------

# Yahoo's statement labels vary by company and by API version; map generously.
_STATEMENT_FIELDS: dict[str, tuple[str, ...]] = {
    "revenue": ("Total Revenue", "TotalRevenue", "OperatingRevenue"),
    "gross_profit": ("Gross Profit", "GrossProfit"),
    "ebitda": ("EBITDA", "NormalizedEBITDA"),
    "ebit": ("EBIT", "OperatingIncome", "Operating Income"),
    "pbt": ("Pretax Income", "PretaxIncome"),
    "pat": ("Net Income", "NetIncome", "NetIncomeCommonStockholders"),
    "eps": ("Diluted EPS", "DilutedEPS", "BasicEPS"),
    "assets": ("Total Assets", "TotalAssets"),
    "equity": ("Stockholders Equity", "StockholdersEquity", "TotalEquityGrossMinorityInterest"),
    "debt": ("Total Debt", "TotalDebt"),
    "cash": ("Cash And Cash Equivalents", "CashAndCashEquivalents", "CashCashEquivalentsAndShortTermInvestments"),
    "current_assets": ("Current Assets", "CurrentAssets", "TotalCurrentAssets"),
    "current_liabilities": ("Current Liabilities", "CurrentLiabilities", "TotalCurrentLiabilities"),
    "inventory": ("Inventory", "Inventories"),
    "working_capital": ("Working Capital", "WorkingCapital"),
    "capex": ("Capital Expenditure", "CapitalExpenditure"),
    "cfo": ("Operating Cash Flow", "OperatingCashFlow", "CashFlowFromContinuingOperatingActivities"),
    "cfi": ("Investing Cash Flow", "InvestingCashFlow", "CashFlowFromContinuingInvestingActivities"),
    "cff": ("Financing Cash Flow", "FinancingCashFlow", "CashFlowFromContinuingFinancingActivities"),
    "free_cash_flow": ("Free Cash Flow", "FreeCashFlow"),
    "shares_outstanding": ("Ordinary Shares Number", "ShareIssued", "BasicAverageShares"),
}


def map_statement_frame(frame: Any, *, quarterly: bool) -> list[dict[str, Any]]:
    """A yfinance statement DataFrame into raw period rows. No derived metrics."""
    if frame is None or getattr(frame, "empty", True):
        return []
    labels = {str(idx).strip(): idx for idx in frame.index}
    periods: list[dict[str, Any]] = []
    for column in frame.columns:
        stamp = getattr(column, "date", lambda: column)()
        period_end = stamp.isoformat() if hasattr(stamp, "isoformat") else str(column)[:10]
        row: dict[str, Any] = {"period_end": period_end}
        for field, candidates in _STATEMENT_FIELDS.items():
            for label in candidates:
                if label in labels:
                    value = frame.loc[labels[label], column]
                    number = to_number(value)
                    if number is not None:
                        row[field] = number
                        break
        if len(row) > 1:
            row["fiscal_label"] = fiscal_label(period_end, quarterly=quarterly)
            periods.append(row)
    return periods


def fiscal_label(period_end: str, *, quarterly: bool) -> str:
    """Indian fiscal convention: the year ending 31 March 2026 is FY26."""
    moment = datetime.strptime(period_end[:10], "%Y-%m-%d")
    fiscal_year = moment.year + 1 if moment.month > 3 else moment.year
    label = f"FY{str(fiscal_year)[-2:]}"
    if not quarterly:
        return label
    quarter = {1: "Q4", 2: "Q4", 3: "Q4", 4: "Q1", 5: "Q1", 6: "Q1", 7: "Q2", 8: "Q2",
               9: "Q2", 10: "Q3", 11: "Q3", 12: "Q3"}[moment.month]
    return f"{label}{quarter}"


def _yahoo_session():
    """Browser-like session — datacenter IPs often get empty fundamentals without this."""
    try:
        from curl_cffi import requests as cffi_requests

        session = cffi_requests.Session(impersonate="chrome")
        try:
            # Warm crumb/cookie jar used by Yahoo fundamentals endpoints.
            session.get("https://fc.yahoo.com", timeout=15)
            session.get("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=15)
        except Exception:
            pass
        return session
    except Exception:
        return None


def _frame_nonempty(frame: Any) -> bool:
    try:
        if frame is None:
            return False
        if getattr(frame, "empty", False):
            return False
        return bool(getattr(frame, "shape", (0, 0))[0] or getattr(frame, "shape", (0, 0))[1])
    except Exception:
        return False


def _chart_reachable(yahoo_symbol: str) -> bool:
    """Prices still work when fundamentals are blocked — used to classify errors."""
    try:
        raw = _http_get(chart_url(yahoo_symbol, range_="5d", interval="1d"), timeout=15)
        payload = json.loads(raw.decode("utf-8"))
        return bool((((payload.get("chart") or {}).get("result") or [None])[0]))
    except Exception:
        return False


def fetch_statements(
    symbol: str,
    *,
    loader: Optional[Callable[[str], dict[str, Any]]] = None,
) -> dict[str, Any]:
    """Annual and quarterly statements. Uses yfinance when available.

    ``loader`` lets tests supply recorded frames; production passes nothing.
    On cloud hosts Yahoo often returns empty fundamentals unless curl_cffi
    chrome impersonation is used; we try that first, then plain Ticker.
    """
    if loader is not None:
        return loader(symbol)
    try:
        import yfinance  # noqa: F401
    except Exception as exc:
        return {"ok": False, "symbol": symbol, "error": f"yfinance_unavailable:{exc}",
                "annual": [], "quarterly": []}

    from yfinance import Ticker

    errors: list[str] = []
    session = _yahoo_session()
    chart_ok = False
    for candidate in yahoo_symbols(symbol):
        try:
            ticker = Ticker(candidate, session=session) if session is not None else Ticker(candidate)
            # Prefer get_* (fundamentals timeseries); fall back to properties.
            try:
                income = ticker.get_income_stmt(freq="yearly")
                balance = ticker.get_balance_sheet(freq="yearly")
                cash = ticker.get_cash_flow(freq="yearly")
            except Exception:
                income = ticker.income_stmt
                balance = ticker.balance_sheet
                cash = ticker.cashflow
            try:
                q_income = ticker.get_income_stmt(freq="quarterly")
                q_balance = ticker.get_balance_sheet(freq="quarterly")
                q_cash = ticker.get_cash_flow(freq="quarterly")
            except Exception:
                q_income = ticker.quarterly_income_stmt
                q_balance = ticker.quarterly_balance_sheet
                q_cash = ticker.quarterly_cashflow

            if not any(_frame_nonempty(f) for f in (income, balance, cash, q_income, q_balance, q_cash)):
                # Retry once without a custom session — some envs break with curl_cffi.
                if session is not None:
                    ticker2 = Ticker(candidate)
                    income = ticker2.income_stmt
                    balance = ticker2.balance_sheet
                    cash = ticker2.cashflow
                    q_income = ticker2.quarterly_income_stmt
                    q_balance = ticker2.quarterly_balance_sheet
                    q_cash = ticker2.quarterly_cashflow

            annual = _merge_frames([income, balance, cash], quarterly=False)
            quarterly = _merge_frames([q_income, q_balance, q_cash], quarterly=True)
        except Exception as exc:
            errors.append(f"{candidate}:{type(exc).__name__}:{str(exc)[:80]}")
            continue
        if annual or quarterly:
            return {
                "ok": True,
                "symbol": symbol,
                "yahoo_symbol": candidate,
                "annual": annual,
                "quarterly": quarterly,
                "transport": "curl_cffi" if session is not None else "yfinance",
            }
        if _chart_reachable(candidate):
            chart_ok = True
            errors.append(f"{candidate}:fundamentals_empty_chart_ok")
        else:
            errors.append(f"{candidate}:empty")

    reason = "; ".join(errors)[:300]
    if chart_ok:
        reason = (
            "yahoo_fundamentals_blocked:"
            + reason
            + " (chart/prices reachable; statement endpoints returned empty — "
            "common on cloud/datacenter IPs)"
        )
    return {"ok": False, "symbol": symbol, "error": reason, "annual": [], "quarterly": []}


def _merge_frames(frames: list[Any], *, quarterly: bool) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for frame in frames:
        for row in map_statement_frame(frame, quarterly=quarterly):
            key = row["fiscal_label"]
            target = merged.setdefault(key, {"fiscal_label": key, "period_end": row["period_end"]})
            for field, value in row.items():
                if field in ("fiscal_label", "period_end"):
                    continue
                target.setdefault(field, value)
    return sorted(merged.values(), key=lambda r: r["period_end"])
