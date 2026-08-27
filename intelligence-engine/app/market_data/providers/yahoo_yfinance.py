"""Optional yfinance soft path for Yahoo financial statements / calendar / filings.

Uses:
  - Ticker.get_income_stmt / get_balance_sheet / get_cash_flow|get_cashflow
  - quarterly_* properties as secondary (pretty titles — prefer get_* pretty=False)
  - Ticker.calendar, get_earnings_dates (needs lxml), get_sec_filings
  - Ticker.get_earnings is deprecated / returns None — do not use

when quoteSummary crumb auth fails under plain httpx. Never exposes Yahoo-native
payloads outward — callers must map through yahoo_mapper canonical helpers.
"""

from __future__ import annotations

import logging
import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from datetime import date, datetime
from typing import Any

_LOG = logging.getLogger("agi.yahoo.yfinance")
_EXEC = ThreadPoolExecutor(max_workers=2, thread_name_prefix="yahoo-yf")
# Hard ceiling — Meta.NS-style 404 storms must not hold Ask for minutes.
_YF_TIMEOUT_SEC = float(os.environ.get("YAHOO_YFINANCE_TIMEOUT_SEC", "4") or "4")


def yfinance_available() -> bool:
    try:
        import yfinance  # noqa: F401

        return True
    except Exception:
        return False


def _df_to_period_rows(df: Any) -> list[dict[str, Any]]:
    """Convert yfinance statement DataFrame (rows=fields, cols=dates) → period dicts."""
    if df is None:
        return []
    try:
        import pandas as pd
    except Exception:
        return []
    if not isinstance(df, pd.DataFrame) or df.empty:
        return []

    rows: list[dict[str, Any]] = []
    for col in df.columns:
        if hasattr(col, "strftime"):
            end = col.strftime("%Y-%m-%d")
        else:
            end = str(col)[:10]
        period: dict[str, Any] = {"endDate": end}
        for field in df.index:
            try:
                val = df.at[field, col]
            except Exception:
                continue
            if val is None:
                continue
            try:
                if pd.isna(val):
                    continue
            except Exception:
                pass
            raw_name = str(field).strip()
            # Properties like quarterly_income_stmt may use pretty titles ("Free Cash Flow").
            if " " in raw_name:
                parts = [p for p in raw_name.split() if p]
                name = parts[0].capitalize() + "".join(p.capitalize() for p in parts[1:])
            else:
                name = raw_name
            try:
                num = float(val)
            except (TypeError, ValueError):
                continue
            if name and name.isupper():
                period[name.lower()] = num
            elif name:
                period[name[0].lower() + name[1:]] = num
            else:
                continue
        if len(period) > 1:
            rows.append(period)
    rows.sort(key=lambda r: r.get("endDate") or "", reverse=True)
    return rows


def _safe_df_call(fn: Any, **kwargs: Any) -> Any:
    try:
        return fn(**kwargs)
    except TypeError:
        # Some aliases omit pretty=
        try:
            kwargs.pop("pretty", None)
            return fn(**kwargs)
        except Exception:
            return None
    except Exception:
        return None


def _serialize_scalar(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (date, datetime)):
        return v.isoformat() if isinstance(v, datetime) else v.isoformat()
    if isinstance(v, (int, float, str, bool)):
        return v
    try:
        import pandas as pd

        if pd.isna(v):
            return None
    except Exception:
        pass
    if hasattr(v, "isoformat"):
        try:
            return v.isoformat()
        except Exception:
            pass
    return str(v)


def _calendar_to_dict(cal: Any) -> dict[str, Any]:
    if not isinstance(cal, dict):
        return {}
    out: dict[str, Any] = {}
    for k, v in cal.items():
        key = str(k)
        if isinstance(v, list):
            out[key] = [_serialize_scalar(x) for x in v]
        else:
            out[key] = _serialize_scalar(v)
    return out


def _earnings_dates_to_rows(df: Any, *, limit: int = 12) -> list[dict[str, Any]]:
    if df is None:
        return []
    try:
        import pandas as pd
    except Exception:
        return []
    if not isinstance(df, pd.DataFrame) or df.empty:
        return []
    rows: list[dict[str, Any]] = []
    # Index is typically Earnings Date; columns EPS Estimate / Reported EPS / Surprise(%)
    working = df.reset_index()
    for _, series in working.head(limit).iterrows():
        item: dict[str, Any] = {}
        for col, val in series.items():
            cname = str(col).strip()
            if cname.lower() in {"earnings date", "earningsdate", "date"}:
                item["earnings_date"] = _serialize_scalar(val)
            elif "estimate" in cname.lower():
                try:
                    item["eps_estimate"] = None if pd.isna(val) else float(val)
                except (TypeError, ValueError):
                    pass
            elif "reported" in cname.lower():
                try:
                    item["eps_actual"] = None if pd.isna(val) else float(val)
                except (TypeError, ValueError):
                    pass
            elif "surprise" in cname.lower():
                try:
                    item["surprise_percent"] = None if pd.isna(val) else float(val)
                except (TypeError, ValueError):
                    pass
        if item.get("earnings_date"):
            rows.append(item)
    return rows


def _sec_filings_to_rows(raw: Any, *, limit: int = 40) -> list[dict[str, Any]]:
    rows_in: list[Any]
    if isinstance(raw, dict):
        # Sometimes {"filings": [...]} or type→list
        if isinstance(raw.get("filings"), list):
            rows_in = raw["filings"]
        else:
            rows_in = []
            for v in raw.values():
                if isinstance(v, list):
                    rows_in.extend(v)
    elif isinstance(raw, list):
        rows_in = raw
    else:
        return []
    out: list[dict[str, Any]] = []
    for row in rows_in[:limit]:
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "date": _serialize_scalar(row.get("date")),
                "filing_type": row.get("type") or row.get("filing_type"),
                "title": row.get("title"),
                "url": row.get("edgarUrl") or row.get("url"),
                "epoch_date": row.get("epochDate"),
            }
        )
    return out


def _statement_df(t: Any, kind: str, freq: str) -> Any:
    """Prefer get_* pretty=False; fall back to quarterly_* properties."""
    if kind == "income":
        df = _safe_df_call(t.get_income_stmt, as_dict=False, pretty=False, freq=freq)
        if df is not None and getattr(df, "empty", True) is False:
            return df
        if freq == "quarterly":
            return getattr(t, "quarterly_income_stmt", None)
        return getattr(t, "income_stmt", None)
    if kind == "balance":
        return _safe_df_call(t.get_balance_sheet, as_dict=False, pretty=False, freq=freq)
    if kind == "cash":
        # Docs list get_cashflow; library also exposes get_cash_flow
        fn = getattr(t, "get_cash_flow", None) or getattr(t, "get_cashflow", None)
        df = _safe_df_call(fn, as_dict=False, pretty=False, freq=freq) if fn else None
        if df is not None and getattr(df, "empty", True) is False:
            return df
        if freq == "quarterly":
            return getattr(t, "quarterly_cashflow", None)
        return getattr(t, "cashflow", None)
    return None


def _fetch_package_sync(yahoo_symbol: str) -> dict[str, Any]:
    cache_key = f"yf_pkg:{yahoo_symbol}"
    try:
        from app.market_data.providers.yahoo_request_cache import cached_get, cached_set

        hit = cached_get(cache_key)
        if isinstance(hit, dict):
            return hit
    except Exception:
        cached_get = cached_set = None  # type: ignore[assignment]

    import yfinance as yf

    t = yf.Ticker(yahoo_symbol)
    income_annual = _df_to_period_rows(_statement_df(t, "income", "yearly"))
    income_q = _df_to_period_rows(_statement_df(t, "income", "quarterly"))
    balance_annual = _df_to_period_rows(_statement_df(t, "balance", "yearly"))
    balance_q = _df_to_period_rows(_statement_df(t, "balance", "quarterly"))
    cash_annual = _df_to_period_rows(_statement_df(t, "cash", "yearly"))
    cash_q = _df_to_period_rows(_statement_df(t, "cash", "quarterly"))

    info: dict[str, Any] = {}
    try:
        raw = t.info or {}
        if isinstance(raw, dict):
            info = raw
    except Exception:
        info = {}

    calendar: dict[str, Any] = {}
    try:
        calendar = _calendar_to_dict(t.calendar)
    except Exception:
        calendar = {}

    earnings_dates: list[dict[str, Any]] = []
    try:
        earnings_dates = _earnings_dates_to_rows(t.get_earnings_dates(limit=12))
    except Exception:
        earnings_dates = []

    sec_filings: list[dict[str, Any]] = []
    try:
        sec_filings = _sec_filings_to_rows(t.get_sec_filings())
    except Exception:
        sec_filings = []

    # get_earnings is deprecated and returns None — derive soft annual NI series instead
    earnings_annual = [
        {"period_end": r.get("endDate"), "net_income": r.get("netIncome") or r.get("netIncomeCommonStockholders")}
        for r in income_annual
        if (r.get("netIncome") is not None or r.get("netIncomeCommonStockholders") is not None)
    ]

    pack = {
        "source": "yfinance",
        "endpoint": "fundamentals-timeseries+calendar",
        "symbol": yahoo_symbol,
        "income_annual": income_annual,
        "income_quarterly": income_q,
        "balance_annual": balance_annual,
        "balance_quarterly": balance_q,
        "cash_annual": cash_annual,
        "cash_quarterly": cash_q,
        "info": info,
        "calendar": calendar,
        "earnings_dates": earnings_dates,
        "sec_filings": sec_filings,
        "earnings_annual": earnings_annual,
        "apis_used": [
            "get_income_stmt",
            "get_balance_sheet",
            "get_cash_flow|get_cashflow",
            "calendar",
            "get_earnings_dates",
            "get_sec_filings",
        ],
    }
    if cached_set is not None:
        try:
            cached_set(cache_key, pack)
        except Exception:
            pass
    return pack


def fetch_yfinance_financial_package_sync(
    yahoo_symbol: str, *, timeout_sec: float | None = None
) -> dict[str, Any]:
    """Sync fetch with hard wall-clock timeout + request/TTL cache."""
    if not yahoo_symbol or not yfinance_available():
        return {}
    cache_key = f"yf_pkg:{yahoo_symbol}"
    try:
        from app.market_data.providers.yahoo_request_cache import cached_get

        hit = cached_get(cache_key)
        if isinstance(hit, dict):
            return hit
    except Exception:
        pass
    budget = _YF_TIMEOUT_SEC if timeout_sec is None else max(0.5, float(timeout_sec))
    fut = _EXEC.submit(_fetch_package_sync, yahoo_symbol)
    try:
        return fut.result(timeout=budget) or {}
    except FuturesTimeout:
        _LOG.warning(
            "yfinance_timeout symbol=%s budget_s=%.1f — continuing without Yahoo pack",
            yahoo_symbol,
            budget,
        )
        empty = {"source": "yfinance", "symbol": yahoo_symbol, "timeout": True, "enabled": False}
        try:
            from app.market_data.providers.yahoo_request_cache import cached_set

            # Negative-cache briefly so Ask fan-out does not re-stampede
            cached_set(cache_key, empty, ttl_sec=60.0)
        except Exception:
            pass
        return empty
    except Exception:
        return {}


async def fetch_yfinance_financial_package(yahoo_symbol: str) -> dict[str, Any]:
    """
    Async wrapper around yfinance Ticker statement + calendar APIs.
    Returns empty dict if yfinance missing or fetch fails / times out.
    """
    if not yahoo_symbol or not yfinance_available():
        return {}
    import asyncio

    loop = asyncio.get_running_loop()
    try:
        return await loop.run_in_executor(
            None,
            lambda: fetch_yfinance_financial_package_sync(yahoo_symbol),
        )
    except Exception:
        return {}
