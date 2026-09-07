"""Market multiples + light fundamentals for subject and peers."""

from __future__ import annotations

from typing import Any

from ownership_intelligence.dates import parse_nse_date


def _f(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def fetch_quote(ticker: str, *, force: bool = False, injected: dict[str, Any] | None = None) -> dict[str, Any]:
    if injected is not None:
        return {
            "ok": injected.get("ltp") is not None,
            "ticker": ticker.upper(),
            "ltp": _f(injected.get("ltp")),
            "provider": injected.get("provider") or "injected",
            "as_of": injected.get("as_of"),
        }
    try:
        from live_market_context.providers import fetch_best_quote

        q = fetch_best_quote(ticker, force=force)
        return {
            "ok": bool(q.get("ok") and q.get("ltp") is not None),
            "ticker": ticker.upper(),
            "ltp": _f(q.get("ltp")),
            "provider": q.get("provider"),
            "as_of": q.get("as_of"),
            "volume": q.get("volume"),
            "lineage": q.get("lineage") or [],
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "ticker": ticker.upper(), "ltp": None, "error": str(exc)[:160]}


def light_fundamentals(
    ticker: str,
    *,
    opener=None,
    injected_earnings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Light NSE fundamentals for peers (integrated EPS) or full earnings pack for subject."""
    key = ticker.upper()
    if injected_earnings is not None:
        # Already-normalised light fundamentals (tests / peer cache)
        if injected_earnings.get("ttm_eps") is not None or injected_earnings.get("ttm_pat") is not None:
            return {"ticker": key, **injected_earnings, "ok": injected_earnings.get("ok", True)}
        return _from_earnings_pack(key, injected_earnings)

    # Prefer full earnings pack when cheap path requested via analyse subject;
    # peers use integrated feed only for speed.
    try:
        from earnings_intelligence.discovery import discover_filings

        idx = discover_filings(key, opener=opener)
        q = list(idx.get("quarterly") or [])
        # TTM EPS from last 4 diluted EPS prints in raw_summary
        eps_vals = []
        pat_vals = []
        rev_vals = []
        for row in q[:4]:
            summary = row.get("raw_summary") or {}
            # Prefer already-parsed statements if present
            st = (row.get("statements") or {}).get("income_statement") or {}
            eps = _f(st.get("eps_basic") or st.get("eps_diluted") or summary.get("reDilEPS"))
            pat = _f(st.get("pat_owners") or st.get("pat") or summary.get("proLossAftTax"))
            rev = _f(st.get("revenue_from_operations") or summary.get("income"))
            # Integrated income/PAT often in lakhs
            if summary.get("income") is not None and st.get("revenue_from_operations") is None:
                try:
                    rev = float(summary["income"]) * 100_000.0
                except (TypeError, ValueError):
                    pass
            if summary.get("proLossAftTax") is not None and st.get("pat") is None:
                try:
                    pat = float(summary["proLossAftTax"]) * 100_000.0
                except (TypeError, ValueError):
                    pass
            if eps is not None:
                eps_vals.append(eps)
            if pat is not None:
                pat_vals.append(pat)
            if rev is not None:
                rev_vals.append(rev)
        ttm_eps = round(sum(eps_vals), 4) if len(eps_vals) >= 4 else (round(eps_vals[0] * 4, 4) if len(eps_vals) == 1 else None)
        if ttm_eps is None and len(eps_vals) >= 2:
            ttm_eps = round(sum(eps_vals) * (4 / len(eps_vals)), 4)
        ttm_pat = round(sum(pat_vals), 2) if len(pat_vals) >= 4 else None
        ttm_rev = round(sum(rev_vals), 2) if len(rev_vals) >= 4 else None
        latest_q = q[0] if q else None
        return {
            "ticker": key,
            "ok": ttm_eps is not None or ttm_pat is not None or ttm_rev is not None,
            "ttm_eps": ttm_eps,
            "ttm_pat": ttm_pat,
            "ttm_revenue": ttm_rev,
            "latest_quarter": (latest_q or {}).get("period_end"),
            "source": "nse_integrated_light",
            "quarters_used": len(eps_vals) or len(pat_vals) or len(rev_vals),
        }
    except Exception as exc:  # noqa: BLE001
        return {"ticker": key, "ok": False, "error": str(exc)[:160]}


def _from_earnings_pack(ticker: str, pack: dict[str, Any]) -> dict[str, Any]:
    ttm = pack.get("ttm") or {}
    ttm_inc = (ttm.get("income_statement") or {}) if ttm.get("available") else {}
    lq = pack.get("latest_quarter") or {}
    la = pack.get("latest_annual") or {}
    lq_inc = lq.get("income_statement") or {}
    la_inc = la.get("income_statement") or {}
    la_bal = la.get("balance_sheet") or {}
    la_cf = la.get("cash_flow") or {}
    la_m = ((pack.get("metrics") or {}).get("latest_annual") or {})
    lq_m = ((pack.get("metrics") or {}).get("latest_quarter") or {})
    yoy = ((pack.get("metrics") or {}).get("yoy_growth") or {})

    ttm_eps = _f(ttm_inc.get("eps_basic"))
    if ttm_eps is None:
        # sum last 4 quarter eps
        eps = []
        for row in (pack.get("quarter_history") or [])[:4]:
            e = _f(((row.get("income_statement") or {}).get("eps_basic")))
            if e is not None:
                eps.append(e)
        if len(eps) >= 4:
            ttm_eps = round(sum(eps), 4)
        elif len(eps) == 1:
            ttm_eps = round(eps[0] * 4, 4)

    equity = _f(la_bal.get("total_equity") or la_bal.get("equity_owners"))
    debt = _f(la_bal.get("total_debt"))
    cash = _f(la_bal.get("cash"))
    net_debt = None
    if debt is not None:
        net_debt = round(debt - float(cash or 0.0), 2)

    shares = _f(la_bal.get("shares_outstanding"))
    face = _f(la_bal.get("face_value"))
    esc = _f(la_bal.get("equity_share_capital"))
    if shares is None and esc not in (None, 0) and face not in (None, 0):
        shares = round(esc / face, 2)
    # If EPS still missing but shares known, imply TTM EPS from PAT
    ttm_pat = _f(ttm_inc.get("pat_owners") or ttm_inc.get("pat"))
    if ttm_eps is None and ttm_pat is not None and shares not in (None, 0):
        ttm_eps = round(ttm_pat / shares, 4)

    return {
        "ticker": ticker,
        "ok": True,
        "ttm_eps": ttm_eps,
        "ttm_pat": ttm_pat,
        "ttm_revenue": _f(ttm_inc.get("revenue_from_operations")),
        "ttm_ebitda": _f(ttm_inc.get("ebitda")),
        "ttm_ebit": _f(ttm_inc.get("ebit")),
        "latest_quarter": lq.get("period_end"),
        "latest_annual": la.get("period_end"),
        "equity": equity,
        "equity_share_capital": esc,
        "total_assets": _f(la_bal.get("total_assets")),
        "cash": cash,
        "total_debt": debt,
        "net_debt": net_debt,
        "shares_outstanding": shares,
        "face_value": face,
        "roe_pct": _f(la_m.get("roe_pct")),
        "roce_pct": _f(la_m.get("roce_pct")),
        "ebitda_margin_pct": _f(lq_m.get("ebitda_margin_pct") or la_m.get("ebitda_margin_pct")),
        "ebit_margin_pct": _f(lq_m.get("ebit_margin_pct") or la_m.get("ebit_margin_pct")),
        "pat_margin_pct": _f(lq_m.get("pat_margin_pct") or la_m.get("pat_margin_pct")),
        "debt_to_equity": _f(la_m.get("debt_to_equity")),
        "fcf": _f(la_cf.get("free_cash_flow")),
        "ocf": _f(la_cf.get("operating_cash_flow")),
        "revenue_growth_yoy_pct": _f(yoy.get("revenue_growth_pct")),
        "pat_growth_yoy_pct": _f(yoy.get("pat_growth_pct")),
        "eps_growth_yoy_pct": _f(yoy.get("eps_growth_pct")),
        "annual_history": pack.get("annual_history") or [],
        "quarter_history": pack.get("quarter_history") or [],
        "source": "earnings_intelligence_pack",
        "coverage_pct": pack.get("coverage_pct"),
    }


def compute_multiples(
    *,
    price: float | None,
    fundamentals: dict[str, Any],
    market_cap: float | None = None,
) -> dict[str, Any]:
    eps = _f(fundamentals.get("ttm_eps"))
    rev = _f(fundamentals.get("ttm_revenue"))
    ebitda = _f(fundamentals.get("ttm_ebitda"))
    equity = _f(fundamentals.get("equity"))
    net_debt = _f(fundamentals.get("net_debt"))
    ocf = _f(fundamentals.get("ocf"))
    growth = _f(fundamentals.get("eps_growth_yoy_pct") or fundamentals.get("pat_growth_yoy_pct"))

    # Market cap first so we can fall back to mcap / PAT for PE when EPS missing
    mcap = market_cap
    pat = _f(fundamentals.get("ttm_pat"))
    pe = round(price / eps, 4) if price and eps not in (None, 0) else None
    if pe is None and mcap is not None and pat not in (None, 0):
        pe = round(mcap / pat, 4)
    # Forward PE soft: if growth positive, forward eps ≈ trailing * (1+g)
    forward_pe = None
    if pe is not None and growth is not None and growth > -50:
        if eps not in (None, 0) and price:
            fwd_eps = eps * (1.0 + growth / 100.0)
            if fwd_eps not in (None, 0):
                forward_pe = round(price / fwd_eps, 4)
        elif mcap is not None and pat not in (None, 0):
            fwd_pat = pat * (1.0 + growth / 100.0)
            if fwd_pat:
                forward_pe = round(mcap / fwd_pat, 4)

    pb = None
    if mcap is not None and equity not in (None, 0):
        # Skip absurd equity (mis-mapped share capital)
        assets = _f(fundamentals.get("total_assets"))
        if assets is None or float(equity) / float(assets) >= 0.005:
            pb = round(mcap / equity, 4)
    ev = None
    if mcap is not None:
        ev = round(mcap + float(net_debt or 0.0), 2)
    ev_ebitda = round(ev / ebitda, 4) if ev is not None and ebitda not in (None, 0) else None
    ev_sales = round(ev / rev, 4) if ev is not None and rev not in (None, 0) else None
    ps = round(mcap / rev, 4) if mcap is not None and rev not in (None, 0) else None
    pcf = round(mcap / ocf, 4) if mcap is not None and ocf not in (None, 0) else None
    peg = None
    if pe is not None and growth not in (None, 0) and growth > 0:
        peg = round(pe / growth, 4)

    return {
        "price": price,
        "market_cap": mcap,
        "enterprise_value": ev,
        "net_debt": net_debt,
        "pe": pe,
        "forward_pe": forward_pe,
        "pb": pb,
        "ev_ebitda": ev_ebitda,
        "ev_sales": ev_sales,
        "price_to_sales": ps,
        "price_to_cash_flow": pcf,
        "peg": peg,
        "ttm_eps": eps,
    }


def estimate_market_cap(price: float | None, fundamentals: dict[str, Any]) -> float | None:
    """Soft mcap from shares if known; else PAT/EPS; else paid-up capital / face value."""
    if price is None:
        return None
    shares = _f(fundamentals.get("shares_outstanding"))
    if shares:
        return round(price * shares, 2)
    esc = _f(fundamentals.get("equity_share_capital"))
    face = _f(fundamentals.get("face_value")) or 1.0
    if esc not in (None, 0) and face not in (None, 0):
        sh = esc / face
        if sh > 1e6:
            return round(price * sh, 2)
    eps = _f(fundamentals.get("ttm_eps"))
    pat = _f(fundamentals.get("ttm_pat"))
    if eps not in (None, 0) and pat is not None:
        # shares ≈ PAT / EPS
        sh = pat / eps
        if sh > 0:
            return round(price * sh, 2)
    return None
