"""Derived financial analytics + earnings intelligence (analytical facts only)."""

from __future__ import annotations

from typing import Any


def _f(v: Any) -> float | None:
    try:
        if v is None:
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _pct_change(curr: float | None, prev: float | None) -> float | None:
    if curr is None or prev is None or prev == 0:
        return None
    return round(100.0 * (curr - prev) / abs(prev), 4)


def _margin(numer: float | None, denom: float | None) -> float | None:
    if numer is None or denom is None or denom == 0:
        return None
    return round(100.0 * numer / denom, 4)


def statement_metrics(income: dict[str, Any] | None, balance: dict[str, Any] | None, cashflow: dict[str, Any] | None) -> dict[str, Any]:
    inc = income or {}
    bal = balance or {}
    cf = cashflow or {}
    rev = _f(inc.get("revenue_from_operations"))
    ebitda = _f(inc.get("ebitda"))
    ebit = _f(inc.get("ebit"))
    pat = _f(inc.get("pat_owners") if inc.get("pat_owners") is not None else inc.get("pat"))
    equity = _f(bal.get("total_equity"))
    assets = _f(bal.get("total_assets"))
    debt = _f(bal.get("total_debt"))
    fin = _f(inc.get("finance_costs"))
    ocf = _f(cf.get("operating_cash_flow"))
    fcf = _f(cf.get("free_cash_flow"))
    return {
        "ebitda_margin_pct": _margin(ebitda, rev),
        "pat_margin_pct": _margin(pat, rev),
        "ebit_margin_pct": _margin(ebit, rev),
        "roe_pct": _margin(pat, equity),
        "roce_pct": _margin(ebit, assets),  # soft proxy
        "asset_turnover": round(rev / assets, 4) if rev is not None and assets not in (None, 0) else None,
        "debt_to_equity": round(debt / equity, 4) if debt is not None and equity not in (None, 0) else None,
        "interest_coverage": round(ebit / fin, 4) if ebit is not None and fin not in (None, 0) else None,
        "cash_conversion": round(ocf / pat, 4) if ocf is not None and pat not in (None, 0) else None,
        "fcf": fcf,
        "ocf": ocf,
    }


def growth_vs_prior(current: dict[str, Any] | None, prior: dict[str, Any] | None) -> dict[str, Any]:
    cur_i = ((current or {}).get("statements") or {}).get("income_statement") or {}
    pri_i = ((prior or {}).get("statements") or {}).get("income_statement") or {}
    return {
        "revenue_growth_pct": _pct_change(
            _f(cur_i.get("revenue_from_operations")), _f(pri_i.get("revenue_from_operations"))
        ),
        "pat_growth_pct": _pct_change(
            _f(cur_i.get("pat_owners") if cur_i.get("pat_owners") is not None else cur_i.get("pat")),
            _f(pri_i.get("pat_owners") if pri_i.get("pat_owners") is not None else pri_i.get("pat")),
        ),
        "eps_growth_pct": _pct_change(_f(cur_i.get("eps_basic")), _f(pri_i.get("eps_basic"))),
        "ebitda_growth_pct": _pct_change(_f(cur_i.get("ebitda")), _f(pri_i.get("ebitda"))),
    }


def build_ttm(quarterly_enriched: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Sum last 4 quarter income OneD facts when available."""
    rows = []
    for q in quarterly_enriched:
        inc = ((q.get("statements") or {}).get("income_statement") or {})
        if inc.get("revenue_from_operations") is not None or inc.get("pat") is not None:
            rows.append(q)
        if len(rows) >= 4:
            break
    if len(rows) < 4:
        return {"available": False, "quarters_used": len(rows), "reason": "need_4_quarters"}

    def sum_field(field: str) -> float | None:
        vals = []
        for r in rows:
            v = _f((((r.get("statements") or {}).get("income_statement") or {}).get(field)))
            if v is not None:
                vals.append(v)
        if len(vals) < 4:
            return None
        return round(sum(vals), 2)

    income = {
        "revenue_from_operations": sum_field("revenue_from_operations"),
        "other_income": sum_field("other_income"),
        "total_income": sum_field("total_income"),
        "ebitda": sum_field("ebitda"),
        "ebit": sum_field("ebit"),
        "pbt": sum_field("pbt"),
        "pat": sum_field("pat"),
        "pat_owners": sum_field("pat_owners"),
        "finance_costs": sum_field("finance_costs"),
        "depreciation": sum_field("depreciation"),
        "tax_expense": sum_field("tax_expense"),
    }
    income = {k: v for k, v in income.items()}
    # EPS: sum if available (approximate)
    eps_vals = [
        _f((((r.get("statements") or {}).get("income_statement") or {}).get("eps_basic")))
        for r in rows
    ]
    eps_vals = [v for v in eps_vals if v is not None]
    income["eps_basic"] = round(sum(eps_vals), 4) if len(eps_vals) == 4 else None

    return {
        "available": income.get("revenue_from_operations") is not None or income.get("pat") is not None,
        "quarters_used": 4,
        "period_ends": [r.get("period_end") for r in rows],
        "income_statement": income,
        "metrics": statement_metrics(income, None, None),
    }


def earnings_intelligence(
    *,
    latest_q: dict[str, Any] | None,
    prior_q: dict[str, Any] | None,
    yoy_q: dict[str, Any] | None,
    latest_a: dict[str, Any] | None,
    prior_a: dict[str, Any] | None,
    ttm: dict[str, Any] | None,
) -> dict[str, Any]:
    """Analytical earnings observations — no BUY/SELL."""
    observations: list[str] = []
    q_growth = growth_vs_prior(latest_q, prior_q)
    yoy = growth_vs_prior(latest_q, yoy_q)
    a_growth = growth_vs_prior(latest_a, prior_a)

    lq_inc = ((latest_q or {}).get("statements") or {}).get("income_statement") or {}
    pq_inc = ((prior_q or {}).get("statements") or {}).get("income_statement") or {}
    lq_m = statement_metrics(
        lq_inc,
        ((latest_q or {}).get("statements") or {}).get("balance_sheet"),
        ((latest_q or {}).get("statements") or {}).get("cash_flow"),
    )
    pq_m = statement_metrics(pq_inc, None, None)

    rev_g = yoy.get("revenue_growth_pct")
    pat_g = yoy.get("pat_growth_pct")
    if rev_g is not None:
        observations.append("Revenue growth YoY positive" if rev_g > 0 else "Revenue contraction YoY")
    if pat_g is not None:
        observations.append("PAT growth YoY positive" if pat_g > 0 else "PAT contraction YoY")

    em = lq_m.get("ebitda_margin_pct")
    pem = pq_m.get("ebitda_margin_pct")
    if em is not None and pem is not None:
        if em - pem > 0.5:
            observations.append("Margin expansion")
        elif pem - em > 0.5:
            observations.append("Margin contraction")

    la_cf = ((latest_a or {}).get("statements") or {}).get("cash_flow") or {}
    if la_cf.get("operating_cash_flow") is not None and la_cf.get("free_cash_flow") is not None:
        if float(la_cf["free_cash_flow"]) > 0:
            observations.append("Positive free cash flow (annual)")
        else:
            observations.append("Negative free cash flow (annual)")
        pat_a = _f((((latest_a or {}).get("statements") or {}).get("income_statement") or {}).get("pat"))
        ocf = _f(la_cf.get("operating_cash_flow"))
        if pat_a not in (None, 0) and ocf is not None:
            if ocf / abs(pat_a) >= 0.8:
                observations.append("Cash-flow quality supportive")
            elif ocf / abs(pat_a) < 0.5:
                observations.append("Cash-flow quality weak vs PAT")

    la_bal = ((latest_a or {}).get("statements") or {}).get("balance_sheet") or {}
    am = statement_metrics(
        ((latest_a or {}).get("statements") or {}).get("income_statement"),
        la_bal,
        la_cf,
    )
    if am.get("debt_to_equity") is not None:
        if am["debt_to_equity"] < 0.5:
            observations.append("Conservative leverage")
        elif am["debt_to_equity"] > 1.5:
            observations.append("Elevated leverage")

    segs = ((latest_q or {}).get("statements") or {}).get("segments") or []
    if segs:
        observations.append(f"Segment disclosure available ({len(segs)} segments)")

    if ttm and ttm.get("available"):
        observations.append("TTM metrics available")

    # Significant BS move YoY (assets)
    if latest_a and prior_a:
        a0 = _f((((latest_a.get("statements") or {}).get("balance_sheet") or {}).get("total_assets")))
        a1 = _f((((prior_a.get("statements") or {}).get("balance_sheet") or {}).get("total_assets")))
        ch = _pct_change(a0, a1)
        if ch is not None and abs(ch) >= 15:
            observations.append("Significant balance-sheet change YoY")

    seen: set[str] = set()
    uniq = []
    for o in observations:
        if o not in seen:
            seen.add(o)
            uniq.append(o)

    reasoning_parts = []
    if lq_inc.get("revenue_from_operations") is not None:
        reasoning_parts.append(f"Latest quarter revenue={lq_inc.get('revenue_from_operations')}")
    if lq_inc.get("pat") is not None or lq_inc.get("pat_owners") is not None:
        reasoning_parts.append(f"PAT={lq_inc.get('pat_owners') or lq_inc.get('pat')}")
    if em is not None:
        reasoning_parts.append(f"EBITDA margin={em}%")
    reasoning = "; ".join(reasoning_parts)
    if uniq:
        reasoning += ". Observations: " + "; ".join(uniq[:8]) + "."

    # Soft earnings quality score (evidence richness, not recommendation)
    score = 40.0
    if (latest_q or {}).get("has_income"):
        score += 20
    if (latest_a or {}).get("has_balance"):
        score += 15
    if (latest_a or {}).get("has_cash_flow"):
        score += 15
    if ttm and ttm.get("available"):
        score += 5
    if segs:
        score += 5
    score = min(100.0, score)

    return {
        "forecast_confidence": round(score, 1),  # programme score_field name
        "earnings_quality": round(score, 1),
        "observations": uniq,
        "qoq_growth": q_growth,
        "yoy_growth": yoy,
        "annual_growth": a_growth,
        "latest_quarter_metrics": lq_m,
        "latest_annual_metrics": am,
        "reasoning": reasoning or "Financial statements ingested; analytics limited by available fields.",
        "not_a_recommendation": True,
        # Placeholders for consensus beat/miss when estimate feed lands
        "revenue_beat_miss": None,
        "pat_beat_miss": None,
        "guidance_changes": None,
    }
