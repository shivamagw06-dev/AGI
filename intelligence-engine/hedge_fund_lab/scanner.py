"""Live strategy scanner — runs strategies across the NSE universe.

Every candidate carries the reason it surfaced. These are research
observations built from market data, never recommendations: no buy, no sell,
no price target of AGI's own.
"""

from __future__ import annotations

import os
import statistics as stats
from typing import Any, Optional

from hedge_fund_lab import desk_snapshot


def _num(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


# Vendor data carries occasional nonsense (an 11,360% "net margin", a 0.2 P/E
# on collapsed earnings). Anything outside a plausible band is treated as
# missing rather than surfaced as an opportunity.
_SANE_BOUNDS: dict[str, tuple[float, float]] = {
    "pe": (3.0, 200.0),
    "forward_pe": (3.0, 200.0),
    "pb": (0.05, 50.0),
    "ev_ebitda": (3.0, 60.0),
    "ev_sales": (0.05, 60.0),
    "roe": (-100.0, 150.0),
    "profit_margin": (-100.0, 100.0),
    "dividend_yield": (0.0, 25.0),
    "debt_to_equity": (0.0, 1000.0),
}


# Values inside the sane band but low enough that the denominator is probably
# distorted (depressed or one-off earnings, unconsolidated EBITDA, missing net
# debt). These are surfaced with a verification flag rather than suppressed.
_SUSPECT_BELOW: dict[str, float] = {
    "ev_ebitda": 5.0,
    "pe": 6.0,
    "pb": 0.2,
}


def _suspect_multiple(metric: str, value: Optional[float]) -> bool:
    floor = _SUSPECT_BELOW.get(metric)
    return floor is not None and value is not None and value < floor


def _sane(row: dict[str, Any], field: str) -> Optional[float]:
    """A metric only if it is inside a believable range."""
    value = _num(row.get(field))
    if value is None:
        return None
    low, high = _SANE_BOUNDS.get(field, (float("-inf"), float("inf")))
    return value if low <= value <= high else None


def _median(values: list[Any]) -> Optional[float]:
    clean = [v for v in (_num(x) for x in values) if v is not None]
    return round(stats.median(clean), 2) if clean else None


# Provenance for warehouse-backed scans. Vendors feed the warehouse on the
# nightly refresh; scanners never call vendors at Ask / page-load time.
SOURCES = {
    "market_data": "warehouse.historical_valuation+upstox",
    "fundamentals": "warehouse.historical_ratios",
    "consensus": "warehouse.consensus",
    "factors": "warehouse.hedge_fund_factors",
    "classification": "warehouse.company_master",
    "interpretation": "agi",
}

_UNIVERSE_META: dict[str, Any] = {
    "source": None,
    "as_of": None,
    "count": 0,
    "factors_joined": 0,
}


def universe_meta() -> dict[str, Any]:
    """Coverage / provenance for health and terminal surfaces."""
    return {
        "ok": bool(_UNIVERSE_META.get("count")),
        "source": _UNIVERSE_META.get("source"),
        "as_of": _UNIVERSE_META.get("as_of"),
        "count": int(_UNIVERSE_META.get("count") or 0),
        "factors_joined": int(_UNIVERSE_META.get("factors_joined") or 0),
        "sources": dict(SOURCES),
    }


def _latest_ratios_by_symbol(*, limit: int = 8000) -> dict[str, dict[str, Any]]:
    """Latest annual historical_ratios row per symbol."""
    try:
        from institutional_warehouse import store
    except Exception:
        return {}
    out: dict[str, dict[str, Any]] = {}
    try:
        for row in store.all_rows("historical_ratios", limit=limit) or []:
            if str(row.get("basis") or "").lower() not in ("", "annual"):
                continue
            sym = str(row.get("symbol") or "").upper()
            if not sym:
                continue
            prev = out.get(sym)
            if not prev or str(row.get("period") or "") > str(prev.get("period") or ""):
                out[sym] = row
    except Exception:
        return {}
    return out


def _factors_by_symbol(*, limit: int = 8000) -> dict[str, dict[str, Any]]:
    try:
        from institutional_warehouse import store
    except Exception:
        return {}
    out: dict[str, dict[str, Any]] = {}
    try:
        for row in store.all_rows("hedge_fund_factors", limit=limit) or []:
            sym = str(row.get("symbol") or "").upper()
            if not sym:
                continue
            prev = out.get(sym)
            if not prev or str(row.get("as_of") or "") > str(prev.get("as_of") or ""):
                out[sym] = row
    except Exception:
        return {}
    return out


# A year that halves a company or triples it is possible, and both happen. It is
# also the exact signature of a price series that changed adjustment convention
# halfway through - Dr. Lal PathLabs read -45%, Nuvama -75%, GRM Overseas -76%,
# and every one of those was a split rather than a loss.
#
# So a reading outside this band is withheld and listed instead of published. A
# genuine collapse is withheld with it, which is the cost: a number missing from
# the desk is visible and asks a question, where a wrong one is neither.
RETURN_FLOOR_PCT = -60.0
RETURN_CEILING_PCT = 200.0

_LAST_EXTREMES: list[dict[str, Any]] = []


def _return_1y_by_symbol(*, limit: int = 200000) -> dict[str, Optional[float]]:
    """One-year price return per symbol, computed in the database.

    This used to scan up to 200k history rows in the request process, which
    made the desk multi-minute and tipped the box into 502s, so it was turned
    off behind a flag. With it off the desk fell back to a `return_1y` parsed
    from an uploaded file, and that number goes stale the moment prices move:
    on 2026-08-20 it showed SUNTECK at +23.1% while the stock was down 25.1%
    over the year.

    Turning it back on fixed that symbol and broke every symbol that had split.

    Three feeds write this table. Upstox supplies prices already adjusted for
    splits and bonuses; the NSE bhavcopy supplies the raw price that traded.
    Both land in `close`, so a series can begin on one basis and end on the
    other, and the ratio between the two endpoints then carries the split
    factor rather than the return. Dr. Lal PathLabs split two-for-one and was
    published at -45.29% for the year against a true figure near +12%.

    The fix is to take both endpoints from one source. That needs no judgement
    about which feed adjusts and which does not - a source only has to be
    consistent with itself, and each of them is. Where several sources can
    supply both ends, the one with the most history for that symbol wins.

    A source qualifies only if its own latest bar is within a week of the
    symbol's latest, so a feed that stopped months ago cannot quietly serve a
    stale return, and its base bar has to sit in a 60-day window around the
    anniversary rather than wherever its history happens to start.
    """
    try:
        from institutional_warehouse import db
    except Exception:
        return {}
    table = db.physical_table("daily_market_history")
    weekday = "CAST(strftime('%w', date) AS INTEGER) BETWEEN 1 AND 5"
    # Two prices may only be divided by one another when they are on the same
    # adjustment basis and come from the same feed. The group key is that pair,
    # so a raw price can never be the base for an adjusted one.
    #
    # `price_basis` and `feed_family` are stamped at write time. The fallback
    # covers the rows written before those columns existed, and it is the same
    # table `institutional_warehouse.price_basis` declares - not a second
    # opinion, just one the database can read.
    feed = ("COALESCE(feed_family, CASE"
            " WHEN source LIKE 'upstox%' THEN 'upstox'"
            " WHEN source LIKE 'yahoo%' THEN 'yahoo'"
            " WHEN source = 'nse_bhavcopy' THEN 'nse'"
            " ELSE source END)")
    basis = ("COALESCE(price_basis, CASE"
             " WHEN source LIKE 'upstox%' THEN 'SPLIT_ADJUSTED'"
             " WHEN source LIKE 'yahoo%' THEN 'RAW'"
             " WHEN source = 'nse_bhavcopy' THEN 'RAW'"
             " ELSE 'UNKNOWN' END)")
    try:
        rows = db.query(
            f"""WITH usable AS (
                    SELECT symbol, {feed} || '|' || {basis} AS src, date, close FROM {table}
                    WHERE COALESCE(sys_published, 1) = 1
                      AND close IS NOT NULL AND close > 0 AND {weekday}
                      -- A price whose convention was never established is not
                      -- usable as either end. Agreement between two unknowns
                      -- means nothing.
                      AND {basis} <> 'UNKNOWN'
                ),
                sym_latest AS (
                    SELECT symbol, MAX(date) AS latest FROM usable GROUP BY symbol
                ),
                src_depth AS (
                    SELECT symbol, src, COUNT(*) AS bars, MAX(date) AS src_latest
                    FROM usable GROUP BY symbol, src
                ),
                -- A feed that stopped months ago must not serve a stale return.
                fresh_src AS (
                    SELECT d.symbol, d.src, d.bars, d.src_latest
                    FROM src_depth d JOIN sym_latest y ON y.symbol = d.symbol
                    WHERE d.src_latest >= date(y.latest, '-7 day')
                ),
                last_px AS (
                    SELECT u.symbol, u.src, u.close AS last_close, u.date AS last_date,
                           f.bars
                    FROM usable u
                    JOIN fresh_src f ON f.symbol = u.symbol AND f.src = u.src
                                    AND u.date = f.src_latest
                ),
                base AS (
                    SELECT u.symbol, u.src, u.close AS base_close, u.date AS base_date,
                           ROW_NUMBER() OVER (
                               PARTITION BY u.symbol, u.src ORDER BY u.date DESC
                           ) AS rn
                    FROM usable u
                    JOIN last_px l ON l.symbol = u.symbol AND l.src = u.src
                    WHERE u.date <= date(l.last_date, '-365 day')
                      AND u.date >= date(l.last_date, '-425 day')
                ),
                paired AS (
                    SELECT l.symbol, l.src, l.last_close, b.base_close, l.bars,
                           ROW_NUMBER() OVER (
                               PARTITION BY l.symbol ORDER BY l.bars DESC, l.src
                           ) AS pick
                    FROM last_px l
                    JOIN base b ON b.symbol = l.symbol AND b.src = l.src AND b.rn = 1
                )
                SELECT symbol, src, last_close, base_close
                FROM paired WHERE pick = 1"""
        ) or []
    except Exception:
        return {}

    out: dict[str, Optional[float]] = {}
    extremes: list[dict[str, Any]] = []
    for row in rows:
        symbol = str(row.get("symbol") or "").upper()
        last_close = _num(row.get("last_close"))
        base_close = _num(row.get("base_close"))
        if not (symbol and last_close and base_close and base_close > 0):
            continue
        value = round((last_close / base_close - 1.0) * 100.0, 2)
        if value < RETURN_FLOOR_PCT or value > RETURN_CEILING_PCT:
            extremes.append({"symbol": symbol, "return_1y": value,
                             "basis": row.get("src"), "base": base_close, "last": last_close})
            continue
        out[symbol] = value

    global _LAST_EXTREMES
    _LAST_EXTREMES = sorted(extremes, key=lambda e: abs(e["return_1y"]), reverse=True)
    return out


def extreme_returns() -> list[dict[str, Any]]:
    """One-year returns withheld from the last scan for being implausible."""
    return list(_LAST_EXTREMES)


def _latest_close_by_symbol() -> dict[str, float]:
    """Last traded close per symbol, from the price table that records trades.

    historical_valuation carries its own `cmp`, and it does not agree with the
    market. Compared against daily_market_history on 2026-08-19, 1,050 of 1,162
    symbols differed - RSDFIN at 152.44 against a true close of 96.15, a 58%
    error - and only 112 matched exactly. That price feeds market cap, the
    price-based multiples and the consensus upside, so a wrong close is wrong
    several times over on the page.

    Weekends are excluded: NSE does not trade then and those rows carry a
    differently scaled series.
    """
    try:
        from institutional_warehouse import db
    except Exception:
        return {}
    table = db.physical_table("daily_market_history")
    try:
        rows = db.query(
            f"""WITH usable AS (
                    SELECT symbol, date, close FROM {table}
                    WHERE COALESCE(sys_published, 1) = 1
                      AND close IS NOT NULL AND close > 0
                      AND CAST(strftime('%w', date) AS INTEGER) BETWEEN 1 AND 5
                ),
                latest AS (SELECT symbol, MAX(date) AS d FROM usable GROUP BY symbol)
                SELECT u.symbol, u.close FROM usable u
                JOIN latest l ON u.symbol = l.symbol AND u.date = l.d"""
        ) or []
    except Exception:
        return {}
    out: dict[str, float] = {}
    for row in rows:
        symbol = str(row.get("symbol") or "").upper()
        close = _num(row.get("close"))
        if symbol and close and close > 0:
            out[symbol] = close
    return out


def _legacy_consensus(ticker: str) -> dict[str, Any]:
    try:
        from valuation_consensus.store import get_row as consensus_row

        return consensus_row(ticker) or {}
    except Exception:
        return {}


def _map_warehouse_row(
    mi: dict[str, Any],
    *,
    ratios: dict[str, Any],
    factors: dict[str, Any],
    return_1y: Optional[float],
    legacy_consensus: dict[str, Any],
) -> dict[str, Any]:
    """Shape a Market Intelligence / warehouse row for the scanners."""
    sym = str(mi.get("symbol") or "").upper()
    # Warehouse debt_equity is a multiple (0.5); scanners use Yahoo-style %.
    debt_ratio = _num(ratios.get("debt_equity"))
    debt_to_equity = round(debt_ratio * 100.0, 2) if debt_ratio is not None else None
    profit_margin = _num(ratios.get("net_margin"))
    roe = _num(mi.get("roe"))
    if roe is None:
        roe = _num(ratios.get("roe"))

    # Recomputed from the two numbers the page prints beside it, so the target,
    # the price and the upside always reconcile. The pre-computed value carried
    # its own price: SUNTECK showed 45.31% from a target of 435.93, which
    # implies a price of 300.00 while the stock was at 294.25.
    target_price = _num(mi.get("consensus_target")) or _num(legacy_consensus.get("target_price"))
    price_now = _num(mi.get("cmp"))
    upside = (round((target_price / price_now - 1.0) * 100.0, 2)
              if target_price and price_now and price_now > 0 else None)
    if upside is None:
        upside = _num(mi.get("consensus_upside"))
    if upside is None:
        upside = _num(legacy_consensus.get("upside"))
    coverage = _num(mi.get("analyst_count"))
    if coverage is None:
        coverage = _num(legacy_consensus.get("coverage"))
    buy_count = _num(legacy_consensus.get("buy_count"))
    # Warehouse consensus uses `buy`; MI universe does not currently expose it.
    if buy_count is None:
        buy_count = _num((legacy_consensus or {}).get("buy"))

    # Measured from prices when available. The file-store value is a stale
    # snapshot and only fills gaps.
    r1 = return_1y
    if r1 is None:
        r1 = _num(legacy_consensus.get("return_1y"))
    if r1 is None:
        # The factor warehouse already carries a bounded 12-minus-1 momentum
        # observation. Use it as the lightweight return context when the
        # expensive daily-history join is intentionally disabled.
        r1 = _num(factors.get("momentum_12_1_pct"))

    consensus = {
        "upside": upside,
        "coverage": coverage,
        "buy_count": buy_count,
        "target_price": target_price,
        "return_1y": r1,
        "return_3y": _num(legacy_consensus.get("return_3y")),
        "source": "warehouse.consensus" if upside is not None or coverage is not None else (
            "valuation_consensus" if legacy_consensus else None
        ),
    }

    return {
        "ticker": sym,
        "company_name": mi.get("company_name") or sym,
        # Most company_master records carry an explicit Upstox instrument key.
        # Some older warehouse rows only have an ISIN, though; NSE equity keys
        # are deterministic from it and let the candle scheduler safely use
        # those records without guessing from a ticker.
        "instrument_key": mi.get("instrument_key") or (
            f"NSE_EQ|{mi.get('isin')}" if mi.get("isin") else None
        ),
        "primary_sector": mi.get("sector"),
        "primary_industry": mi.get("industry"),
        "industry_dna": mi.get("industry_dna"),
        "market_cap": _num(mi.get("market_cap")),
        "price": _num(mi.get("cmp")),
        "pe": _num(mi.get("pe")),
        "forward_pe": _num(mi.get("forward_pe")),
        "pb": _num(mi.get("pb")),
        "ev_ebitda": _num(mi.get("ev_ebitda")),
        "roe": roe,
        "profit_margin": profit_margin,
        "debt_to_equity": debt_to_equity,
        "dividend_yield": _num(mi.get("dividend_yield")),
        "consensus": consensus,
        "factors": {
            "value_score": _num(factors.get("value_score")),
            "quality_score": _num(factors.get("quality_score")),
            "growth_score": _num(factors.get("growth_score")),
            "momentum_score": _num(factors.get("momentum_score")),
            "technical_score": _num(factors.get("technical_score")),
            "trend_score": _num(factors.get("trend_score")),
            "momentum_12_1_pct": _num(factors.get("momentum_12_1_pct")),
            "volume_ratio_20d": _num(factors.get("volume_ratio_20d")),
            "consensus_score": _num(factors.get("consensus_score")),
            "opportunity_score": _num(factors.get("opportunity_score")),
            "strategy_agreement": _num(factors.get("strategy_agreement")),
            "as_of": factors.get("as_of"),
        } if factors else {},
        "source": mi.get("source") or "warehouse",
        "valuation_date": mi.get("valuation_date"),
        "data_context": {
            "valuation_period": mi.get("valuation_date"),
            "fundamentals_period": ratios.get("period"),
            "fundamentals_basis": ratios.get("basis") or "annual",
            "accounting_scope": ratios.get("accounting_scope") or ratios.get("scope") or "not_provided",
            "valuation_source": mi.get("source") or SOURCES["market_data"],
            "fundamentals_source": SOURCES["fundamentals"],
            # The warehouse consensus row carries the date; the legacy file
            # store is only a fallback. Reading the fallback first left every
            # desk row with a null date, so nothing on the page said how old
            # the analyst view was.
            "consensus_date": (mi.get("consensus_date")
                               or (legacy_consensus or {}).get("consensus_date")),
        },
    }


def _universe_from_warehouse() -> list[dict[str, Any]]:
    try:
        from market_intelligence_engine.universe import load_universe
    except Exception:
        return []

    try:
        pack = load_universe(limit=5000)
    except Exception:
        return []
    mi_rows = pack.get("rows") or []
    if not mi_rows:
        return []

    ratios = _latest_ratios_by_symbol()
    factors = _factors_by_symbol()
    returns = _return_1y_by_symbol()
    # The traded close, which historical_valuation.cmp disagrees with for about
    # 90% of symbols.
    closes = _latest_close_by_symbol()

    # Soft-fill buy_count / forward_pe from warehouse tabs when CapIQ file store is thin.
    wh_consensus: dict[str, dict[str, Any]] = {}
    forward_pe_map: dict[str, Optional[float]] = {}
    try:
        from institutional_warehouse import store

        for row in store.all_rows("consensus", limit=10000) or []:
            sym = str(row.get("symbol") or "").upper()
            if not sym:
                continue
            prev = wh_consensus.get(sym)
            if not prev or str(row.get("consensus_date") or "") > str(prev.get("consensus_date") or ""):
                wh_consensus[sym] = row
        val_date = pack.get("valuation_date")
        if val_date:
            for row in store.fetch("historical_valuation", filters={"date": val_date}, limit=5000).get("rows") or []:
                sym = str(row.get("symbol") or "").upper()
                if sym:
                    forward_pe_map[sym] = _num(row.get("forward_pe"))
    except Exception:
        wh_consensus = {}

    # historical_valuation.forward_pe is empty, so it was null across the whole
    # universe and the Forward Earnings Growth and Alpha screens returned
    # nothing at all. Capital IQ's forward estimates cover about 910 companies -
    # the real extent of sell-side coverage here - so derive the multiple for
    # those and leave the rest genuinely unknown rather than guessed.
    forward_eps_map = _forward_eps_by_symbol()

    out: list[dict[str, Any]] = []
    factors_joined = 0
    for mi in mi_rows:
        sym = str(mi.get("symbol") or "").upper()
        if not sym:
            continue
        # Skip shells with no usable multiple and no consensus — scanners need signal.
        if not any(_num(mi.get(k)) is not None for k in ("pe", "pb", "ev_ebitda", "roe", "market_cap")):
            continue
        legacy = _legacy_consensus(sym)
        wh = wh_consensus.get(sym) or {}
        if wh:
            # Prefer warehouse buy / analyst_count when legacy file store is thin.
            if not legacy.get("buy_count") and wh.get("buy") is not None:
                legacy = {**legacy, "buy_count": wh.get("buy"), "buy": wh.get("buy")}
            if not legacy.get("coverage") and wh.get("analyst_count") is not None:
                legacy = {**legacy, "coverage": wh.get("analyst_count")}
            if not legacy.get("target_price") and wh.get("target_price") is not None:
                legacy = {**legacy, "target_price": wh.get("target_price")}
            # Carry the date too, or the desk cannot say how old the analyst
            # view is - every row reported a null consensus_date while the
            # warehouse row was stamped 2026-08-02.
            if wh.get("consensus_date") is not None:
                legacy = {**legacy, "consensus_date": wh.get("consensus_date")}
        fac = factors.get(sym) or {}
        if fac:
            factors_joined += 1
        mapped = _map_warehouse_row(
            {
                **mi,
                "valuation_date": pack.get("valuation_date"),
                # Traded close wins over the valuation table's own cmp.
                "cmp": closes.get(sym) or mi.get("cmp"),
                "forward_pe": (
                    mi.get("forward_pe")
                    if mi.get("forward_pe") is not None
                    else forward_pe_map.get(sym)
                    if forward_pe_map.get(sym) is not None
                    # Last resort: price over FY1 consensus EPS. Both vendor
                    # fields are empty here, so without this the whole universe
                    # has no forward multiple at all.
                    else derived_forward_pe(mi.get("cmp"), forward_eps_map.get(sym))
                ),
            },
            ratios=ratios.get(sym) or {},
            factors=fac,
            return_1y=returns.get(sym),
            legacy_consensus=legacy,
        )
        out.append(mapped)

    _UNIVERSE_META.update(
        {
            "source": "warehouse+market_intelligence",
            "as_of": pack.get("valuation_date"),
            "count": len(out),
            "factors_joined": factors_joined,
        }
    )
    return out


def _universe_from_legacy() -> list[dict[str, Any]]:
    """Fallback when the warehouse has not been populated yet."""
    try:
        from valuation_consensus.store import get_row as consensus_row
        from valuation_terminal.store import all_rows
    except Exception:
        return []

    out: list[dict[str, Any]] = []
    for ticker, row in (all_rows() or {}).items():
        merged = dict(row)
        merged["ticker"] = ticker
        merged["consensus"] = consensus_row(ticker) or {}
        out.append(merged)
    _UNIVERSE_META.update(
        {
            "source": "legacy_valuation_terminal",
            "as_of": None,
            "count": len(out),
            "factors_joined": 0,
        }
    )
    return out


_UNIVERSE_CACHE: dict[str, Any] = {"at": 0.0, "rows": None, "source_id": None}
_UNIVERSE_LOCK = __import__("threading").Lock()
# Keep the joined universe warm across page opens + keep-warm pings.
_UNIVERSE_TTL_SEC = 300.0

_HISTORY_CACHE: dict[str, Any] = {"at": 0.0, "rows": None}
_HISTORY_LOCK = __import__("threading").Lock()
# 139,639 rows scanned once and held. Repeated heavy reads on the request path
# are what took the engine down on 2026-08-19.
_HISTORY_TTL_SEC = 900.0
# Metrics worth carrying per company. The workbook holds fifteen; these are the
# ones the screens actually rank on.
_HISTORY_METRICS = ("pe", "pb", "ev_ebitda", "roe", "roa", "ebitda_margin", "debt_equity")


def _valuation_history_by_symbol(*, limit: int = 200000) -> dict[str, dict[str, dict[str, Any]]]:
    """Ten years of per-company ratios from the Capital IQ workbook.

    `sector_ratio_history` holds 139,639 rows covering 2,627 companies over
    FY2016-FY2025 across fifteen metrics, and until now nothing in the hedge
    fund lab read it - the screens ranked purely on a same-day cross-section.
    That measures whether a stock is cheaper than its neighbours today; it
    cannot say whether it is cheap against its own past, which is the question
    a value screen is actually asking.

    Returns {symbol: {metric: {"median", "years", "first", "last", "latest"}}}.
    Only rows the workbook marked ELIGIBLE are used, so vendor outliers it
    already excluded from its own medians stay excluded here.
    """
    try:
        from institutional_warehouse import store
    except Exception:
        return {}

    buckets: dict[str, dict[str, list[tuple[str, float]]]] = {}
    try:
        for row in store.all_rows("sector_ratio_history", limit=limit) or []:
            if str(row.get("median_eligibility") or "").upper() != "ELIGIBLE":
                continue
            metric = str(row.get("metric") or "").lower()
            symbol = str(row.get("symbol") or "").upper()
            value = _num(row.get("value"))
            year = str(row.get("fiscal_year") or "")
            if not symbol or not year or value is None or metric not in _HISTORY_METRICS:
                continue
            buckets.setdefault(symbol, {}).setdefault(metric, []).append((year, value))
    except Exception:
        return {}

    out: dict[str, dict[str, dict[str, Any]]] = {}
    for symbol, metrics in buckets.items():
        for metric, pairs in metrics.items():
            pairs.sort()
            values = [v for _, v in pairs]
            out.setdefault(symbol, {})[metric] = {
                "median": round(stats.median(values), 4),
                "years": len(values),
                "first": pairs[0][0],
                "last": pairs[-1][0],
                "latest": pairs[-1][1],
            }
    return out


_FORWARD_EPS_CACHE: dict[str, Any] = {"at": 0.0, "rows": None}
_FORWARD_EPS_TTL_SEC = 900.0


def _forward_eps_by_symbol() -> dict[str, float]:
    """{symbol: FY1 consensus EPS}, cached like every other warehouse scan."""
    import time

    now = time.time()
    cached = _FORWARD_EPS_CACHE.get("rows")
    if cached is not None and (now - float(_FORWARD_EPS_CACHE.get("at") or 0.0)) < _FORWARD_EPS_TTL_SEC:
        return cached
    try:
        from financial_warehouse_completion.capiq_forward_estimates import latest_forward_eps

        rows = latest_forward_eps()
    except Exception:
        rows = {}
    _FORWARD_EPS_CACHE["at"] = time.time()
    _FORWARD_EPS_CACHE["rows"] = rows
    return rows


def reset_forward_eps_cache() -> None:
    _FORWARD_EPS_CACHE["at"] = 0.0
    _FORWARD_EPS_CACHE["rows"] = None


def derived_forward_pe(price: Optional[float], eps: Optional[float]) -> Optional[float]:
    """Forward P/E from price and FY1 consensus EPS.

    Guards the loss-making case explicitly: a negative EPS produces a negative
    multiple that sorts as though it were the cheapest name on the desk.
    """
    price, eps = _num(price), _num(eps)
    if price is None or eps is None or price <= 0 or eps <= 0:
        return None
    return round(price / eps, 2)


def _served_stale(cache: dict[str, Any], lock: Any, ttl: float,
                  builder: Any, label: str) -> Any:
    """Answer from the cache, refresh behind the answer.

    A heavy cache that rebuilds on whichever request arrives after it expires
    makes that client pay for the whole scan while the rest queue behind the
    lock. `sector_ratio_history` is 139,639 rows and that turnover measured 39
    seconds in production.

    An expired answer is still an answer. It is served, the rebuild runs on its
    own thread, and the only request that waits is one with nothing to serve.
    """
    import threading
    import time

    cached = cache.get("rows")
    fresh = cached is not None and (time.time() - float(cache.get("at") or 0.0)) < ttl

    if cached is not None and not fresh and not cache.get("building"):
        cache["building"] = True

        def _refresh() -> None:
            try:
                rows = builder()
                if rows:
                    cache["rows"] = rows
                    cache["at"] = time.time()
            except Exception:
                # The previous value stays. A failed refresh must not empty a
                # cache that was serving good answers a moment earlier.
                pass
            finally:
                cache["building"] = False

        threading.Thread(target=_refresh, name=f"cache-refresh-{label}", daemon=True).start()

    if cached is not None:
        return cached

    with lock:
        cached = cache.get("rows")
        if cached is not None:
            return cached
        rows = builder()
        cache["at"] = time.time()
        cache["rows"] = rows
        return rows


def _history_index() -> dict[str, dict[str, dict[str, Any]]]:
    return _served_stale(_HISTORY_CACHE, _HISTORY_LOCK, _HISTORY_TTL_SEC,
                         _valuation_history_by_symbol, "history")


def reset_history_cache() -> None:
    """Process-global state has to be clearable or tests leak into each other."""
    _HISTORY_CACHE["at"] = 0.0
    _HISTORY_CACHE["rows"] = None


def own_history_context(ticker: str, metric: str, value: Optional[float]) -> dict[str, Any]:
    """Where today's multiple sits against this company's own ten-year record.

    A negative `discount_vs_own_pct` means the stock is cheaper than its own
    history on a metric where lower is cheaper. Returns an explicit reason when
    no comparison is possible rather than a silent null, because "no history"
    and "no discount" are different findings.
    """
    entry = ((_history_index().get(str(ticker).upper()) or {}).get(str(metric).lower()) or {})
    median = _num(entry.get("median"))
    if value is None or median is None or median <= 0:
        return {"available": False, "reason": "no_eligible_history" if median is None else "no_current_value"}
    return {
        "available": True,
        "own_median": median,
        "years": entry.get("years"),
        "span": f"{entry.get('first')}-{entry.get('last')}",
        "discount_vs_own_pct": round(((value / median) - 1.0) * 100.0, 1),
    }


def _build_universe() -> list[dict[str, Any]]:
    """The expensive part: join the warehouse into one universe."""
    rows = _universe_from_warehouse()
    if not rows:
        rows = _universe_from_legacy()
    return rows


def _universe() -> list[dict[str, Any]]:
    """Companies with market multiples (+ consensus / factors when available).

    This used to rebuild inside whichever request arrived after the cache
    expired, behind a lock, so the client's wait was the rebuild's duration -
    200 seconds after a restart, 12 to 25 on a normal turnover, and a timeout
    when a backfill slice was running.

    It now returns whatever is on hand and refreshes behind the request. A
    slightly old universe answered immediately is worth more than a current one
    answered in twenty seconds, and the age is reported rather than hidden.
    """
    return desk_snapshot.current(_build_universe, source="warehouse")


def universe_snapshot_status() -> dict[str, Any]:
    return desk_snapshot.status()


def rebuild_universe_snapshot() -> dict[str, Any]:
    """Force a rebuild now. Used at boot and by the scheduled warmer."""
    return desk_snapshot.rebuild(_build_universe, source="warehouse")


def _primary_metric(dna: Optional[str]) -> str:
    try:
        from valuation_terminal.sector_lens import lens_for

        return lens_for(dna)["primary_metric"]
    except Exception:
        return "pe"


def _industry_medians(universe: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in universe:
        industry = row.get("primary_industry")
        if industry:
            groups.setdefault(industry, []).append(row)
    out: dict[str, dict[str, Any]] = {}
    for industry, members in groups.items():
        out[industry] = {
            "count": len(members),
            "pe": _median([_sane(m, "pe") for m in members]),
            "pb": _median([_sane(m, "pb") for m in members]),
            "ev_ebitda": _median([_sane(m, "ev_ebitda") for m in members]),
            "roe": _median([_sane(m, "roe") for m in members]),
            "dividend_yield": _median([m.get("dividend_yield") for m in members]),
            "return_1y": _median([(m.get("consensus") or {}).get("return_1y") for m in members]),
            "profit_margin": _median([_sane(m, "profit_margin") for m in members]),
        }
    return out


def _base(row: dict[str, Any]) -> dict[str, Any]:
    consensus = row.get("consensus") or {}
    return {
        "ticker": row["ticker"],
        "company_name": row.get("company_name"),
        "instrument_key": row.get("instrument_key"),
        "sector": row.get("primary_sector"),
        "industry": row.get("primary_industry"),
        "market_cap": row.get("market_cap"),
        "consensus_upside": consensus.get("upside"),
        "coverage": consensus.get("coverage"),
        "return_1y": consensus.get("return_1y"),
        "data_context": row.get("data_context") or {},
    }


# ---------------------------------------------------------------------------
# Market regime, derived from the universe itself
# ---------------------------------------------------------------------------
def market_regime() -> dict[str, Any]:
    universe = _universe()
    if not universe:
        return {"ok": False, "error": "universe_empty"}

    returns = [
        _num((r.get("consensus") or {}).get("return_1y"))
        for r in universe
        if _num((r.get("consensus") or {}).get("return_1y")) is not None
    ]
    positive_1y = sum(1 for r in returns if r > 0)
    positive_1y_pct = round((positive_1y / len(returns)) * 100.0, 1) if returns else None
    median_return = _median(returns)
    median_pe = _median([r.get("pe") for r in universe])
    median_upside = _median([(r.get("consensus") or {}).get("upside") for r in universe])

    if positive_1y_pct is None:
        stance = "Unknown"
    elif positive_1y_pct >= 60 and (median_return or 0) > 5:
        stance = "Risk On"
    elif positive_1y_pct <= 40:
        stance = "Risk Off"
    else:
        stance = "Mixed"

    # Strategy suitability follows the regime, not a fixed opinion.
    def stars(n: int) -> int:
        return max(1, min(5, n))

    risk_on = stance == "Risk On"
    risk_off = stance == "Risk Off"
    suitability = [
        {
            "strategy": "Long / Short Equity",
            "stars": stars(5 if stance == "Mixed" else 4),
            "why": "Pays on dispersion, which is widest when the market is not moving as one.",
        },
        {
            "strategy": "Momentum / CTA Trend",
            "stars": stars(5 if risk_on else 2),
            "why": "Needs sustained direction; chops up in range-bound tape.",
        },
        {
            "strategy": "Equity Market Neutral",
            "stars": stars(4 if not risk_off else 3),
            "why": "Independent of direction, but vulnerable to factor unwinds in stress.",
        },
        {
            "strategy": "Value / Deep Value",
            "stars": stars(4 if median_pe and median_pe > 25 else 3),
            "why": "Dispersion in multiples creates the gap value strategies close.",
        },
        {
            "strategy": "Merger Arbitrage",
            "stars": stars(2 if risk_off else 3),
            "why": "Spread capture depends on deals closing and credit staying open.",
        },
        {
            "strategy": "Distressed",
            "stars": stars(4 if risk_off else 2),
            "why": "Feeds on forced selling, which only appears under stress.",
        },
    ]

    return {
        "ok": True,
        "stance": stance,
        "classification_type": "agi_model_output",
        "positive_1y_return_pct": positive_1y_pct,
        # Backward-compatible field. This is not daily advancing breadth.
        "breadth_advancing_pct": positive_1y_pct,
        "median_return_1y_pct": median_return,
        "median_pe": median_pe,
        "median_consensus_upside_pct": median_upside,
        "universe": len(universe),
        "universe_meta": universe_meta(),
        "strategy_suitability": suitability,
        "methodology": {
            "definition": "AGI model classification from covered-universe one-year returns and valuation.",
            "drivers": "covered-universe 1Y positive-return breadth, median 1Y return and valuation",
            "positive_1y_return_formula": "companies with 1Y return > 0 / companies with a valid 1Y return",
            "period": "latest stored observation with trailing one-year return",
            "universe": "covered warehouse universe",
            "exclusions": "companies without a valid one-year return",
            "source": SOURCES["market_data"],
            "timestamp": universe_meta().get("as_of"),
        },
        "note": "Risk stance is an AGI model output, not an objective market fact or live daily breadth reading.",
    }


# ---------------------------------------------------------------------------
# Scanners
# ---------------------------------------------------------------------------
def _scan_value(universe, medians, limit) -> list[dict[str, Any]]:
    out = []
    for row in universe:
        industry = row.get("primary_industry")
        med = medians.get(industry) or {}
        if (med.get("count") or 0) < 5:
            continue
        metric = _primary_metric(row.get("industry_dna"))
        value, benchmark = _sane(row, metric), _num(med.get(metric))
        roe, roe_med = _sane(row, "roe"), _num(med.get("roe"))
        if value is None or not benchmark or value <= 0:
            continue
        discount = round(((value / benchmark) - 1.0) * 100.0, 1)
        if discount > -25:
            continue
        # A cheap multiple with sub-par returns is a trap, not value.
        trap = roe is not None and roe_med is not None and roe < roe_med
        # Previously every EV/EBITDA row was flagged regardless of value, so the
        # status could not separate a plausible 8x from an impossible 1.03x.
        normalization_required = _suspect_multiple(metric, value) or discount <= -75
        classification = (
            "Potential value trap"
            if trap
            else "Headline discount — normalization required"
            if normalization_required
            else "Relative-value research candidate"
        )
        # A cross-sectional discount says the stock is cheaper than its
        # neighbours today. It cannot say whether the whole industry re-rated,
        # which is why the same screen flags a sector-wide de-rating as value.
        # The ten-year record answers that separately.
        own = own_history_context(row["ticker"], metric, value)
        out.append(
            {
                **_base(row),
                "metric": metric,
                "value": value,
                "industry_median": benchmark,
                "discount_pct": discount,
                "vs_own_history": own,
                "roe": roe,
                "industry_median_roe": roe_med,
                "classification": classification,
                "validation_status": "normalization_required" if normalization_required else "screen_validated",
                "relative_multiple": round(value / benchmark, 2),
                "why": (
                    f"Trades at {value} on {metric.upper()} against an industry median of "
                    f"{benchmark}, a {abs(discount)}% discount"
                    + (
                        f", but return on equity of {roe}% is below the industry's {roe_med}% — "
                        "the discount may be deserved."
                        if trap
                        else f", while return on equity of {roe}% is at or above the industry's "
                        f"{roe_med}%." if roe is not None and roe_med is not None
                        else "."
                    )
                    + (
                        f" Against its own {own['span']} record it trades "
                        f"{abs(own['discount_vs_own_pct'])}% {'below' if own['discount_vs_own_pct'] < 0 else 'above'} "
                        f"a {own['years']}-year median of {own['own_median']}."
                        if own.get("available") else ""
                    )
                    + (" This is a headline multiple. Validate the underlying EBITDA and reconcile enterprise-value adjustments before drawing a valuation conclusion." if normalization_required else "")
                ),
            }
        )
    out.sort(key=lambda r: (r["validation_status"] != "screen_validated", r["discount_pct"]))
    return out[:limit]


def _scan_quality(universe, medians, limit) -> list[dict[str, Any]]:
    out = []
    for row in universe:
        roe = _sane(row, "roe")
        margin = _sane(row, "profit_margin")
        debt = _sane(row, "debt_to_equity")
        if roe is None or margin is None or roe < 15 or margin < 10:
            continue
        if debt is not None and debt > 150:
            continue
        out.append(
            {
                **_base(row),
                "roe": roe,
                "profit_margin": margin,
                "debt_to_equity": debt,
                "quality_score": round(min(100.0, roe + margin / 2 - (debt or 0) / 20), 1),
                "validation_status": "accounting_basis_verification_required" if debt is not None and (row.get("data_context") or {}).get("accounting_scope") == "not_provided" else "screen_validated",
                "debt_to_equity_basis": {
                    "status": "verify_accounting_basis" if debt is not None and (row.get("data_context") or {}).get("accounting_scope") == "not_provided" else "reported_basis_available",
                    "period": (row.get("data_context") or {}).get("fundamentals_period"),
                    "scope": (row.get("data_context") or {}).get("accounting_scope"),
                    "debt_definition": "not_provided",
                    "lease_liabilities_included": "not_provided",
                    "equity_basis": "not_provided",
                    "source": (row.get("data_context") or {}).get("fundamentals_source"),
                },
                "why": (
                    f"Return on equity of {roe}% on a {margin}% net margin"
                    + (f" with debt/equity at {debt}x — verify accounting basis" if debt is not None and (row.get("data_context") or {}).get("accounting_scope") == "not_provided" else f" with debt/equity at {debt}x" if debt is not None else "")
                    + " — the profitability profile institutions screen for."
                ),
            }
        )
    out.sort(key=lambda r: -r["quality_score"])
    return out[:limit]


def _scan_momentum(universe, medians, limit) -> list[dict[str, Any]]:
    out = []
    for row in universe:
        consensus = row.get("consensus") or {}
        r1 = _num(consensus.get("return_1y"))
        industry = row.get("primary_industry")
        med = (medians.get(industry) or {}).get("return_1y")
        if r1 is None or r1 < 35:
            continue
        relative = round(r1 - (_num(med) or 0.0), 1)
        if relative < 15:
            continue
        out.append(
            {
                **_base(row),
                "return_1y": r1,
                "return_3y": consensus.get("return_3y"),
                "industry_median_return_1y": med,
                "relative_strength": relative,
                "why": (
                    f"Up {r1}% over a year against an industry median of {med}%, "
                    f"a relative strength of {relative} points."
                ),
            }
        )
    out.sort(key=lambda r: -r["relative_strength"])
    return out[:limit]


def _scan_conviction(universe, medians, limit) -> list[dict[str, Any]]:
    out = []
    for row in universe:
        consensus = row.get("consensus") or {}
        coverage = _num(consensus.get("coverage")) or 0
        buy = _num(consensus.get("buy_count")) or 0
        upside = _num(consensus.get("upside"))
        if coverage < 8 or upside is None:
            continue
        share = round((buy / coverage) * 100.0, 1) if coverage else 0.0
        if share < 60:
            continue
        out.append(
            {
                **_base(row),
                "buy_share_pct": share,
                "buy": buy,
                "consensus_upside": upside,
                "why": (
                    f"{int(buy)} of {int(coverage)} brokers positive ({share}%) with "
                    f"{upside}% implied upside — high sell-side conviction, which is an "
                    "expectation to test rather than accept."
                ),
            }
        )
    out.sort(key=lambda r: -(r["buy_share_pct"] * (r["consensus_upside"] or 0)))
    return out[:limit]


def _scan_stress(universe, medians, limit) -> list[dict[str, Any]]:
    out = []
    for row in universe:
        debt = _sane(row, "debt_to_equity")
        margin = _sane(row, "profit_margin")
        r1 = _num((row.get("consensus") or {}).get("return_1y"))
        flags = []
        if debt is not None and debt > 150:
            flags.append(f"debt/equity at {debt}")
        if margin is not None and margin < 0:
            flags.append(f"negative net margin of {margin}%")
        if r1 is not None and r1 < -20:
            flags.append(f"shares down {abs(r1)}% over a year")
        if len(flags) < 2:
            continue
        out.append(
            {
                **_base(row),
                "debt_to_equity": debt,
                "profit_margin": margin,
                "stress_flags": flags,
                "why": "Balance sheet and price both signalling stress: " + "; ".join(flags) + ".",
            }
        )
    out.sort(key=lambda r: -(len(r["stress_flags"])))
    return out[:limit]


def _scan_pairs(universe, medians, limit) -> list[dict[str, Any]]:
    """Valuation-spread research candidates, not a statistical-arbitrage signal."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in universe:
        industry = row.get("primary_industry")
        metric = _primary_metric(row.get("industry_dna"))
        value = _sane(row, metric)
        if industry and value and value > 0:
            groups.setdefault(industry, []).append({**row, "_metric": metric, "_value": value})

    out = []
    for industry, members in groups.items():
        if len(members) < 6:
            continue
        members.sort(key=lambda m: m["_value"])
        cheap, rich = members[0], members[-1]
        spread = round((rich["_value"] / cheap["_value"]), 2)
        if spread < 2.0:
            continue
        metric = cheap["_metric"]
        out.append(
            {
                "industry": industry,
                "metric": metric,
                "long_leg": {
                    **_base(cheap),
                    "value": cheap["_value"],
                    "roe": cheap.get("roe"),
                },
                "short_leg": {
                    **_base(rich),
                    "value": rich["_value"],
                    "roe": rich.get("roe"),
                },
                "spread_multiple": spread,
                "industry_median": (medians.get(industry) or {}).get(metric),
                "peers": len(members),
                "classification": "Valuation dispersion candidate",
                "comparability_status": "fundamental_comparability_required",
                "promotion_status": "not_market_neutral",
                "required_tests": [
                    "business-model and revenue-driver comparability",
                    "rolling return correlation and beta",
                    "cointegration and spread stationarity",
                    "factor exposure neutrality",
                    "liquidity, borrow cost and slippage",
                    "costed point-in-time backtest",
                ],
                "why": (
                    f"Within {industry}, {cheap.get('company_name')} trades at "
                    f"{cheap['_value']} on {metric.upper()} while "
                    f"{rich.get('company_name')} trades at {rich['_value']} — a "
                    f"{spread}× headline valuation dispersion across {len(members)} industry members. "
                    "Industry membership alone does not establish economic comparability or market neutrality."
                ),
                "caution": (
                    "Valuation gaps within an industry usually reflect real differences in "
                    "returns, growth or governance. Check those before treating the spread "
                    "as mispricing."
                ),
            }
        )
    out.sort(key=lambda r: -r["spread_multiple"])
    return out[:limit]


def _scan_technical(universe, medians, limit) -> list[dict[str, Any]]:
    """Technical confirmation from nightly, end-of-day warehouse factors.

    We require both an established trend and an independently calculated 12–1
    momentum score. This deliberately avoids calling live market vendors while
    a user has the terminal open.
    """
    out = []
    for row in universe:
        factors = row.get("factors") or {}
        score = _num(factors.get("technical_score"))
        trend = _num(factors.get("trend_score"))
        momentum = _num(factors.get("momentum_12_1_pct"))
        if score is None or trend is None or momentum is None:
            continue
        if score < 65 or trend < 75 or momentum <= 0:
            continue
        volume_ratio = _num(factors.get("volume_ratio_20d"))
        out.append(
            {
                **_base(row),
                "technical_score": score,
                "trend_score": trend,
                "momentum_12_1_pct": momentum,
                "volume_ratio_20d": volume_ratio,
                "factor_as_of": factors.get("as_of"),
                "why": (
                    f"Technical score {score} with trend score {trend} and 12–1 momentum of "
                    f"{momentum}% (latest 21 sessions excluded)"
                    + (f"; 20-day volume is {volume_ratio}× the preceding 20 days." if volume_ratio is not None else ".")
                    + " Confirm price structure and liquidity before treating this as a timing signal."
                ),
            }
        )
    out.sort(key=lambda r: (-r["technical_score"], -r["momentum_12_1_pct"]))
    return out[:limit]


def _scan_alpha(universe, medians, limit) -> list[dict[str, Any]]:
    """Multi-factor research queue with every component exposed.

    A composite is surfaced only when at least three independently refreshed
    components exist. The output is a research priority, never a trade or a
    probability of return.
    """
    out = []
    weights = {
        "value": 0.30,
        "quality": 0.30,
        "growth": 0.25,
        "consensus": 0.15,
    }
    for row in universe:
        factors = row.get("factors") or {}
        components = {
            "value": _num(factors.get("value_score")),
            "quality": _num(factors.get("quality_score")),
            "growth": _num(factors.get("growth_score")),
            "consensus": _num(factors.get("consensus_score")),
        }
        available = {name: value for name, value in components.items() if value is not None}
        if len(available) < 3:
            continue
        total_weight = sum(weights[name] for name in available)
        composite = round(sum(value * weights[name] for name, value in available.items()) / total_weight, 1)
        agreement = sum(1 for value in available.values() if value >= 60)
        if composite < 62 or agreement < 3:
            continue
        debt = _sane(row, "debt_to_equity")
        margin = _sane(row, "profit_margin")
        risks = []
        if debt is not None and debt > 200:
            risks.append("elevated leverage")
        if margin is not None and margin < 0:
            risks.append("negative profitability")
        evidence = ", ".join(f"{name.title()} {value:.0f}" for name, value in available.items())
        out.append(
            {
                **_base(row),
                "alpha_opportunity_score": composite,
                "factor_agreement": agreement,
                "factor_scores": available,
                "factor_as_of": factors.get("as_of"),
                "risk_flags": risks,
                "classification": "Needs risk review" if risks else "Multi-factor research candidate",
                "why": (
                    f"{agreement} of {len(available)} available factors are supportive: {evidence}. "
                    f"Composite research score {composite}."
                    + (f" Risk flags: {', '.join(risks)}." if risks else "")
                    + " Validate the next catalyst, estimate changes and downside before acting."
                ),
            }
        )
    out.sort(key=lambda r: (-r["alpha_opportunity_score"], -r["factor_agreement"]))
    return out[:limit]


_SCANNERS = {
    "alpha": ("Alpha opportunity", _scan_alpha),
    "value": ("Value", _scan_value),
    "quality": ("Quality", _scan_quality),
    "conviction": ("Consensus conviction", _scan_conviction),
    "stress": ("Stress", _scan_stress),
    "pairs": ("Valuation dispersion candidates", _scan_pairs),
}


def scan(strategy: str, *, limit: int = 15, sector: Optional[str] = None) -> dict[str, Any]:
    key = str(strategy or "").strip().lower()
    if key in {"technical", "momentum"}:
        return {
            "ok": False,
            "error": "technical_research_paused",
            "message": "Technical and momentum scans are paused. Alpha currently uses fundamentals and earnings consensus only.",
            "available": sorted(_SCANNERS),
        }
    if key not in _SCANNERS:
        return {"ok": False, "error": "unknown_scan", "available": sorted(_SCANNERS)}

    universe = _universe()
    if sector:
        universe = [r for r in universe if str(r.get("primary_sector") or "").lower() == sector.lower()]
    if not universe:
        return {"ok": False, "error": "universe_empty"}

    medians = _industry_medians(universe)
    label, fn = _SCANNERS[key]
    results = fn(universe, medians, max(1, min(50, int(limit or 15))))
    return {
        "ok": True,
        "scan": key,
        "label": label,
        "universe_scanned": len(universe),
        "results": results,
        "count": len(results),
        "sources": dict(SOURCES),
        "universe_meta": universe_meta(),
        "policy": "Research observations only — no buy, sell or price target.",
    }


def daily_monitor(limit: int = 6) -> dict[str, Any]:
    """The evening sweep: what moved and what stands out today."""
    universe = _universe()
    if not universe:
        return {"ok": False, "error": "universe_empty"}
    medians = _industry_medians(universe)
    return {
        "ok": True,
        "regime": market_regime(),
        "sections": [
            {"id": key, "label": label, "results": fn(universe, medians, limit)}
            for key, (label, fn) in _SCANNERS.items()
        ],
        "universe": len(universe),
        "universe_meta": universe_meta(),
        "sources": dict(SOURCES),
        "policy": "Research observations only — no buy, sell or price target.",
    }
