"""Deterministic relationship detectors (FIRE-02)."""

from __future__ import annotations

from typing import Any

from financial_intelligence.drivers.core import (
    confidence_for_points,
    direction,
    evidence_points,
    latest_pair,
    make_relationship,
    pct_change,
    prior_pair,
    series_history_n,
    severity_for,
)
from financial_intelligence.trends import normalize_series


def _growth(series: list[dict[str, Any]]) -> tuple[float | None, dict | None, dict | None]:
    rows = normalize_series(series)
    if len(rows) < 2:
        return None, None, None
    prior, curr = rows[-2], rows[-1]
    return pct_change(float(curr["value"]), float(prior["value"])), curr, prior


def analyse_income_chain(series_map: dict[str, list], *, coverage_pct: float | None) -> list[dict]:
    out: list[dict] = []
    chain = ["revenue", "gross_profit", "ebitda", "ebit", "net_income"]
    for a, b in zip(chain, chain[1:]):
        pair = latest_pair(series_map.get(a) or [], series_map.get(b) or [])
        prior = prior_pair(series_map.get(a) or [], series_map.get(b) or [])
        if not pair or not prior:
            continue
        a0, b0 = prior
        a1, b1 = pair
        ga = pct_change(float(a1["value"]), float(a0["value"]))
        gb = pct_change(float(b1["value"]), float(b0["value"]))
        if ga is None or gb is None:
            continue
        ev = evidence_points(a0, a1, b0, b1, metrics=[a, a, b, b])
        hist = series_history_n(series_map, a, b)
        conf = confidence_for_points(ev, history_n=hist, coverage_pct=coverage_pct)
        if gb > ga + 1.0:
            code = f"{a}_to_{b}_margin_improved"
            obs = f"{b.replace('_', ' ').title()} grew faster ({gb:.1f}%) than {a.replace('_', ' ')} ({ga:.1f}%), indicating margin improvement in the chain."
            sev = severity_for(code, adverse=False)
        elif gb < ga - 1.0:
            code = f"{a}_to_{b}_margin_deteriorated"
            obs = f"{b.replace('_', ' ').title()} grew slower ({gb:.1f}%) than {a.replace('_', ' ')} ({ga:.1f}%), indicating margin deterioration in the chain."
            sev = severity_for(code, adverse=True)
        else:
            continue
        rel = make_relationship(
            category="Margin Drivers",
            relationship=f"{a} vs {b}",
            observation=obs,
            narrative=obs,
            evidence=ev,
            confidence=conf,
            severity=sev,
            code=code,
            supporting_values={"growth_a_pct": ga, "growth_b_pct": gb, "period": a1["period"], "prior_period": a0["period"]},
        )
        if rel:
            out.append(rel)

    # Operating leverage: revenue vs ebit / operating_margin
    rev_g, rev_c, rev_p = _growth(series_map.get("revenue") or [])
    ebit_g, ebit_c, ebit_p = _growth(series_map.get("ebit") or [])
    if rev_g is not None and ebit_g is not None and rev_c and ebit_c and rev_p and ebit_p:
        ev = evidence_points(rev_p, rev_c, ebit_p, ebit_c, metrics=["revenue", "revenue", "ebit", "ebit"])
        conf = confidence_for_points(ev, history_n=series_history_n(series_map, "revenue", "ebit"), coverage_pct=coverage_pct)
        if rev_g > 0 and ebit_g > rev_g + 1.0:
            code = "operating_leverage_increased"
            obs = f"EBIT grew {ebit_g:.1f}% while revenue grew {rev_g:.1f}% — operating leverage increased."
            adverse = False
        elif rev_g > 0 and ebit_g < rev_g - 1.0:
            code = "operating_leverage_weakened"
            obs = f"EBIT grew only {ebit_g:.1f}% against revenue growth of {rev_g:.1f}% — operating leverage weakened."
            adverse = True
        else:
            code = ""
            obs = ""
            adverse = False
        if code:
            rel = make_relationship(
                category="Margin Drivers",
                relationship="Revenue vs EBIT",
                observation=obs,
                narrative=obs,
                evidence=ev,
                confidence=conf,
                severity=severity_for(code, adverse=adverse),
                code=code,
                supporting_values={"revenue_growth_pct": rev_g, "ebit_growth_pct": ebit_g, "period": rev_c["period"]},
            )
            if rel:
                out.append(rel)
    return out


def analyse_profitability_drivers(series_map: dict[str, list], *, coverage_pct: float | None) -> list[dict]:
    out: list[dict] = []
    rev_g, rev_c, rev_p = _growth(series_map.get("revenue") or [])
    om_g, om_c, om_p = _growth(series_map.get("operating_margin") or [])
    gm_g, gm_c, gm_p = _growth(series_map.get("gross_margin") or [])
    pat_g, pat_c, pat_p = _growth(series_map.get("net_income") or [])
    fcf_g, fcf_c, fcf_p = _growth(series_map.get("free_cash_flow") or [])
    rec_g, rec_c, rec_p = _growth(series_map.get("receivables") or [])

    candidates: list[tuple] = []
    if rev_g is not None and om_g is not None and rev_g > 0 and om_g > 0:
        candidates.append(
            (
                "possible_operating_leverage",
                "Revenue ↑ / Operating Margin ↑",
                "Revenue and operating margin both increased — consistent with operating leverage.",
                False,
                ["revenue", "operating_margin"],
                (rev_p, rev_c, om_p, om_c),
                {"revenue_growth_pct": rev_g, "operating_margin_change_pct": om_g},
            )
        )
    if rev_g is not None and om_g is not None and rev_g > 0 and om_g < 0:
        candidates.append(
            (
                "margin_pressure",
                "Revenue ↑ / Operating Margin ↓",
                "Revenue increased while operating margin declined — margin pressure.",
                True,
                ["revenue", "operating_margin"],
                (rev_p, rev_c, om_p, om_c),
                {"revenue_growth_pct": rev_g, "operating_margin_change_pct": om_g},
            )
        )
    if rev_g is not None and om_g is not None and rev_g < 0 and om_g > 0:
        candidates.append(
            (
                "cost_discipline",
                "Revenue ↓ / Operating Margin ↑",
                "Revenue declined while operating margin expanded — cost discipline observed.",
                False,
                ["revenue", "operating_margin"],
                (rev_p, rev_c, om_p, om_c),
                {"revenue_growth_pct": rev_g, "operating_margin_change_pct": om_g},
            )
        )
    if rev_g is not None and pat_g is not None and rev_g > 0 and pat_g < 0:
        candidates.append(
            (
                "profitability_deterioration",
                "Revenue ↑ / PAT ↓",
                "Revenue increased while PAT declined — profitability deterioration.",
                True,
                ["revenue", "net_income"],
                (rev_p, rev_c, pat_p, pat_c),
                {"revenue_growth_pct": rev_g, "pat_growth_pct": pat_g},
            )
        )
    if rev_g is not None and fcf_g is not None and rev_g > 0 and fcf_g < 0:
        candidates.append(
            (
                "cash_conversion_pressure",
                "Revenue ↑ / FCF ↓",
                "Revenue increased while free cash flow declined — cash conversion pressure.",
                True,
                ["revenue", "free_cash_flow"],
                (rev_p, rev_c, fcf_p, fcf_c),
                {"revenue_growth_pct": rev_g, "fcf_growth_pct": fcf_g},
            )
        )
    if rev_g is not None and rec_g is not None and rev_g > 0 and rec_g > (rev_g + 5.0):
        candidates.append(
            (
                "working_capital_deterioration_receivables",
                "Revenue ↑ / Receivables ↑↑",
                f"Receivables grew {rec_g:.1f}% versus revenue growth of {rev_g:.1f}% — working capital deterioration.",
                True,
                ["revenue", "receivables"],
                (rev_p, rev_c, rec_p, rec_c),
                {"revenue_growth_pct": rev_g, "receivables_growth_pct": rec_g},
            )
        )
    if rev_g is not None and gm_g is not None and rev_g > 0 and gm_g > 0:
        candidates.append(
            (
                "gross_margin_support",
                "Revenue ↑ / Gross Margin ↑",
                "Revenue and gross margin both increased.",
                False,
                ["revenue", "gross_margin"],
                (rev_p, rev_c, gm_p, gm_c),
                {"revenue_growth_pct": rev_g, "gross_margin_change_pct": gm_g},
            )
        )

    for code, relationship, obs, adverse, mets, rows, vals in candidates:
        pts = [r for r in rows if r]
        if len(pts) < 2:
            continue
        labels: list[str] = []
        for m in mets:
            labels.extend([m, m])
        ev = evidence_points(*pts, metrics=labels[: len(pts)])
        conf = confidence_for_points(ev, history_n=series_history_n(series_map, *mets), coverage_pct=coverage_pct)
        rel = make_relationship(
            category="Profitability Drivers",
            relationship=relationship,
            observation=obs,
            narrative=obs,
            evidence=ev,
            confidence=conf,
            severity=severity_for(code, adverse=adverse),
            code=code,
            supporting_values={**vals, "period": (rev_c or {}).get("period")},
        )
        if rel:
            out.append(rel)
    return out


def analyse_cash_quality(series_map: dict[str, list], *, coverage_pct: float | None) -> list[dict]:
    out: list[dict] = []
    pat = normalize_series(series_map.get("net_income") or [])
    ocf = normalize_series(series_map.get("operating_cash_flow") or [])
    fcf = normalize_series(series_map.get("free_cash_flow") or [])
    pair = latest_pair(pat, ocf)
    prior = prior_pair(pat, ocf)
    if pair:
        p1, o1 = pair
        ratio = float(o1["value"]) / float(p1["value"]) if float(p1["value"]) != 0 else None
        ev = evidence_points(p1, o1, metrics=["net_income", "operating_cash_flow"])
        hist = series_history_n(series_map, "net_income", "operating_cash_flow")
        conf = confidence_for_points(ev, history_n=hist, coverage_pct=coverage_pct)
        if ratio is not None:
            if ratio >= 1.0:
                code, obs, adverse = "strong_cash_conversion", f"Operating cash flow ({o1['value']:.2f}) covers PAT ({p1['value']:.2f}); conversion ratio {ratio:.2f}.", False
            elif ratio >= 0.7:
                code, obs, adverse = "adequate_cash_conversion", f"Operating cash flow ({o1['value']:.2f}) is below PAT ({p1['value']:.2f}); conversion ratio {ratio:.2f}.", True
            else:
                code, obs, adverse = "weak_cash_conversion", f"Operating cash flow ({o1['value']:.2f}) lags PAT ({p1['value']:.2f}); conversion ratio {ratio:.2f}.", True
            rel = make_relationship(
                category="Cash Quality",
                relationship="PAT vs Operating Cash Flow",
                observation=obs,
                narrative=obs,
                evidence=ev,
                confidence=conf,
                severity=severity_for(code, adverse=adverse),
                code=code,
                supporting_values={"conversion_ratio": round(ratio, 4), "period": p1["period"]},
            )
            if rel:
                out.append(rel)
            if ratio < 0.7:
                rel2 = make_relationship(
                    category="Cash Quality",
                    relationship="PAT vs Operating Cash Flow",
                    observation="Profit is not fully supported by operating cash flow at the latest aligned period.",
                    narrative="Profit is not fully supported by operating cash flow at the latest aligned period.",
                    evidence=ev,
                    confidence=conf,
                    severity="High",
                    code="profit_not_supported_by_cash",
                    supporting_values={"conversion_ratio": round(ratio, 4), "period": p1["period"]},
                )
                if rel2:
                    out.append(rel2)

    if prior and pair:
        p0, o0 = prior
        p1, o1 = pair
        gp = pct_change(float(p1["value"]), float(p0["value"]))
        go = pct_change(float(o1["value"]), float(o0["value"]))
        if gp is not None and go is not None and gp > 0 and go < gp - 5.0:
            ev = evidence_points(p0, p1, o0, o1, metrics=["net_income", "net_income", "operating_cash_flow", "operating_cash_flow"])
            conf = confidence_for_points(ev, history_n=series_history_n(series_map, "net_income", "operating_cash_flow"), coverage_pct=coverage_pct)
            obs = (
                f"Operating cash flow has grown materially slower than profit "
                f"({go:.1f}% vs PAT {gp:.1f}%) over the latest comparable periods."
            )
            rel = make_relationship(
                category="Cash Quality",
                relationship="PAT vs Operating Cash Flow",
                observation=obs,
                narrative=obs,
                evidence=ev,
                confidence=conf,
                severity="Medium",
                code="ocf_slower_than_pat",
                supporting_values={"pat_growth_pct": gp, "ocf_growth_pct": go, "period": p1["period"], "prior_period": p0["period"]},
            )
            if rel:
                out.append(rel)

    fcf_g, fcf_c, fcf_p = _growth(fcf)
    if fcf_g is not None and fcf_c and fcf_p:
        ev = evidence_points(fcf_p, fcf_c, metrics=["free_cash_flow", "free_cash_flow"])
        conf = confidence_for_points(ev, history_n=len(fcf), coverage_pct=coverage_pct)
        if fcf_g > 0:
            code, obs, adverse = "improving_cash_generation", f"Free cash flow improved {fcf_g:.1f}% period-to-period.", False
        else:
            code, obs, adverse = "deteriorating_cash_generation", f"Free cash flow declined {abs(fcf_g):.1f}% period-to-period.", True
        rel = make_relationship(
            category="Cash Flow Drivers",
            relationship="Free Cash Flow trend",
            observation=obs,
            narrative=obs,
            evidence=ev,
            confidence=conf,
            severity=severity_for(code, adverse=adverse),
            code=code,
            supporting_values={"fcf_growth_pct": fcf_g, "period": fcf_c["period"]},
        )
        if rel:
            out.append(rel)
    return out


def analyse_working_capital(series_map: dict[str, list], *, coverage_pct: float | None) -> list[dict]:
    out: list[dict] = []
    checks = [
        ("inventory", "inventory_build", "Inventory build", True),
        ("receivables", "receivable_expansion", "Receivable expansion", True),
        ("payables", "supplier_financing_changes", "Supplier financing changes", False),
        ("working_capital", "working_capital_pressure", "Working capital pressure", True),
    ]
    for metric, code, label, rising_adverse in checks:
        g, curr, prior = _growth(series_map.get(metric) or [])
        if g is None or not curr or not prior:
            continue
        d = direction(g)
        if d == "flat":
            continue
        adverse = (d == "up") if rising_adverse else (d == "down" and metric == "payables")
        # payables up can be supplier financing (neutral/info); payables down sharply = financing change
        if metric == "payables":
            adverse = abs(g) >= 10
            code = "supplier_financing_changes"
        if metric == "working_capital":
            if d == "up" and g >= 5:
                code, adverse = "working_capital_pressure", True
            elif d == "down":
                code, adverse = "improving_efficiency", False
            else:
                continue
        ev = evidence_points(prior, curr, metrics=[metric, metric])
        conf = confidence_for_points(ev, history_n=series_history_n(series_map, metric), coverage_pct=coverage_pct)
        obs = f"{label}: {metric.replace('_', ' ')} changed {g:.1f}% from {prior['period']} to {curr['period']}."
        rel = make_relationship(
            category="Working Capital Drivers",
            relationship=f"{metric} trend",
            observation=obs,
            narrative=obs,
            evidence=ev,
            confidence=conf,
            severity=severity_for(code, adverse=adverse),
            code=code,
            supporting_values={"growth_pct": g, "period": curr["period"], "prior_period": prior["period"]},
        )
        if rel:
            out.append(rel)

    # CCC proxy if all three present: DIO+DSO-DPO not computed without COGS/revenue days — use WC vs revenue
    rev_g, rev_c, rev_p = _growth(series_map.get("revenue") or [])
    wc_g, wc_c, wc_p = _growth(series_map.get("working_capital") or [])
    if rev_g is not None and wc_g is not None and rev_c and wc_c and rev_p and wc_p and rev_g > 0 and wc_g > rev_g + 5:
        ev = evidence_points(rev_p, rev_c, wc_p, wc_c, metrics=["revenue", "revenue", "working_capital", "working_capital"])
        conf = confidence_for_points(ev, history_n=series_history_n(series_map, "revenue", "working_capital"), coverage_pct=coverage_pct)
        obs = f"Working capital grew {wc_g:.1f}% versus revenue {rev_g:.1f}% — working capital pressure relative to sales."
        rel = make_relationship(
            category="Working Capital",
            relationship="Revenue vs Working Capital",
            observation=obs,
            narrative=obs,
            evidence=ev,
            confidence=conf,
            severity="Medium",
            code="wc_vs_revenue_pressure",
            supporting_values={"revenue_growth_pct": rev_g, "wc_growth_pct": wc_g, "period": rev_c["period"]},
        )
        if rel:
            out.append(rel)
    return out


def analyse_balance_sheet(series_map: dict[str, list], *, coverage_pct: float | None) -> list[dict]:
    out: list[dict] = []
    debt_g, debt_c, debt_p = _growth(series_map.get("total_debt") or [])
    cash_g, cash_c, cash_p = _growth(series_map.get("cash") or [])
    nd_g, nd_c, nd_p = _growth(series_map.get("net_debt") or [])

    if debt_g is not None and debt_c and debt_p:
        ev = evidence_points(debt_p, debt_c, metrics=["total_debt", "total_debt"])
        conf = confidence_for_points(ev, history_n=series_history_n(series_map, "total_debt"), coverage_pct=coverage_pct)
        if debt_g > 0:
            code, obs, adverse = "increasing_leverage", f"Total debt increased {debt_g:.1f}%.", True
        else:
            code, obs, adverse = "deleveraging", f"Total debt declined {abs(debt_g):.1f}%.", False
        rel = make_relationship(
            category="Balance Sheet Drivers",
            relationship="Debt trend",
            observation=obs,
            narrative=obs,
            evidence=ev,
            confidence=conf,
            severity=severity_for(code, adverse=adverse),
            code=code,
            supporting_values={"debt_growth_pct": debt_g, "period": debt_c["period"]},
        )
        if rel:
            out.append(rel)

    if cash_g is not None and cash_c and cash_p:
        ev = evidence_points(cash_p, cash_c, metrics=["cash", "cash"])
        conf = confidence_for_points(ev, history_n=series_history_n(series_map, "cash"), coverage_pct=coverage_pct)
        if cash_g > 0:
            code, obs, adverse = "liquidity_improvement", f"Cash increased {cash_g:.1f}%.", False
        else:
            code, obs, adverse = "liquidity_deterioration", f"Cash declined {abs(cash_g):.1f}%.", True
        rel = make_relationship(
            category="Balance Sheet Drivers",
            relationship="Cash trend",
            observation=obs,
            narrative=obs,
            evidence=ev,
            confidence=conf,
            severity=severity_for(code, adverse=adverse),
            code=code,
            supporting_values={"cash_growth_pct": cash_g, "period": cash_c["period"]},
        )
        if rel:
            out.append(rel)

    # Debt / EBITDA if both present at same period
    pair = latest_pair(series_map.get("total_debt") or [], series_map.get("ebitda") or [])
    if pair:
        d1, e1 = pair
        if float(e1["value"]) != 0:
            ratio = float(d1["value"]) / float(e1["value"])
            ev = evidence_points(d1, e1, metrics=["total_debt", "ebitda"])
            conf = confidence_for_points(ev, history_n=series_history_n(series_map, "total_debt", "ebitda"), coverage_pct=coverage_pct)
            adverse = ratio >= 2.5
            rel = make_relationship(
                category="Balance Sheet",
                relationship="Debt / EBITDA",
                observation=f"Debt/EBITDA is {ratio:.2f} at {d1['period']}.",
                narrative=f"Debt/EBITDA is {ratio:.2f} at {d1['period']}.",
                evidence=ev,
                confidence=conf,
                severity="Medium" if adverse else "Low",
                code="debt_to_ebitda",
                supporting_values={"debt_to_ebitda": round(ratio, 4), "period": d1["period"]},
            )
            if rel:
                out.append(rel)

    ic = normalize_series(series_map.get("interest_coverage") or [])
    if len(ic) >= 1:
        row = ic[-1]
        ev = evidence_points(row, metrics=["interest_coverage"])
        conf = confidence_for_points(ev, history_n=len(ic), coverage_pct=coverage_pct)
        val = float(row["value"])
        adverse = val < 3.0
        rel = make_relationship(
            category="Balance Sheet",
            relationship="Interest Coverage",
            observation=f"Interest coverage is {val:.2f} at {row['period']}.",
            narrative=f"Interest coverage is {val:.2f} at {row['period']}.",
            evidence=ev,
            confidence=conf,
            severity="High" if val < 2 else ("Medium" if adverse else "Low"),
            code="interest_coverage_level",
            supporting_values={"interest_coverage": val, "period": row["period"]},
        )
        if rel:
            out.append(rel)

    _ = nd_g  # net debt optional path covered via debt/cash
    return out


def analyse_capital_allocation(series_map: dict[str, list], *, coverage_pct: float | None) -> list[dict]:
    out: list[dict] = []
    capex_g, capex_c, capex_p = _growth(series_map.get("capex") or [])
    div_g, div_c, div_p = _growth(series_map.get("dividends") or [])
    bb_g, bb_c, bb_p = _growth(series_map.get("share_buybacks") or [])
    debt_g, debt_c, debt_p = _growth(series_map.get("total_debt") or [])

    # Capex intensity vs revenue
    rev_g, rev_c, rev_p = _growth(series_map.get("revenue") or [])
    if capex_g is not None and rev_g is not None and capex_c and rev_c and capex_p and rev_p:
        ev = evidence_points(capex_p, capex_c, rev_p, rev_c, metrics=["capex", "capex", "revenue", "revenue"])
        conf = confidence_for_points(ev, history_n=series_history_n(series_map, "capex", "revenue"), coverage_pct=coverage_pct)
        if capex_g > rev_g + 10 and capex_g > 0:
            code, obs, adverse = "aggressive_expansion", f"Capex grew {capex_g:.1f}% versus revenue {rev_g:.1f}% — aggressive expansion signal.", True
        elif abs(capex_g) < 5 and debt_g is not None and debt_g < 0:
            code, obs, adverse = "conservative_capital_allocation", "Capex stable with declining debt — conservative capital allocation.", False
        else:
            code = ""
            obs = ""
            adverse = False
        if code:
            rel = make_relationship(
                category="Capital Allocation Drivers",
                relationship="Capex vs Revenue",
                observation=obs,
                narrative=obs,
                evidence=ev,
                confidence=conf,
                severity=severity_for(code, adverse=adverse),
                code=code,
                supporting_values={"capex_growth_pct": capex_g, "revenue_growth_pct": rev_g, "period": capex_c["period"]},
            )
            if rel:
                out.append(rel)

    if div_g is not None and div_c and div_p and div_g > 0:
        ev = evidence_points(div_p, div_c, metrics=["dividends", "dividends"])
        conf = confidence_for_points(ev, history_n=series_history_n(series_map, "dividends"), coverage_pct=coverage_pct)
        rel = make_relationship(
            category="Capital Allocation Drivers",
            relationship="Dividends",
            observation=f"Dividends increased {div_g:.1f}% — shareholder return focus.",
            narrative=f"Dividends increased {div_g:.1f}% — shareholder return focus.",
            evidence=ev,
            confidence=conf,
            severity="Low",
            code="shareholder_return_focus",
            supporting_values={"dividends_growth_pct": div_g, "period": div_c["period"]},
        )
        if rel:
            out.append(rel)

    if bb_g is not None and bb_c and bb_p and bb_g > 0:
        ev = evidence_points(bb_p, bb_c, metrics=["share_buybacks", "share_buybacks"])
        conf = confidence_for_points(ev, history_n=series_history_n(series_map, "share_buybacks"), coverage_pct=coverage_pct)
        rel = make_relationship(
            category="Capital Allocation Drivers",
            relationship="Share Buybacks",
            observation=f"Share buybacks increased {bb_g:.1f}% — shareholder return focus.",
            narrative=f"Share buybacks increased {bb_g:.1f}% — shareholder return focus.",
            evidence=ev,
            confidence=conf,
            severity="Low",
            code="shareholder_return_buybacks",
            supporting_values={"buybacks_growth_pct": bb_g, "period": bb_c["period"]},
        )
        if rel:
            out.append(rel)

    if debt_g is not None and debt_c and debt_p and debt_g < 0:
        ev = evidence_points(debt_p, debt_c, metrics=["total_debt", "total_debt"])
        conf = confidence_for_points(ev, history_n=series_history_n(series_map, "total_debt"), coverage_pct=coverage_pct)
        rel = make_relationship(
            category="Capital Allocation Drivers",
            relationship="Debt repayment",
            observation=f"Debt declined {abs(debt_g):.1f}% — balance sheet strengthening.",
            narrative=f"Debt declined {abs(debt_g):.1f}% — balance sheet strengthening.",
            evidence=ev,
            confidence=conf,
            severity="Low",
            code="balance_sheet_strengthening",
            supporting_values={"debt_growth_pct": debt_g, "period": debt_c["period"]},
        )
        if rel:
            out.append(rel)
    return out


def analyse_returns(series_map: dict[str, list], *, coverage_pct: float | None) -> list[dict]:
    out: list[dict] = []
    for metric in ("roe", "roce", "roic", "asset_turnover"):
        g, curr, prior = _growth(series_map.get(metric) or [])
        if g is None or not curr or not prior:
            continue
        ev = evidence_points(prior, curr, metrics=[metric, metric])
        conf = confidence_for_points(ev, history_n=series_history_n(series_map, metric), coverage_pct=coverage_pct)
        if g > 0:
            code, obs, adverse = f"{metric}_improving_efficiency", f"{metric.upper()} improved ({prior['value']:.2f} → {curr['value']:.2f}).", False
        else:
            code, obs, adverse = f"{metric}_declining_efficiency", f"{metric.upper()} declined ({prior['value']:.2f} → {curr['value']:.2f}).", True
        rel = make_relationship(
            category="Return Drivers",
            relationship=f"{metric.upper()} trend",
            observation=obs,
            narrative=obs,
            evidence=ev,
            confidence=conf,
            severity=severity_for(code, adverse=adverse),
            code=code,
            supporting_values={"change_pct": g, "period": curr["period"], "prior_period": prior["period"]},
        )
        if rel:
            out.append(rel)
    return out


def analyse_all(series_map: dict[str, list], *, coverage_pct: float | None = None) -> list[dict]:
    rows: list[dict] = []
    rows.extend(analyse_income_chain(series_map, coverage_pct=coverage_pct))
    rows.extend(analyse_profitability_drivers(series_map, coverage_pct=coverage_pct))
    rows.extend(analyse_cash_quality(series_map, coverage_pct=coverage_pct))
    rows.extend(analyse_working_capital(series_map, coverage_pct=coverage_pct))
    rows.extend(analyse_balance_sheet(series_map, coverage_pct=coverage_pct))
    rows.extend(analyse_capital_allocation(series_map, coverage_pct=coverage_pct))
    rows.extend(analyse_returns(series_map, coverage_pct=coverage_pct))
    # Deduplicate by code+relationship+period
    seen = set()
    unique = []
    for r in rows:
        key = (r.get("code"), r.get("relationship"), (r.get("supporting_values") or {}).get("period"))
        if key in seen:
            continue
        seen.add(key)
        unique.append(r)
    return unique
