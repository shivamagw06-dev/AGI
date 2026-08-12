"""Live strategy scanner — runs strategies across the NSE universe.

Every candidate carries the reason it surfaced. These are research
observations built from market data, never recommendations: no buy, no sell,
no price target of AGI's own.
"""

from __future__ import annotations

import os
import statistics as stats
from typing import Any, Optional


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
    "ev_ebitda": (1.0, 80.0),
    "ev_sales": (0.05, 60.0),
    "roe": (-100.0, 150.0),
    "profit_margin": (-100.0, 100.0),
    "dividend_yield": (0.0, 25.0),
    "debt_to_equity": (0.0, 1000.0),
}


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


def _return_1y_by_symbol(*, limit: int = 200000) -> dict[str, Optional[float]]:
    """Optional 1Y price returns from daily_market_history.

    Default is OFF. Scanning up to 200k history rows on every cold universe
    build made Hedge Fund / Market Intelligence opens multi-minute and could
    tip the Render box into 502s. Scanners already fall back to consensus
    ``return_1y`` when this map is empty. Set HFL_LOAD_PRICE_RETURNS=1 to
    re-enable the expensive path.
    """
    flag = (os.getenv("HFL_LOAD_PRICE_RETURNS") or "").strip().lower()
    if flag not in ("1", "true", "yes", "on"):
        return {}
    try:
        from institutional_warehouse import store
    except Exception:
        return {}
    by_sym: dict[str, list[tuple[str, float]]] = {}
    # Hard-cap even when enabled — never read the whole history table in-request.
    capped = max(1000, min(int(limit or 200000), 40_000))
    try:
        for row in store.all_rows("daily_market_history", limit=capped) or []:
            sym = str(row.get("symbol") or "").upper()
            close = _num(row.get("close") or row.get("adj_close"))
            day = str(row.get("date") or "")
            if not sym or close is None or not day:
                continue
            by_sym.setdefault(sym, []).append((day, close))
    except Exception:
        return {}

    out: dict[str, Optional[float]] = {}
    for sym, points in by_sym.items():
        points.sort(key=lambda p: p[0])
        if len(points) < 2:
            continue
        last_px = points[-1][1]
        # Prefer ~252 trading sessions back; else first available print.
        base_px = points[max(0, len(points) - 253)][1]
        if not base_px:
            continue
        out[sym] = round(((last_px / base_px) - 1.0) * 100.0, 2)
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

    r1 = return_1y
    if r1 is None:
        r1 = _num(legacy_consensus.get("return_1y"))

    consensus = {
        "upside": upside,
        "coverage": coverage,
        "buy_count": buy_count,
        "target_price": _num(mi.get("consensus_target")) or _num(legacy_consensus.get("target_price")),
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
            "consensus_date": (legacy_consensus or {}).get("consensus_date"),
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
        fac = factors.get(sym) or {}
        if fac:
            factors_joined += 1
        mapped = _map_warehouse_row(
            {
                **mi,
                "valuation_date": pack.get("valuation_date"),
                "forward_pe": mi.get("forward_pe") if mi.get("forward_pe") is not None else forward_pe_map.get(sym),
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


_UNIVERSE_CACHE: dict[str, Any] = {"at": 0.0, "rows": None}
# Keep the joined universe warm across page opens + keep-warm pings.
_UNIVERSE_TTL_SEC = 300.0


def _universe() -> list[dict[str, Any]]:
    """Companies with market multiples (+ consensus / factors when available).

    Prefers the institutional warehouse via Market Intelligence (Upstox ratios,
    HVIE valuation, CapIQ consensus tabs). Falls back to the Yahoo-era file
    store only when the warehouse universe is empty.
    """
    import time

    now = time.time()
    cached = _UNIVERSE_CACHE.get("rows")
    if cached is not None and (now - float(_UNIVERSE_CACHE.get("at") or 0.0)) < _UNIVERSE_TTL_SEC:
        return cached

    rows = _universe_from_warehouse()
    if not rows:
        rows = _universe_from_legacy()
    _UNIVERSE_CACHE["at"] = now
    _UNIVERSE_CACHE["rows"] = rows
    return rows


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
        normalization_required = metric == "ev_ebitda" or discount <= -75
        classification = (
            "Potential value trap"
            if trap
            else "Headline discount — normalization required"
            if normalization_required
            else "Relative-value research candidate"
        )
        out.append(
            {
                **_base(row),
                "metric": metric,
                "value": value,
                "industry_median": benchmark,
                "discount_pct": discount,
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
                    + (" This is a headline multiple. Validate the underlying EBITDA and reconcile enterprise-value adjustments before drawing a valuation conclusion." if normalization_required else "")
                ),
            }
        )
    out.sort(key=lambda r: r["discount_pct"])
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
