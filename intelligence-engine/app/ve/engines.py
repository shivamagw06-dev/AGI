"""Valuation model plugins — DCF, relative, SOTP, DDM, RI, asset, replacement."""

from __future__ import annotations

from typing import Any, Callable

from app.ve.config import DEFAULT_ASSUMPTIONS, HORIZON_YEARS, PEER_MULTIPLES
from app.ve.models import Assumption, ModelResult, PeerRow, SensitivityPoint


def _f(assumptions: dict[str, float], key: str, default: float | None = None) -> float:
    if key in assumptions:
        return float(assumptions[key])
    if default is not None:
        return float(default)
    return float(DEFAULT_ASSUMPTIONS.get(key, 0.0))


def _npv(cashflows: list[float], rate: float) -> float:
    total = 0.0
    for i, cf in enumerate(cashflows, start=1):
        total += cf / ((1.0 + rate) ** i)
    return total


def dcf_fcff(assumptions: dict[str, float], *, base_revenue_cr: float = 150000.0) -> ModelResult:
    g = _f(assumptions, "revenue_growth")
    margin = _f(assumptions, "ebit_margin")
    tax = _f(assumptions, "tax_rate")
    capex = _f(assumptions, "capex_pct_sales")
    nwc = _f(assumptions, "nwc_pct_sales")
    wacc = max(0.01, _f(assumptions, "wacc"))
    tg = min(_f(assumptions, "terminal_growth"), wacc - 0.01)
    shares = max(0.01, _f(assumptions, "shares_outstanding_cr"))
    net_debt = _f(assumptions, "net_debt_cr")

    revenue = base_revenue_cr
    fcf_list: list[float] = []
    for _ in range(HORIZON_YEARS):
        revenue *= 1.0 + g
        ebit = revenue * margin
        nopat = ebit * (1.0 - tax)
        reinvestment = revenue * (capex + nwc) * g / max(g, 0.01) * 0.35  # scaled reinvestment
        fcf = max(0.0, nopat - reinvestment)
        fcf_list.append(fcf)
    terminal = fcf_list[-1] * (1.0 + tg) / max(wacc - tg, 0.01)
    ev = _npv(fcf_list, wacc) + terminal / ((1.0 + wacc) ** HORIZON_YEARS)
    equity = ev - net_debt
    per_share = equity / shares
    return ModelResult(
        model="dcf_fcff",
        intrinsic_value=round(per_share, 2),
        fair_value=round(per_share, 2),
        equity_value=round(equity, 2),
        enterprise_value=round(ev, 2),
        confidence=0.72,
        details={
            "base_revenue_cr": base_revenue_cr,
            "horizon_years": HORIZON_YEARS,
            "fcf_path_cr": [round(x, 2) for x in fcf_list],
            "terminal_value_cr": round(terminal, 2),
            "wacc": wacc,
            "terminal_growth": tg,
        },
    )


def dcf_fcfe(assumptions: dict[str, float], *, base_revenue_cr: float = 150000.0) -> ModelResult:
    # FCFE ≈ FCFF adjusted for net borrowing / equity discount at cost of equity
    fcff = dcf_fcff(assumptions, base_revenue_cr=base_revenue_cr)
    coe = max(0.01, _f(assumptions, "cost_of_equity"))
    wacc = max(0.01, _f(assumptions, "wacc"))
    scale = wacc / coe
    per_share = float(fcff.intrinsic_value) * scale * 0.95
    return ModelResult(
        model="dcf_fcfe",
        intrinsic_value=round(per_share, 2),
        fair_value=round(per_share, 2),
        equity_value=fcff.equity_value,
        enterprise_value=fcff.enterprise_value,
        confidence=0.68,
        details={"derived_from": "dcf_fcff", "cost_of_equity": coe, "scale": round(scale, 4)},
    )


def _eps(assumptions: dict[str, float], base_revenue_cr: float) -> float:
    shares = max(0.01, _f(assumptions, "shares_outstanding_cr"))
    margin = _f(assumptions, "ebit_margin")
    tax = _f(assumptions, "tax_rate")
    net_income = base_revenue_cr * margin * (1.0 - tax)
    return net_income / shares


def relative_pe(assumptions: dict[str, float], *, base_revenue_cr: float = 150000.0, peer_pe: float = 22.0) -> ModelResult:
    eps = _eps(assumptions, base_revenue_cr)
    g = _f(assumptions, "revenue_growth")
    # Slight quality premium/discount vs peer
    target_pe = peer_pe * (1.0 + (g - 0.10))
    value = eps * target_pe
    return ModelResult(
        model="relative_pe",
        intrinsic_value=round(value, 2),
        fair_value=round(value, 2),
        multiple=round(target_pe, 2),
        confidence=0.65,
        details={"eps": round(eps, 2), "peer_pe": peer_pe, "target_pe": round(target_pe, 2)},
    )


def relative_ev_ebitda(assumptions: dict[str, float], *, base_revenue_cr: float = 150000.0, peer_mult: float = 14.0) -> ModelResult:
    margin = _f(assumptions, "ebit_margin")
    shares = max(0.01, _f(assumptions, "shares_outstanding_cr"))
    net_debt = _f(assumptions, "net_debt_cr")
    ebitda = base_revenue_cr * margin * 1.15
    ev = ebitda * peer_mult
    equity = ev - net_debt
    per_share = equity / shares
    return ModelResult(
        model="relative_ev_ebitda",
        intrinsic_value=round(per_share, 2),
        fair_value=round(per_share, 2),
        enterprise_value=round(ev, 2),
        equity_value=round(equity, 2),
        multiple=peer_mult,
        confidence=0.64,
        details={"ebitda_cr": round(ebitda, 2), "peer_ev_ebitda": peer_mult},
    )


def relative_ev_sales(assumptions: dict[str, float], *, base_revenue_cr: float = 150000.0, peer_mult: float = 3.5) -> ModelResult:
    shares = max(0.01, _f(assumptions, "shares_outstanding_cr"))
    net_debt = _f(assumptions, "net_debt_cr")
    ev = base_revenue_cr * peer_mult
    per_share = (ev - net_debt) / shares
    return ModelResult(
        model="relative_ev_sales",
        intrinsic_value=round(per_share, 2),
        fair_value=round(per_share, 2),
        enterprise_value=round(ev, 2),
        multiple=peer_mult,
        confidence=0.55,
        details={"peer_ev_sales": peer_mult},
    )


def relative_pb(assumptions: dict[str, float], *, peer_pb: float = 5.0) -> ModelResult:
    book = _f(assumptions, "book_equity_cr")
    shares = max(0.01, _f(assumptions, "shares_outstanding_cr"))
    roe = _f(assumptions, "roe")
    target_pb = peer_pb * (1.0 + (roe - 0.15))
    per_share = (book * target_pb) / shares
    return ModelResult(
        model="relative_pb",
        intrinsic_value=round(per_share, 2),
        fair_value=round(per_share, 2),
        multiple=round(target_pb, 2),
        confidence=0.58,
        details={"book_equity_cr": book, "peer_pb": peer_pb},
    )


def relative_peg(assumptions: dict[str, float], *, base_revenue_cr: float = 150000.0, peer_pe: float = 22.0) -> ModelResult:
    eps = _eps(assumptions, base_revenue_cr)
    g_pct = max(1.0, _f(assumptions, "revenue_growth") * 100)
    peg = peer_pe / g_pct
    fair_pe = peg * g_pct  # tautological baseline then adjust
    fair_pe = min(35.0, max(8.0, g_pct * 1.1))
    value = eps * fair_pe
    return ModelResult(
        model="relative_peg",
        intrinsic_value=round(value, 2),
        fair_value=round(value, 2),
        multiple=round(fair_pe, 2),
        confidence=0.56,
        details={"eps": round(eps, 2), "growth_pct": round(g_pct, 2), "implied_peg": round(peg, 3)},
    )


def relative_pcf(assumptions: dict[str, float], *, base_revenue_cr: float = 150000.0, peer_pcf: float = 18.0) -> ModelResult:
    shares = max(0.01, _f(assumptions, "shares_outstanding_cr"))
    margin = _f(assumptions, "ebit_margin")
    fcf_ps = (base_revenue_cr * margin * 0.7) / shares
    value = fcf_ps * peer_pcf
    return ModelResult(
        model="relative_pcf",
        intrinsic_value=round(value, 2),
        fair_value=round(value, 2),
        multiple=peer_pcf,
        confidence=0.57,
        details={"fcf_per_share": round(fcf_ps, 2), "peer_pcf": peer_pcf},
    )


def sotp(assumptions: dict[str, float], *, segments: list[dict[str, Any]] | None = None) -> ModelResult:
    shares = max(0.01, _f(assumptions, "shares_outstanding_cr"))
    net_debt = _f(assumptions, "net_debt_cr")
    segs = segments or [
        {"name": "core_ops", "ebitda_cr": 30000.0, "multiple": 14.0},
        {"name": "investments", "nav_cr": 15000.0},
        {"name": "other", "nav_cr": 5000.0},
    ]
    total = 0.0
    detail = []
    for s in segs:
        if "ebitda_cr" in s:
            val = float(s["ebitda_cr"]) * float(s.get("multiple") or 12.0)
        else:
            val = float(s.get("nav_cr") or 0.0)
        total += val
        detail.append({"name": s.get("name"), "value_cr": round(val, 2)})
    equity = total - net_debt
    per_share = equity / shares
    return ModelResult(
        model="sotp",
        intrinsic_value=round(per_share, 2),
        fair_value=round(per_share, 2),
        enterprise_value=round(total, 2),
        equity_value=round(equity, 2),
        confidence=0.6,
        details={"segments": detail},
    )


def ddm(assumptions: dict[str, float], *, base_revenue_cr: float = 150000.0) -> ModelResult:
    coe = max(0.01, _f(assumptions, "cost_of_equity"))
    g = min(_f(assumptions, "revenue_growth") * 0.6, coe - 0.01)
    payout = _f(assumptions, "dividend_payout")
    eps = _eps(assumptions, base_revenue_cr)
    d1 = eps * payout * (1.0 + g)
    value = d1 / max(coe - g, 0.01)
    return ModelResult(
        model="ddm",
        intrinsic_value=round(value, 2),
        fair_value=round(value, 2),
        confidence=0.52,
        details={"d1": round(d1, 2), "cost_of_equity": coe, "growth": g, "payout": payout},
    )


def residual_income(assumptions: dict[str, float]) -> ModelResult:
    book = _f(assumptions, "book_equity_cr")
    shares = max(0.01, _f(assumptions, "shares_outstanding_cr"))
    roe = _f(assumptions, "roe")
    coe = max(0.01, _f(assumptions, "cost_of_equity"))
    bps = book / shares
    # Simplified RI: BV + sum RI / (1+r)^t with persistent RI
    ri = (roe - coe) * bps
    total_ri = 0.0
    for t in range(1, HORIZON_YEARS + 1):
        total_ri += ri / ((1.0 + coe) ** t)
        ri *= 0.9
    value = bps + total_ri
    return ModelResult(
        model="residual_income",
        intrinsic_value=round(value, 2),
        fair_value=round(value, 2),
        confidence=0.6,
        details={"book_per_share": round(bps, 2), "roe": roe, "cost_of_equity": coe},
    )


def asset_based(assumptions: dict[str, float]) -> ModelResult:
    book = _f(assumptions, "book_equity_cr")
    tangible = _f(assumptions, "tangible_assets_cr")
    shares = max(0.01, _f(assumptions, "shares_outstanding_cr"))
    net_debt = _f(assumptions, "net_debt_cr")
    nav = max(book, tangible - net_debt)
    per_share = nav / shares
    return ModelResult(
        model="asset_based",
        intrinsic_value=round(per_share, 2),
        fair_value=round(per_share, 2),
        confidence=0.5,
        details={"nav_cr": round(nav, 2)},
    )


def replacement_cost(assumptions: dict[str, float]) -> ModelResult:
    tangible = _f(assumptions, "tangible_assets_cr")
    premium = _f(assumptions, "replacement_premium")
    shares = max(0.01, _f(assumptions, "shares_outstanding_cr"))
    net_debt = _f(assumptions, "net_debt_cr")
    replacement = tangible * premium - net_debt
    per_share = replacement / shares
    return ModelResult(
        model="replacement_cost",
        intrinsic_value=round(per_share, 2),
        fair_value=round(per_share, 2),
        confidence=0.48,
        details={"replacement_premium": premium, "replacement_nav_cr": round(replacement, 2)},
    )


MODEL_PLUGINS: dict[str, Callable[..., ModelResult]] = {
    "dcf_fcff": dcf_fcff,
    "dcf_fcfe": dcf_fcfe,
    "relative_pe": relative_pe,
    "relative_ev_ebitda": relative_ev_ebitda,
    "relative_ev_sales": relative_ev_sales,
    "relative_pb": relative_pb,
    "relative_peg": relative_peg,
    "relative_pcf": relative_pcf,
    "sotp": sotp,
    "ddm": ddm,
    "residual_income": residual_income,
    "asset_based": asset_based,
    "replacement_cost": replacement_cost,
}


def run_model(name: str, assumptions: dict[str, float], **kwargs: Any) -> ModelResult:
    fn = MODEL_PLUGINS.get(name)
    if not fn:
        raise KeyError(f"Unknown valuation model: {name}")
    return fn(assumptions, **kwargs)


def build_peer_rows(symbol: str, peer_symbols: list[str]) -> list[PeerRow]:
    rows: list[PeerRow] = []
    for sym in [symbol] + peer_symbols:
        m = PEER_MULTIPLES.get(sym.upper()) or PEER_MULTIPLES["DEFAULT"]
        rows.append(
            PeerRow(
                symbol=sym.upper(),
                pe=m["pe"],
                ev_ebitda=m["ev_ebitda"],
                ev_sales=m["ev_sales"],
                pb=m["pb"],
                roce=m["roce"],
                roe=m["roe"],
                growth=m["growth"],
                margin=m["margin"],
                leverage=m["leverage"],
                fcf_yield=m["fcf_yield"],
            )
        )
    return rows


def sensitivity_grid(
    base_assumptions: dict[str, float],
    *,
    base_revenue_cr: float,
    parameters: tuple[str, ...] = ("wacc", "revenue_growth", "terminal_growth", "ebit_margin"),
    deltas: tuple[float, ...] = (-0.02, -0.01, 0.01, 0.02),
) -> list[SensitivityPoint]:
    base = dcf_fcff(base_assumptions, base_revenue_cr=base_revenue_cr)
    base_iv = base.intrinsic_value or 1.0
    points: list[SensitivityPoint] = []
    for param in parameters:
        for d in deltas:
            adj = dict(base_assumptions)
            adj[param] = float(adj.get(param, DEFAULT_ASSUMPTIONS.get(param, 0.0))) + d
            if param == "wacc":
                adj[param] = max(0.01, adj[param])
            iv = dcf_fcff(adj, base_revenue_cr=base_revenue_cr).intrinsic_value
            points.append(
                SensitivityPoint(
                    parameter=param,
                    delta_pct=round(d * 100, 2),
                    intrinsic_value=round(iv, 2),
                    change_pct=round(((iv - base_iv) / base_iv) * 100, 2),
                )
            )
    return points


def assumptions_to_map(items: list[Assumption]) -> dict[str, float]:
    return {a.name: float(a.value) for a in items}
