"""Growth CAGRs + profitability from earnings packs (3Y / 5Y / 10Y)."""

from __future__ import annotations

from typing import Any

from valuation_intelligence.schema import GrowthMetrics


def _f(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _cagr(first: float | None, last: float | None, years: float) -> float | None:
    if first is None or last is None or years <= 0:
        return None
    if first <= 0 or last <= 0:
        return None
    try:
        return round(((last / first) ** (1.0 / years) - 1.0) * 100.0, 2)
    except Exception:
        return None


def _annual_rows(earnings: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalise annual history from earnings_intelligence pack or slim dict."""
    if not isinstance(earnings, dict):
        return []
    # Slim injected shape: {"annual": [{revenue, ebitda, pat, eps}, ...]} newest-first or oldest-first
    if isinstance(earnings.get("annual"), list):
        return [r for r in earnings["annual"] if isinstance(r, dict)]
    # Full pack: annual_history with nested income_statement
    rows: list[dict[str, Any]] = []
    for r in earnings.get("annual_history") or []:
        if not isinstance(r, dict):
            continue
        inc = r.get("income_statement") if isinstance(r.get("income_statement"), dict) else r
        rows.append(
            {
                "period_end": r.get("period_end"),
                "revenue": _f(inc.get("revenue_from_operations") or inc.get("revenue")),
                "ebitda": _f(inc.get("ebitda")),
                "ebit": _f(inc.get("ebit")),
                "pat": _f(inc.get("pat_owners") or inc.get("pat") or inc.get("profit_loss")),
                "eps": _f(inc.get("eps_basic") or inc.get("eps_diluted") or inc.get("eps")),
            }
        )
    return rows


def growth_from_earnings(earnings: dict[str, Any] | None) -> GrowthMetrics:
    rows = _annual_rows(earnings or {})
    if not rows:
        return GrowthMetrics()

    # Ensure oldest → newest by period_end when available
    def _key(r: dict[str, Any]) -> str:
        return str(r.get("period_end") or "")

    if any(r.get("period_end") for r in rows):
        ordered = sorted(rows, key=_key)
    else:
        # Assume newest-first lists (common) → reverse
        ordered = list(reversed(rows))

    def series(key: str) -> list[float | None]:
        return [_f(r.get(key)) for r in ordered]

    rev = series("revenue")
    ebitda = series("ebitda")
    pat = series("pat")
    eps = series("eps")

    def window_cagr(vals: list[float | None], years: int) -> float | None:
        clean_idx = [(i, v) for i, v in enumerate(vals) if v is not None]
        if len(clean_idx) < 2:
            return None
        if len(vals) >= years + 1:
            window = vals[-(years + 1) :]
            first = next((v for v in window if v is not None), None)
            last = next((v for v in reversed(window) if v is not None), None)
            return _cagr(first, last, float(years))
        first = clean_idx[0][1]
        last = clean_idx[-1][1]
        span = max(1, clean_idx[-1][0] - clean_idx[0][0])
        return _cagr(first, last, float(span))

    return GrowthMetrics(
        revenue_cagr_3y=window_cagr(rev, 3),
        revenue_cagr_5y=window_cagr(rev, 5),
        revenue_cagr_10y=window_cagr(rev, 10),
        ebitda_cagr_3y=window_cagr(ebitda, 3),
        ebitda_cagr_5y=window_cagr(ebitda, 5),
        ebitda_cagr_10y=window_cagr(ebitda, 10),
        eps_cagr_3y=window_cagr(eps, 3),
        eps_cagr_5y=window_cagr(eps, 5),
        eps_cagr_10y=window_cagr(eps, 10),
        pat_cagr_3y=window_cagr(pat, 3),
        pat_cagr_5y=window_cagr(pat, 5),
        pat_cagr_10y=window_cagr(pat, 10),
    )


def profitability_from_earnings(earnings: dict[str, Any] | None) -> dict[str, float | None]:
    """Prefer metrics already computed on the earnings pack; fall back to statements."""
    if not isinstance(earnings, dict):
        return {}

    la_m = ((earnings.get("metrics") or {}).get("latest_annual") or {}) if isinstance(earnings.get("metrics"), dict) else {}
    lq_m = ((earnings.get("metrics") or {}).get("latest_quarter") or {}) if isinstance(earnings.get("metrics"), dict) else {}

    out = {
        "roe": _f(la_m.get("roe_pct") or earnings.get("roe_pct") or earnings.get("roe")),
        "roce": _f(la_m.get("roce_pct") or earnings.get("roce_pct") or earnings.get("roce")),
        "roa": _f(la_m.get("roa_pct") or earnings.get("roa")),
        "ebitda_margin": _f(
            lq_m.get("ebitda_margin_pct") or la_m.get("ebitda_margin_pct") or earnings.get("ebitda_margin_pct")
        ),
        "ebit_margin": _f(lq_m.get("ebit_margin_pct") or la_m.get("ebit_margin_pct")),
        "pat_margin": _f(lq_m.get("pat_margin_pct") or la_m.get("pat_margin_pct")),
    }
    if any(v is not None for v in out.values()):
        return out

    # Slim / reconstructed
    ttm = earnings.get("ttm") if isinstance(earnings.get("ttm"), dict) else {}
    ttm_inc = ttm.get("income_statement") if isinstance(ttm.get("income_statement"), dict) else ttm
    rows = _annual_rows(earnings)
    latest = rows[-1] if rows else {}
    # Prefer newest if period-sorted ascending
    if rows and any(r.get("period_end") for r in rows):
        latest = sorted(rows, key=lambda r: str(r.get("period_end") or ""))[-1]

    rev = _f(ttm_inc.get("revenue_from_operations") or ttm_inc.get("revenue") or latest.get("revenue"))
    ebitda = _f(ttm_inc.get("ebitda") or latest.get("ebitda"))
    ebit = _f(ttm_inc.get("ebit") or latest.get("ebit"))
    pat = _f(ttm_inc.get("pat_owners") or ttm_inc.get("pat") or latest.get("pat"))

    equity = None
    assets = None
    la = earnings.get("latest_annual") if isinstance(earnings.get("latest_annual"), dict) else {}
    bal = la.get("balance_sheet") if isinstance(la.get("balance_sheet"), dict) else {}
    equity = _f(bal.get("total_equity") or bal.get("equity"))
    assets = _f(bal.get("total_assets") or bal.get("assets"))

    def margin(num: float | None, den: float | None) -> float | None:
        if num is None or den in (None, 0):
            return None
        return round(num / den * 100.0, 2)

    def ratio(num: float | None, den: float | None) -> float | None:
        if num is None or den in (None, 0):
            return None
        return round(num / den * 100.0, 2)

    return {
        "roe": ratio(pat, equity),
        "roa": ratio(pat, assets),
        "roce": ratio(ebit if ebit is not None else ebitda, equity),
        "ebitda_margin": margin(ebitda, rev),
        "ebit_margin": margin(ebit, rev),
        "pat_margin": margin(pat, rev),
    }
