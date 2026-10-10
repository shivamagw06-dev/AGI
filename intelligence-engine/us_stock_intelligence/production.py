"""Canonical US equity intelligence assembled from the Yahoo provider.

The module deliberately returns AGI canonical objects and derived research
statistics, never Yahoo-native response payloads and never a buy/sell call.
"""

from __future__ import annotations

import asyncio
import copy
import math
import re
import statistics
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.market_data.providers.yahoo import YahooFinanceProvider

_CACHE_TTL_SECONDS = 120.0
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_OVERVIEW_CACHE_TTL_SECONDS = 60.0
_OVERVIEW_CACHE: tuple[float, dict[str, Any]] | None = None
_SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9.-]{0,14}$")

_BENCHMARKS: dict[str, str] = {
    "^GSPC": "S&P 500",
    "^DJI": "Dow Jones",
    "^IXIC": "Nasdaq Composite",
    "^RUT": "Russell 2000",
    "^VIX": "VIX",
    "^TNX": "US 10Y Yield",
}
_SECTOR_ETFS: dict[str, str] = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLV": "Health Care",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLE": "Energy",
    "XLI": "Industrials",
    "XLC": "Communication",
    "XLU": "Utilities",
    "XLRE": "Real Estate",
    "XLB": "Materials",
}
_US_UNIVERSE: dict[str, str] = {
    "AAPL": "Technology", "MSFT": "Technology", "NVDA": "Technology", "AVGO": "Technology",
    "ORCL": "Technology", "CRM": "Technology", "AMD": "Technology", "ADBE": "Technology",
    "CSCO": "Technology", "IBM": "Technology", "QCOM": "Technology", "TXN": "Technology",
    "AMZN": "Consumer Discretionary", "TSLA": "Consumer Discretionary", "HD": "Consumer Discretionary",
    "MCD": "Consumer Discretionary", "NKE": "Consumer Discretionary", "SBUX": "Consumer Discretionary",
    "META": "Communication", "GOOGL": "Communication", "NFLX": "Communication", "DIS": "Communication",
    "JPM": "Financials", "BAC": "Financials", "WFC": "Financials", "GS": "Financials",
    "MS": "Financials", "V": "Financials", "MA": "Financials", "BRK-B": "Financials",
    "LLY": "Health Care", "UNH": "Health Care", "JNJ": "Health Care", "ABBV": "Health Care",
    "MRK": "Health Care", "PFE": "Health Care", "TMO": "Health Care", "ABT": "Health Care",
    "XOM": "Energy", "CVX": "Energy", "COP": "Energy", "SLB": "Energy",
    "WMT": "Consumer Staples", "COST": "Consumer Staples", "PG": "Consumer Staples",
    "KO": "Consumer Staples", "PEP": "Consumer Staples", "PM": "Consumer Staples",
    "CAT": "Industrials", "GE": "Industrials", "HON": "Industrials", "RTX": "Industrials",
    "UPS": "Industrials", "DE": "Industrials", "BA": "Industrials", "LMT": "Industrials",
    "NEE": "Utilities", "DUK": "Utilities", "SO": "Utilities", "AMT": "Real Estate",
    "PLD": "Real Estate", "LIN": "Materials", "FCX": "Materials", "SHW": "Materials",
}


def _number(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _pick(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def _clean_symbol(symbol: str) -> str:
    value = (symbol or "AAPL").strip().upper().replace("BRK.B", "BRK-B")
    if value.startswith("US:"):
        value = value[3:]
    if not _SYMBOL_RE.fullmatch(value):
        raise ValueError("Enter a valid US ticker, for example AAPL, MSFT or BRK-B.")
    return value


def _dump(value: Any, fallback: Any) -> Any:
    if isinstance(value, Exception):
        return fallback
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    return value if value is not None else fallback


def _period(row: dict[str, Any]) -> str | None:
    return str(_pick(row, "period_end", "end_date", "as_of") or "") or None


def _statement_rows(financial_history: dict[str, Any], cadence: str) -> list[dict[str, Any]]:
    income = ((financial_history.get("income_statement") or {}).get(cadence) or [])
    balance = ((financial_history.get("balance_sheet") or {}).get(cadence) or [])
    cash = ((financial_history.get("cash_flow") or {}).get(cadence) or [])
    balance_by_period = {_period(row): row for row in balance}
    cash_by_period = {_period(row): row for row in cash}
    rows: list[dict[str, Any]] = []
    for item in income[:6]:
        period = _period(item)
        inc = item.get("line_items") or {}
        bal = (balance_by_period.get(period) or {}).get("line_items") or {}
        cfs = (cash_by_period.get(period) or {}).get("line_items") or {}
        rows.append(
            {
                "period": period,
                "revenue": _pick(inc, "revenue", "total_revenue"),
                "ebitda": _pick(inc, "ebitda"),
                "operating_income": _pick(inc, "operating_income", "ebit"),
                "net_income": _pick(inc, "net_income"),
                "eps": _pick(inc, "diluted_eps", "basic_eps", "eps"),
                "operating_cash_flow": _pick(cfs, "operating_cash_flow"),
                "free_cash_flow": _pick(cfs, "free_cash_flow"),
                "cash": _pick(bal, "cash_and_equivalents", "cash", "cash_and_short_term_investments"),
                "debt": _pick(bal, "total_debt", "long_term_debt"),
            }
        )
    return rows


def _pct_change(current: Any, prior: Any) -> float | None:
    current_n = _number(current)
    prior_n = _number(prior)
    if current_n is None or prior_n in (None, 0):
        return None
    return round((current_n / prior_n - 1.0) * 100.0, 2)


def _price_analytics(bars: list[dict[str, Any]]) -> dict[str, Any]:
    clean = [row for row in bars if _number(row.get("close")) is not None]
    closes = [float(row["close"]) for row in clean]
    if not closes:
        return {}

    def trailing(sessions: int) -> float | None:
        if len(closes) <= sessions or closes[-sessions - 1] == 0:
            return None
        return round((closes[-1] / closes[-sessions - 1] - 1.0) * 100.0, 2)

    returns = [math.log(closes[i] / closes[i - 1]) for i in range(1, len(closes)) if closes[i - 1] > 0]
    volatility = round(statistics.stdev(returns) * math.sqrt(252) * 100.0, 2) if len(returns) > 1 else None
    peak = closes[0]
    max_drawdown = 0.0
    for close in closes:
        peak = max(peak, close)
        max_drawdown = min(max_drawdown, close / peak - 1.0)
    sma50 = sum(closes[-50:]) / min(50, len(closes))
    sma200 = sum(closes[-200:]) / min(200, len(closes))
    latest = closes[-1]
    trend = "positive" if latest > sma50 > sma200 else "negative" if latest < sma50 < sma200 else "mixed"
    return {
        "return_1m_pct": trailing(21),
        "return_3m_pct": trailing(63),
        "return_6m_pct": trailing(126),
        "return_1y_pct": round((latest / closes[0] - 1.0) * 100.0, 2) if len(closes) > 1 else None,
        "annualized_volatility_pct": volatility,
        "max_drawdown_pct": round(max_drawdown * 100.0, 2),
        "sma_50": round(sma50, 2),
        "sma_200": round(sma200, 2),
        "trend": trend,
        "range_high": round(max(closes), 2),
        "range_low": round(min(closes), 2),
    }


def _research_flags(metrics: dict[str, Any], technicals: dict[str, Any], annual: list[dict[str, Any]]) -> list[dict[str, str]]:
    flags: list[dict[str, str]] = []
    pe = _number(_pick(metrics, "trailing_pe", "trailingPE"))
    beta = _number(_pick(metrics, "beta"))
    vol = _number(technicals.get("annualized_volatility_pct"))
    drawdown = _number(technicals.get("max_drawdown_pct"))
    if pe is not None and pe > 35:
        flags.append({"level": "watch", "label": "Premium valuation", "detail": f"Trailing P/E is {pe:.1f}x."})
    if beta is not None and beta > 1.35:
        flags.append({"level": "watch", "label": "High market sensitivity", "detail": f"Reported beta is {beta:.2f}."})
    if vol is not None and vol > 45:
        flags.append({"level": "risk", "label": "Elevated volatility", "detail": f"Annualized realized volatility is {vol:.1f}%."})
    if drawdown is not None and drawdown < -25:
        flags.append({"level": "risk", "label": "Material drawdown", "detail": f"One-year maximum drawdown is {drawdown:.1f}%."})
    if len(annual) >= 2 and _pct_change(annual[0].get("revenue"), annual[1].get("revenue")) is not None:
        growth = _pct_change(annual[0].get("revenue"), annual[1].get("revenue"))
        if growth is not None and growth < 0:
            flags.append({"level": "watch", "label": "Revenue contraction", "detail": f"Latest annual revenue changed {growth:.1f}% year on year."})
    if not flags:
        flags.append({"level": "info", "label": "No mechanical red flag", "detail": "The available Yahoo fields did not trigger AGI's basic screening thresholds."})
    return flags


async def analyse_us_stock(symbol: str) -> dict[str, Any]:
    ticker = _clean_symbol(symbol)
    cached = _CACHE.get(ticker)
    if cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        out = copy.deepcopy(cached[1])
        out["cache_hit"] = True
        return out

    provider = YahooFinanceProvider()
    scoped = f"US:{ticker}"
    start = date.today() - timedelta(days=370)
    errors: dict[str, str] = {}

    async def capture(label: str, awaitable: Any) -> Any:
        try:
            return await asyncio.wait_for(awaitable, timeout=28.0)
        except Exception as exc:  # noqa: BLE001
            errors[label] = str(exc)[:220]
            return exc

    quote_raw, history_raw, fundamentals_raw, financial_raw, actions_raw, events_raw = await asyncio.gather(
        capture("quote", provider.get_quote(scoped)),
        capture("price_history", provider.get_ohlcv(scoped, interval="1d", start=start, end=date.today())),
        capture("fundamentals", provider.get_fundamentals(scoped)),
        capture("financial_history", provider.get_financial_intelligence(scoped)),
        capture("corporate_actions", provider.get_corporate_actions(scoped)),
        capture("calendar", provider.get_calendar_events(symbol=scoped)),
    )

    quote = _dump(quote_raw, {})
    history = _dump(history_raw, {})
    fundamentals = _dump(fundamentals_raw, {})
    financial = _dump(financial_raw, {})
    actions = [_dump(row, {}) for row in actions_raw] if isinstance(actions_raw, list) else []
    events = [_dump(row, {}) for row in events_raw] if isinstance(events_raw, list) else []
    bars = list(history.get("bars") or [])
    financial_history = financial.get("financial_history") or {}
    valuation_snapshot = financial.get("valuation_snapshot") or {}
    metrics = dict(fundamentals.get("metrics") or {})
    metrics.update({k: v for k, v in (valuation_snapshot.get("metrics") or {}).items() if v not in (None, "")})
    annual = _statement_rows(financial_history, "annual")
    quarterly = _statement_rows(financial_history, "quarterly")
    technicals = _price_analytics(bars)

    revenue_growth = _pct_change(annual[0].get("revenue"), annual[1].get("revenue")) if len(annual) >= 2 else None
    earnings_growth = _pct_change(annual[0].get("net_income"), annual[1].get("net_income")) if len(annual) >= 2 else None
    latest_revenue = _number(annual[0].get("revenue")) if annual else None
    latest_income = _number(annual[0].get("net_income")) if annual else None
    net_margin = round(latest_income / latest_revenue * 100.0, 2) if latest_revenue and latest_income is not None else None

    coverage_checks = [
        bool(quote.get("last")),
        len(bars) >= 120,
        len(metrics) >= 5,
        bool(annual),
        bool(quarterly),
        not errors.get("financial_history"),
    ]
    coverage_score = round(sum(coverage_checks) / len(coverage_checks) * 100)
    grade = "A" if coverage_score >= 85 else "B" if coverage_score >= 65 else "C" if coverage_score >= 45 else "INCOMPLETE"
    name = _pick(metrics, "long_name", "longName", "short_name", "shortName") or ticker

    out = {
        "status": "ok" if quote or bars or metrics else "unavailable",
        "symbol": ticker,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "cache_hit": False,
        "provider": {
            "name": "Yahoo Finance",
            "role": "market data and secondary research source",
            "canonicalized": True,
            "real_time_claimed": False,
        },
        "profile": {
            "name": name,
            "sector": _pick(metrics, "sector"),
            "industry": _pick(metrics, "industry"),
            "exchange": quote.get("exchange"),
            "currency": quote.get("currency") or fundamentals.get("currency") or "USD",
        },
        "quote": quote,
        "price_history": bars,
        "technicals": technicals,
        "valuation": {
            "market_cap": _pick(metrics, "market_cap", "marketCap"),
            "enterprise_value": _pick(metrics, "enterprise_value", "enterpriseValue"),
            "trailing_pe": _pick(metrics, "trailing_pe", "trailingPE"),
            "forward_pe": _pick(metrics, "forward_pe", "forwardPE"),
            "price_to_book": _pick(metrics, "price_to_book", "priceToBook"),
            "price_to_sales": _pick(metrics, "price_to_sales", "priceToSalesTrailing12Months"),
            "enterprise_to_ebitda": _pick(metrics, "enterprise_to_ebitda", "enterpriseToEbitda"),
            "peg_ratio": _pick(metrics, "peg_ratio", "pegRatio"),
            "dividend_yield": _pick(metrics, "dividend_yield", "dividendYield"),
            "beta": _pick(metrics, "beta"),
        },
        "financials": {
            "currency": valuation_snapshot.get("currency") or fundamentals.get("currency") or quote.get("currency") or "USD",
            "annual": annual,
            "quarterly": quarterly,
            "revenue_growth_pct": revenue_growth,
            "earnings_growth_pct": earnings_growth,
            "net_margin_pct": net_margin,
        },
        "analyst": {
            "recommendation": _pick(metrics, "recommendation_key", "recommendationKey"),
            "recommendation_mean": _pick(metrics, "recommendation_mean", "recommendationMean"),
            "analyst_count": _pick(metrics, "number_of_analyst_opinions", "numberOfAnalystOpinions"),
            "target_mean_price": _pick(metrics, "target_mean_price", "targetMeanPrice"),
            "target_high_price": _pick(metrics, "target_high_price", "targetHighPrice"),
            "target_low_price": _pick(metrics, "target_low_price", "targetLowPrice"),
        },
        "events": events[:12],
        "corporate_actions": actions[:20],
        "risk_flags": _research_flags(metrics, technicals, annual),
        "quality": {
            "coverage_score": coverage_score,
            "grade": grade,
            "price_sessions": len(bars),
            "annual_periods": len(annual),
            "quarterly_periods": len(quarterly),
            "errors": errors,
        },
        "policy": {
            "research_only": True,
            "no_buy_sell_recommendation": True,
            "note": "Yahoo data may be delayed, incomplete or revised. Derived statistics are AGI calculations, not Yahoo recommendations.",
        },
    }
    _CACHE[ticker] = (time.monotonic(), copy.deepcopy(out))
    return out


def _raw_value(row: dict[str, Any], key: str) -> Any:
    value = row.get(key)
    if isinstance(value, dict):
        return value.get("raw", value.get("fmt"))
    return value


def _normalize_market_quote(row: dict[str, Any], sector: str | None = None) -> dict[str, Any]:
    symbol = str(row.get("symbol") or "").upper()
    dividend = _number(_raw_value(row, "dividendYield"))
    if dividend is not None and dividend < 1:
        dividend *= 100.0
    volume = _number(_raw_value(row, "regularMarketVolume"))
    average_volume = _number(_raw_value(row, "averageDailyVolume3Month"))
    volume_ratio = volume / average_volume if volume is not None and average_volume not in (None, 0) else None
    fifty_two_week = _number(_raw_value(row, "fiftyTwoWeekChangePercent"))
    if fifty_two_week is not None and abs(fifty_two_week) <= 2:
        fifty_two_week *= 100.0
    return {
        "symbol": symbol,
        "name": _raw_value(row, "shortName") or _raw_value(row, "longName") or symbol,
        "sector": sector,
        "exchange": _raw_value(row, "fullExchangeName") or _raw_value(row, "exchange"),
        "currency": _raw_value(row, "currency") or "USD",
        "market_state": _raw_value(row, "marketState"),
        "price": _raw_value(row, "regularMarketPrice"),
        "change": _raw_value(row, "regularMarketChange"),
        "change_pct": _raw_value(row, "regularMarketChangePercent"),
        "previous_close": _raw_value(row, "regularMarketPreviousClose"),
        "day_high": _raw_value(row, "regularMarketDayHigh"),
        "day_low": _raw_value(row, "regularMarketDayLow"),
        "volume": volume,
        "average_volume": average_volume,
        "volume_ratio": round(volume_ratio, 2) if volume_ratio is not None else None,
        "market_cap": _raw_value(row, "marketCap"),
        "trailing_pe": _raw_value(row, "trailingPE"),
        "forward_pe": _raw_value(row, "forwardPE"),
        "eps_ttm": _raw_value(row, "epsTrailingTwelveMonths"),
        "dividend_yield_pct": round(dividend, 2) if dividend is not None else None,
        "beta": _raw_value(row, "beta"),
        "fifty_two_week_change_pct": round(fifty_two_week, 2) if fifty_two_week is not None else None,
        "as_of_epoch": _raw_value(row, "regularMarketTime"),
    }


async def _bulk_market_quotes(provider: YahooFinanceProvider, symbols: list[str]) -> list[dict[str, Any]]:
    if not symbols:
        return []
    payload = await provider._get(
        f"{provider.base_url}/v7/finance/quote",
        {"symbols": ",".join(symbols), "formatted": "false"},
        need_crumb=True,
    )
    return list(((payload.get("quoteResponse") or {}).get("result") or []))


async def _predefined_screen(provider: YahooFinanceProvider, screen_id: str) -> list[dict[str, Any]]:
    payload = await provider._get(
        f"{provider.base_url}/v1/finance/screener/predefined/saved",
        {"scrIds": screen_id, "count": 25, "start": 0, "formatted": "false"},
        need_crumb=True,
    )
    result = ((payload.get("finance") or {}).get("result") or [])
    return list((result[0] if result else {}).get("quotes") or [])


def _sorted(rows: list[dict[str, Any]], key: str, *, reverse: bool = True, limit: int = 15) -> list[dict[str, Any]]:
    eligible = [row for row in rows if _number(row.get(key)) is not None]
    return sorted(eligible, key=lambda row: float(row[key]), reverse=reverse)[:limit]


async def market_overview() -> dict[str, Any]:
    """Live/daily US benchmarks, sectors, breadth and research screeners."""
    global _OVERVIEW_CACHE
    if _OVERVIEW_CACHE and time.monotonic() - _OVERVIEW_CACHE[0] < _OVERVIEW_CACHE_TTL_SECONDS:
        out = copy.deepcopy(_OVERVIEW_CACHE[1])
        out["cache_hit"] = True
        return out

    provider = YahooFinanceProvider()
    all_symbols = list(_BENCHMARKS) + list(_SECTOR_ETFS) + list(_US_UNIVERSE)
    errors: dict[str, str] = {}

    async def capture(label: str, awaitable: Any, fallback: Any) -> Any:
        try:
            return await asyncio.wait_for(awaitable, timeout=25.0)
        except Exception as exc:  # noqa: BLE001
            errors[label] = str(exc)[:220]
            return fallback

    raw_quotes, raw_gainers, raw_losers, raw_active = await asyncio.gather(
        capture("market_quotes", _bulk_market_quotes(provider, all_symbols), []),
        capture("day_gainers", _predefined_screen(provider, "day_gainers"), []),
        capture("day_losers", _predefined_screen(provider, "day_losers"), []),
        capture("most_actives", _predefined_screen(provider, "most_actives"), []),
    )

    normalized: dict[str, dict[str, Any]] = {}
    for row in raw_quotes:
        ticker = str(row.get("symbol") or "").upper()
        normalized[ticker] = _normalize_market_quote(row, _US_UNIVERSE.get(ticker) or _SECTOR_ETFS.get(ticker))
    universe = [normalized[symbol] for symbol in _US_UNIVERSE if symbol in normalized]
    benchmarks = []
    for symbol, name in _BENCHMARKS.items():
        if symbol in normalized:
            row = dict(normalized[symbol])
            row["name"] = name
            benchmarks.append(row)
    sectors = []
    for symbol, name in _SECTOR_ETFS.items():
        if symbol in normalized:
            row = dict(normalized[symbol])
            row["name"] = name
            sectors.append(row)

    def broad(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [_normalize_market_quote(row) for row in rows if row.get("symbol")]

    gainers = broad(raw_gainers) or _sorted(universe, "change_pct")
    losers = broad(raw_losers) or _sorted(universe, "change_pct", reverse=False)
    most_active = broad(raw_active) or _sorted(universe, "volume_ratio")
    value = _sorted([row for row in universe if 0 < (_number(row.get("trailing_pe")) or -1) <= 22 and (_number(row.get("market_cap")) or 0) >= 2_000_000_000], "trailing_pe", reverse=False)
    momentum = _sorted([row for row in universe if (_number(row.get("fifty_two_week_change_pct")) or -999) > 0], "fifty_two_week_change_pct")
    dividend = _sorted([row for row in universe if (_number(row.get("dividend_yield_pct")) or 0) > 0], "dividend_yield_pct")

    advancing = sum(1 for row in universe if (_number(row.get("change_pct")) or 0) > 0)
    declining = sum(1 for row in universe if (_number(row.get("change_pct")) or 0) < 0)
    unchanged = max(0, len(universe) - advancing - declining)
    states = [row.get("market_state") for row in benchmarks if row.get("market_state")]
    market_state = max(set(states), key=states.count) if states else "UNKNOWN"
    overview = {
        "status": "ok" if benchmarks or universe or gainers else "unavailable",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "cache_hit": False,
        "refresh_seconds": int(_OVERVIEW_CACHE_TTL_SECONDS),
        "market_state": market_state,
        "benchmarks": benchmarks,
        "sectors": sectors,
        "breadth": {
            "advancing": advancing,
            "declining": declining,
            "unchanged": unchanged,
            "coverage": len(universe),
            "advance_ratio_pct": round(advancing / len(universe) * 100.0, 1) if universe else None,
        },
        "screeners": {
            "day_gainers": gainers[:20],
            "day_losers": losers[:20],
            "most_active": most_active[:20],
            "value": value[:20],
            "momentum": momentum[:20],
            "dividend": dividend[:20],
        },
        "quality": {
            "bellwether_coverage": len(universe),
            "broad_market_screens": bool(raw_gainers or raw_losers or raw_active),
            "errors": errors,
        },
        "source": {
            "name": "Yahoo Finance",
            "note": "Broad US predefined market screens plus a liquid cross-sector bellwether universe. Quotes may be delayed.",
        },
    }
    _OVERVIEW_CACHE = (time.monotonic(), copy.deepcopy(overview))
    return overview
