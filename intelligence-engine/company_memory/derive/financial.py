"""Financial Intelligence — QoQ/YoY/TTM/CAGR objects (recompute only when filings change)."""

from __future__ import annotations

from typing import Any


def _f(v: Any) -> float | None:
    try:
        if v is None or v == "":
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _cagr(first: float | None, last: float | None, years: float) -> float | None:
    if first is None or last is None or years <= 0 or first <= 0 or last <= 0:
        return None
    try:
        return round(((last / first) ** (1.0 / years) - 1.0) * 100.0, 2)
    except Exception:
        return None


def _pct_change(a: float | None, b: float | None) -> float | None:
    if a is None or b in (None, 0):
        return None
    return round((a / b - 1.0) * 100.0, 2)


def derive_financial_history(
    entity: str,
    *,
    earnings_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pack = earnings_pack if isinstance(earnings_pack, dict) else {}
    annual = list(pack.get("annual_history") or [])
    quarters = list(pack.get("quarter_history") or [])
    ttm = pack.get("ttm") if isinstance(pack.get("ttm"), dict) else {}
    ttm_inc = ttm.get("income_statement") if isinstance(ttm.get("income_statement"), dict) else {}
    metrics = pack.get("metrics") if isinstance(pack.get("metrics"), dict) else {}
    yoy = metrics.get("yoy_growth") if isinstance(metrics.get("yoy_growth"), dict) else {}
    qoq = metrics.get("qoq_growth") if isinstance(metrics.get("qoq_growth"), dict) else {}
    la_m = metrics.get("latest_annual") if isinstance(metrics.get("latest_annual"), dict) else {}
    lq_m = metrics.get("latest_quarter") if isinstance(metrics.get("latest_quarter"), dict) else {}

    # Prefer live earnings pack; soft-fill from HD annual if empty
    if not annual:
        try:
            from knowledge_factory.historical_depth import store as hd_store

            series = hd_store.get_series("financials_annual", entity) or {}
            for r in series.get("records") or []:
                p = r.get("payload") or {}
                annual.append(
                    {
                        "period_end": r.get("period_end"),
                        "income_statement": {
                            "revenue_from_operations": p.get("revenue"),
                            "ebitda": p.get("ebitda"),
                            "pat": p.get("net_income"),
                            "eps_basic": p.get("eps"),
                        },
                        "balance_sheet": {
                            "total_equity": p.get("equity"),
                            "total_debt": p.get("total_debt"),
                            "cash": p.get("cash"),
                        },
                        "cash_flow": {"operating_cash_flow": p.get("ocf"), "free_cash_flow": p.get("fcf")},
                    }
                )
        except Exception:
            pass

    def _inc(row: dict[str, Any]) -> dict[str, Any]:
        return row.get("income_statement") if isinstance(row.get("income_statement"), dict) else {}

    rev_series = [_f(_inc(r).get("revenue_from_operations")) for r in reversed(annual)]
    ebitda_series = [_f(_inc(r).get("ebitda")) for r in reversed(annual)]
    pat_series = [_f(_inc(r).get("pat_owners") or _inc(r).get("pat")) for r in reversed(annual)]
    eps_series = [_f(_inc(r).get("eps_basic") or _inc(r).get("eps_diluted")) for r in reversed(annual)]

    def window(vals: list[float | None], years: int) -> float | None:
        clean = [(i, v) for i, v in enumerate(vals) if v is not None]
        if len(clean) < 2:
            return None
        if len(vals) >= years + 1:
            window_vals = vals[-(years + 1) :]
            first = next((v for v in window_vals if v is not None), None)
            last = next((v for v in reversed(window_vals) if v is not None), None)
            return _cagr(first, last, float(years))
        return _cagr(clean[0][1], clean[-1][1], float(max(1, clean[-1][0] - clean[0][0])))

    la = annual[0] if annual else {}
    la_bal = la.get("balance_sheet") if isinstance(la.get("balance_sheet"), dict) else {}
    la_cf = la.get("cash_flow") if isinstance(la.get("cash_flow"), dict) else {}
    ocf = _f(la_cf.get("operating_cash_flow"))
    pat = _f(_inc(la).get("pat_owners") or _inc(la).get("pat"))
    cash_quality = None
    if ocf is not None and pat not in (None, 0):
        cash_quality = round(ocf / pat, 3)

    revenue = {
        "qoq": _f(qoq.get("revenue_growth_pct")),
        "yoy": _f(yoy.get("revenue_growth_pct")),
        "ttm": _f(ttm_inc.get("revenue_from_operations")),
        "cagr_3y": window(rev_series, 3),
        "cagr_5y": window(rev_series, 5),
        "cagr_10y": window(rev_series, 10),
    }
    ebitda = {
        "ttm": _f(ttm_inc.get("ebitda")),
        "margin": _f(lq_m.get("ebitda_margin_pct") or la_m.get("ebitda_margin_pct")),
        "cagr_3y": window(ebitda_series, 3),
        "cagr_5y": window(ebitda_series, 5),
        "trend": "improving"
        if len([v for v in ebitda_series if v is not None]) >= 2
        and ebitda_series[-1] is not None
        and ebitda_series[-2] is not None
        and ebitda_series[-1] > ebitda_series[-2]
        else "stable_or_soft",
    }
    out = {
        "available": bool(annual or quarters or ttm_inc),
        "entity": entity,
        "source": pack.get("source") or ("earnings_intelligence" if pack else "historical_depth"),
        "coverage_pct": pack.get("coverage_pct"),
        "revenue": revenue,
        "ebitda": ebitda,
        "pat": {
            "ttm": _f(ttm_inc.get("pat_owners") or ttm_inc.get("pat")),
            "yoy": _f(yoy.get("pat_growth_pct")),
            "cagr_3y": window(pat_series, 3),
            "cagr_5y": window(pat_series, 5),
            "margin": _f(lq_m.get("pat_margin_pct") or la_m.get("pat_margin_pct")),
        },
        "eps": {
            "ttm": _f(ttm_inc.get("eps_basic")),
            "yoy": _f(yoy.get("eps_growth_pct")),
            "cagr_3y": window(eps_series, 3),
            "cagr_5y": window(eps_series, 5),
            "trend": "up" if _pct_change(eps_series[-1] if eps_series else None, eps_series[-2] if len(eps_series) > 1 else None) and (_pct_change(eps_series[-1], eps_series[-2]) or 0) > 0 else "flat_or_down",
        },
        "cash_flow": {
            "operating": ocf,
            "free": _f(la_cf.get("free_cash_flow")),
            "quality_ocf_to_pat": cash_quality,
        },
        "debt": {
            "total_debt": _f(la_bal.get("total_debt")),
            "cash": _f(la_bal.get("cash")),
            "debt_to_equity": _f(la_m.get("debt_to_equity")),
        },
        "returns": {
            "roe": _f(la_m.get("roe_pct")),
            "roce": _f(la_m.get("roce_pct")),
            "roa": _f(la_m.get("roa_pct")),
        },
        "periods": {
            "annual_n": len(annual),
            "quarterly_n": len(quarters),
            "ttm_available": bool(ttm.get("available") or ttm_inc),
        },
        "lineage": [
            {"source": "earnings_intelligence", "ref": "annual_history", "n": len(annual)},
            {"source": "earnings_intelligence", "ref": "ttm", "available": bool(ttm_inc)},
        ],
    }
    return out
