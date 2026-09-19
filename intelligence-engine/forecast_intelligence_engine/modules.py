"""FIE forecast modules — evidence-backed, no recommendations, no target prices."""

from __future__ import annotations

from typing import Any

from forecast_intelligence_engine.confidence import section_confidence
from forecast_intelligence_engine.models import FORBIDDEN_TOKENS, WINDOWS
from forecast_intelligence_engine.trend import (
    balance_sheet_forecast,
    business_forecast,
    historical_cagrs,
    profitability_forecast,
    scenario_probabilities,
)


def _block(
    title: str,
    findings: list[str],
    *,
    observed: list[str],
    derived: list[str],
    assumed: list[str],
    evidence: list[dict[str, Any]],
    confidence: dict[str, Any],
    status: str = "ok",
    **extra: Any,
) -> dict[str, Any]:
    text = " ".join(findings)
    lowered = f" {text.lower()} "
    for tok in FORBIDDEN_TOKENS:
        if f" {tok} " in lowered or lowered.strip() == tok:
            return {
                "ok": False,
                "title": title,
                "status": "dqiv_reject",
                "error": f"forbidden_language:{tok}",
                "findings": [],
                "explainability": {"observed": observed, "derived": derived, "assumed": []},
                "evidence": evidence,
                "confidence": {"confidence": "Low", "score": 0.0, "missing": ["language_policy"]},
            }
    out = {
        "ok": True,
        "title": title,
        "status": status,
        "findings": findings,
        "summary": " ".join(findings)[:1400],
        "explainability": {
            "observed": observed,
            "derived": derived,
            "assumed": assumed,
        },
        "evidence": evidence,
        "confidence": confidence,
    }
    out.update(extra)
    return out


def executive(bundle: dict[str, Any]) -> dict[str, Any]:
    m = bundle.get("master") or {}
    name = m.get("company_name") or bundle.get("symbol")
    sector = m.get("sector") or "unspecified sector"
    inputs = bundle.get("inputs_present") or {}
    cagrs = historical_cagrs(bundle.get("annual") or [])
    rev_cagr = cagrs.get("revenue")
    hvie = bundle.get("hvie") or {}
    vpae = bundle.get("vpae") or {}
    rie = bundle.get("rie") or {}
    rie_q = (rie.get("research_quality") or {}).get("research_confidence")
    missing = [k for k, v in inputs.items() if not v]
    findings = [
        f"Business outlook for {name} ({sector}) is framed from warehouse financial history and engine packs.",
    ]
    if rev_cagr is not None:
        findings.append(f"Growth outlook anchors on observed revenue CAGR of {rev_cagr * 100:.1f}%.")
    else:
        findings.append("Growth outlook is limited — insufficient annual history for a stable CAGR.")
    regime = hvie.get("regime")
    pct = hvie.get("historical_percentile")
    if pct is not None:
        findings.append(f"Valuation outlook: own-history percentile {pct} ({regime or 'regime n/a'}).")
    else:
        findings.append("Valuation outlook waiting on HVIE historical coverage.")
    findings.append(
        f"Risk outlook reflects data completeness ({len(inputs) - len(missing)}/{len(inputs)} inputs) "
        f"and research confidence {rie_q or 'n/a'}."
    )
    findings.append(
        f"Primary valuation model from VPAE: {vpae.get('primary_model') or 'unavailable'}."
    )
    if missing:
        findings.append(f"Key monitoring: close gaps in {', '.join(missing[:5])}.")
    conf = section_confidence(
        required_hits=sum(1 for k in ("financials_annual", "hvie", "master") if inputs.get(k)),
        required_total=3,
        observations=len(bundle.get("annual") or []),
        missing=missing[:6],
    )
    return _block(
        "Executive Forecast",
        findings,
        observed=[f"sector={sector}", f"revenue_cagr={rev_cagr}"],
        derived=[f"historical_percentile={pct}", f"regime={regime}"],
        assumed=["Industry demand path remains consistent with recent history unless stated otherwise."],
        evidence=[{"source": "warehouse.financials_annual"}, {"source": "hvie/vpae/rie"}],
        confidence=conf,
        assumptions=[
            {"name": "revenue_growth", "value_pct": round((rev_cagr or 0) * 100, 2) if rev_cagr is not None else None, "basis": "observed_cagr"},
            {"name": "valuation_model", "value": vpae.get("primary_model"), "basis": "vpae"},
            {"name": "market_regime", "value": regime, "basis": "hvie"},
        ],
        monitoring=missing[:8] or ["quarterly_results", "margin_trajectory", "valuation_regime"],
    )


def business(bundle: dict[str, Any]) -> dict[str, Any]:
    annual = bundle.get("annual") or []
    base = business_forecast(annual, scenario="base")
    inputs = bundle.get("inputs_present") or {}
    if not base.get("ok"):
        conf = section_confidence(required_hits=0, required_total=2, missing=["financials_annual"])
        return _block(
            "Business Forecast",
            ["Business forecast unavailable — need at least two annual statements."],
            observed=[],
            derived=[],
            assumed=[],
            evidence=[{"source": "warehouse.financials_annual"}],
            confidence=conf,
            status="waiting_statements",
            forecast={},
        )
    cagrs = base.get("growth_rates_used") or {}
    findings = [
        f"Base-case business forecast uses observed growth rates from {base.get('base_period')}.",
        f"Windows covered: {', '.join(WINDOWS)}.",
        f"Revenue growth used: {cagrs.get('revenue')}%. PAT growth used: {cagrs.get('pat')}%.",
    ]
    conf = section_confidence(
        required_hits=1 if inputs.get("financials_annual") else 0,
        required_total=1,
        observations=len(annual),
        missing=[] if inputs.get("financials_annual") else ["financials_annual"],
    )
    return _block(
        "Business Forecast",
        findings,
        observed=[f"growth_rates={cagrs}"],
        derived=["forward_levels_from_cagr"],
        assumed=["Growth continues near observed CAGR unless scenario multipliers applied."],
        evidence=[{"source": "warehouse.financials_annual"}],
        confidence=conf,
        forecast=base.get("lines") or {},
        base_period=base.get("base_period"),
        base_values=base.get("base_values") or {},
        windows=list(WINDOWS),
        growth_rates_used=cagrs,
    )


def growth(bundle: dict[str, Any]) -> dict[str, Any]:
    cagrs = historical_cagrs(bundle.get("annual") or [])
    findings = ["Growth engine reports observed CAGRs used as forecast anchors (not price forecasts)."]
    for k, v in cagrs.items():
        if v is not None:
            findings.append(f"{k.upper()} CAGR: {v * 100:.1f}%.")
    if all(v is None for v in cagrs.values()):
        findings.append("Insufficient history to compute stable CAGRs.")
    conf = section_confidence(
        required_hits=1 if any(v is not None for v in cagrs.values()) else 0,
        required_total=1,
        observations=len(bundle.get("annual") or []),
    )
    return _block(
        "Growth Forecast",
        findings,
        observed=[f"{k}={v}" for k, v in cagrs.items() if v is not None],
        derived=["cagr_from_annual_statements"],
        assumed=["Future growth remains bounded by observed history unless scenarios widen the band."],
        evidence=[{"source": "warehouse.financials_annual"}],
        confidence=conf,
        cagrs={k: (round(v * 100, 2) if v is not None else None) for k, v in cagrs.items()},
    )


def profitability(bundle: dict[str, Any]) -> dict[str, Any]:
    pack = profitability_forecast(bundle.get("annual") or [], scenario="base")
    if not pack.get("ok"):
        conf = section_confidence(required_hits=0, required_total=1, missing=["margins"])
        return _block(
            "Profitability Forecast",
            ["Profitability forecast unavailable without revenue and margin inputs."],
            observed=[],
            derived=[],
            assumed=[],
            evidence=[{"source": "warehouse.financials_annual"}],
            confidence=conf,
            margins={},
        )
    findings = [
        "Base-case margins held near latest observed ratios; scenarios adjust by disclosed margin deltas.",
        f"Windows: {', '.join(WINDOWS)}.",
    ]
    conf = section_confidence(required_hits=1, required_total=1, observations=len(bundle.get("annual") or []))
    return _block(
        "Profitability Forecast",
        findings,
        observed=["latest_margins"],
        derived=["scenario_margin_deltas"],
        assumed=["Operating structure remains comparable to the latest fiscal year."],
        evidence=[{"source": "warehouse.financials_annual"}],
        confidence=conf,
        margins=pack.get("margins") or {},
    )


def balance_sheet(bundle: dict[str, Any]) -> dict[str, Any]:
    pack = balance_sheet_forecast(bundle.get("annual") or [], scenario="base")
    if not pack.get("ok"):
        conf = section_confidence(required_hits=0, required_total=1, missing=["financials_annual"])
        return _block(
            "Balance Sheet Forecast",
            ["Balance sheet forecast unavailable without annual statements."],
            observed=[],
            derived=[],
            assumed=[],
            evidence=[{"source": "warehouse.financials_annual"}],
            confidence=conf,
            forecast={},
        )
    findings = [
        "Cash, debt, book value and leverage are projected from observed equity/revenue growth anchors.",
        "Liquidity and leverage figures are outlook ranges — not trading signals.",
    ]
    conf = section_confidence(required_hits=1, required_total=1, observations=len(bundle.get("annual") or []))
    return _block(
        "Balance Sheet Forecast",
        findings,
        observed=["cash", "debt", "equity"],
        derived=["net_debt", "leverage"],
        assumed=["Capital structure evolves gradually with book equity growth."],
        evidence=[{"source": "warehouse.financials_annual"}],
        confidence=conf,
        forecast=pack.get("lines") or {},
    )


def valuation(bundle: dict[str, Any]) -> dict[str, Any]:
    hvie = bundle.get("hvie") or {}
    uve = bundle.get("uve") or {}
    vpae = bundle.get("vpae") or {}
    varie = bundle.get("varie") or {}
    pct = hvie.get("historical_percentile")
    regime = hvie.get("regime")
    model = vpae.get("primary_model") or uve.get("primary_model")
    premium = varie.get("premium_pct")
    findings = [
        "Valuation outlook describes expected multiple ranges from HVIE/UVE/VARIE — never a target price.",
    ]
    if pct is not None:
        findings.append(f"Current own-history percentile {pct} ({regime or 'n/a'}).")
        # Band outlook: mean-reversion toward median band if extreme.
        if float(pct) >= 80:
            findings.append("Outlook: elevated valuation vs own history — premium may compress if fundamentals do not keep pace.")
        elif float(pct) <= 20:
            findings.append("Outlook: discounted vs own history — multiple may expand if quality persists.")
        else:
            findings.append("Outlook: valuation sits near historical mid-range.")
    else:
        findings.append("HVIE percentile unavailable — valuation outlook incomplete.")
    if model:
        findings.append(f"Applicable model (VPAE): {model}.")
    if premium is not None:
        findings.append(f"VARIE premium/discount context: {premium}%.")
    # Expected range placeholders from percentile buckets (explainable, not a price).
    range_map = {
        "pe": {"low": "p25", "mid": "median", "high": "p75"},
        "pb": {"low": "p25", "mid": "median", "high": "p75"},
        "ev_ebitda": {"low": "p25", "mid": "median", "high": "p75"},
        "ev_sales": {"low": "p25", "mid": "median", "high": "p75"},
        "dividend_yield": {"low": "p25", "mid": "median", "high": "p75"},
    }
    conf = section_confidence(
        required_hits=sum(1 for k in ("hvie", "vpae") if (bundle.get("inputs_present") or {}).get(k)),
        required_total=2,
        observations=len(bundle.get("historical_valuation") or []),
        missing=[k for k in ("hvie", "historical_valuation") if not (bundle.get("inputs_present") or {}).get(k)],
    )
    return _block(
        "Valuation Outlook",
        findings,
        observed=[f"percentile={pct}", f"regime={regime}", f"model={model}"],
        derived=["valuation_band_outlook"],
        assumed=["Multiples are interpreted under the VPAE-applicable model only."],
        evidence=[{"source": "hvie"}, {"source": "uve"}, {"source": "varie"}, {"source": "vpae"}],
        confidence=conf,
        outlook={
            "historical_percentile": pct,
            "regime": regime,
            "primary_model": model,
            "premium_pct": premium,
            "expected_range_basis": range_map,
            "target_price": None,
        },
    )


def scenarios(bundle: dict[str, Any]) -> dict[str, Any]:
    annual = bundle.get("annual") or []
    quality_score = 0.55
    rie = bundle.get("rie") or {}
    rq = rie.get("research_quality") or {}
    if rq.get("score") is not None:
        try:
            quality_score = float(rq["score"])
        except Exception:
            pass
    stability = min(1.0, len(annual) / 8.0)
    probs = scenario_probabilities(stability=stability, confidence_score=quality_score)
    packs = {
        "bull": business_forecast(annual, scenario="bull"),
        "base": business_forecast(annual, scenario="base"),
        "bear": business_forecast(annual, scenario="bear"),
    }
    findings = [
        f"Scenario probabilities — Bull {probs['bull']}%, Base {probs['base']}%, Bear {probs['bear']}% (sum 100).",
        "Bull/Base/Bear apply disclosed growth and margin multipliers to observed history.",
        "Scenarios describe business paths — not trading recommendations.",
    ]
    conf = section_confidence(
        required_hits=1 if packs["base"].get("ok") else 0,
        required_total=1,
        observations=len(annual),
    )
    return _block(
        "Scenario Engine",
        findings,
        observed=[f"annual_obs={len(annual)}"],
        derived=[f"probabilities={probs}"],
        assumed=[
            "Bull growth multiplier 1.25x observed CAGR",
            "Bear growth multiplier 0.55x observed CAGR",
            "Base uses observed CAGR unchanged",
        ],
        evidence=[{"source": "warehouse.financials_annual"}, {"source": "fie.scenario_engine"}],
        confidence=conf,
        probabilities=probs,
        scenarios={
            k: {
                "ok": v.get("ok"),
                "base_period": v.get("base_period"),
                "base_values": v.get("base_values") or {},
                "growth_rates_used": v.get("growth_rates_used"),
                "lines": {lk: dict(lv or {}) for lk, lv in (v.get("lines") or {}).items()},
            }
            for k, v in packs.items()
        },
    )


def sensitivity(bundle: dict[str, Any]) -> dict[str, Any]:
    base = business_forecast(bundle.get("annual") or [], scenario="base")
    rev_fy1 = ((base.get("lines") or {}).get("revenue") or {}).get("FY+1")
    pat_fy1 = ((base.get("lines") or {}).get("pat") or {}).get("FY+1")
    shocks = [
        ("revenue", +5), ("revenue", -5), ("revenue", +10), ("revenue", -10),
        ("margins", +2), ("margins", -2), ("margins", +5), ("margins", -5),
        ("tax", +2), ("tax", -2),
        ("terminal_multiple", +2), ("terminal_multiple", -2),
        ("interest_rate", +1), ("interest_rate", -1),
    ]
    impacts = []
    for name, delta in shocks:
        impact = None
        if name == "revenue" and rev_fy1 is not None:
            impact = {"revenue_fy1": round(rev_fy1 * (1 + delta / 100.0), 2)}
        elif name == "margins" and pat_fy1 is not None:
            impact = {"pat_fy1_approx": round(pat_fy1 * (1 + delta / 100.0), 2)}
        elif name == "tax" and pat_fy1 is not None:
            impact = {"pat_fy1_approx": round(pat_fy1 * (1 - delta / 200.0), 2)}
        else:
            impact = {"note": "Directional only — no level without base forecast"}
        impacts.append({"shock": f"{name} {delta:+d}{'x' if name == 'terminal_multiple' else '%'}", "impact": impact})
    findings = [
        "Sensitivity shows how FY+1 revenue/PAT levels move under disclosed shocks.",
        "Interest-rate and terminal-multiple shocks are qualitative when EV models are suppressed by VPAE.",
    ]
    conf = section_confidence(required_hits=1 if rev_fy1 is not None else 0, required_total=1, observations=len(bundle.get("annual") or []))
    return _block(
        "Sensitivity Engine",
        findings,
        observed=[f"base_revenue_fy1={rev_fy1}"],
        derived=["shock_impacts"],
        assumed=["Linear local sensitivity around the base forecast."],
        evidence=[{"source": "fie.business_forecast"}],
        confidence=conf,
        sensitivities=impacts,
    )


def risks(bundle: dict[str, Any]) -> dict[str, Any]:
    inputs = bundle.get("inputs_present") or {}
    hvie = bundle.get("hvie") or {}
    rie = bundle.get("rie") or {}
    findings = []
    annual = bundle.get("annual") or []
    last = annual[-1] if annual else {}
    debt = last.get("debt") or last.get("total_debt")
    cash = last.get("cash")
    if not inputs.get("financials_annual"):
        findings.append("Revenue Risk: elevated — statement history incomplete.")
    else:
        findings.append("Revenue Risk: tied to sustainability of observed growth rates.")
    findings.append("Margin Risk: depends on operating leverage and cost inflation.")
    findings.append("Execution Risk: inferred from research confidence and data gaps.")
    if debt is not None:
        findings.append(f"Leverage Risk: latest debt reading present ({debt}).")
    else:
        findings.append("Leverage Risk: debt not available on latest statement.")
    findings.append("Refinancing Risk: monitor maturity profile when cash/debt coverage is thin.")
    pct = hvie.get("historical_percentile")
    if pct is not None and float(pct) >= 80:
        findings.append("Valuation Risk: elevated own-history percentile.")
    else:
        findings.append("Valuation Risk: monitored via HVIE regime and percentile.")
    findings.append("Sector Risk / Macro Risk / Regulatory Risk: use market and research packs; no vendor feeds.")
    rie_risks = ((rie.get("sections") or {}).get("risk") or {}).get("findings") or []
    for f in rie_risks[:3]:
        findings.append(f"Research Risk note: {f}")
    conf = section_confidence(
        required_hits=sum(1 for k in ("financials_annual", "hvie") if inputs.get(k)),
        required_total=2,
        observations=len(annual),
    )
    return _block(
        "Risk Engine",
        findings,
        observed=["debt", "cash", "hvie_percentile"],
        derived=["risk_flags_from_coverage"],
        assumed=["Risks remain relevant until evidence updates."],
        evidence=[{"source": "warehouse"}, {"source": "hvie"}, {"source": "rie"}],
        confidence=conf,
    )


def catalysts(bundle: dict[str, Any]) -> dict[str, Any]:
    actions = bundle.get("corporate_actions") or []
    timeline = bundle.get("research_timeline") or []
    quarterly = bundle.get("quarterly") or []
    findings = [
        "Catalyst Engine lists expected monitoring events — not trade triggers.",
        "Quarterly Results: next results print is the primary near-term catalyst.",
    ]
    if quarterly:
        findings.append(f"Latest quarterly period on file: {quarterly[-1].get('fiscal_period') or quarterly[-1].get('period')}.")
    if actions:
        latest = actions[-1]
        findings.append(
            f"Corporate Actions: latest {latest.get('action_type') or 'action'} on {latest.get('date') or latest.get('action_date') or 'n/a'}."
        )
    else:
        findings.append("Corporate Actions: none recent in warehouse.")
    if timeline:
        findings.append(f"Research timeline events on file: {len(timeline)}.")
    findings.extend([
        "Capex / Expansion / Product Launch: monitor management commentary in filings when present.",
        "Ownership Changes: watch ownership tab updates.",
        "Industry / Macro / Policy cycles: refresh scenarios when market regime packs change.",
    ])
    conf = section_confidence(
        required_hits=1 if (actions or timeline or quarterly) else 0,
        required_total=1,
        observations=len(actions) + len(timeline),
    )
    return _block(
        "Catalyst Engine",
        findings,
        observed=[f"actions={len(actions)}", f"timeline={len(timeline)}"],
        derived=["catalyst_watchlist"],
        assumed=["Catalysts are monitoring items, not certainty of outcomes."],
        evidence=[{"source": "warehouse.corporate_actions"}, {"source": "research_timeline"}],
        confidence=conf,
        catalysts=[
            {"type": "quarterly_results", "status": "expected"},
            {"type": "corporate_actions", "count": len(actions)},
            {"type": "ownership_changes", "status": "watch"},
            {"type": "industry_cycle", "status": "watch"},
            {"type": "macro_cycle", "status": "watch"},
        ],
    )


def confidence_module(bundle: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    inputs = bundle.get("inputs_present") or {}
    missing = [k for k, v in inputs.items() if not v]
    findings = [
        f"Forecast confidence: {quality.get('forecast_confidence')} (score {quality.get('score')}).",
        f"Input coverage: {quality.get('coverage_pct')}%.",
        f"Distribution — High {quality.get('distribution', {}).get('High')}, "
        f"Medium {quality.get('distribution', {}).get('Medium')}, "
        f"Low {quality.get('distribution', {}).get('Low')}.",
    ]
    if missing:
        findings.append(f"Confidence drag from missing: {', '.join(missing[:6])}.")
    return _block(
        "Confidence Engine",
        findings,
        observed=["section_scores", "input_presence"],
        derived=["forecast_quality_score"],
        assumed=[],
        evidence=[{"source": "fie.confidence"}],
        confidence={
            "confidence": quality.get("forecast_confidence"),
            "score": quality.get("score"),
        },
        forecast_quality=quality,
    )


def history_module(bundle: dict[str, Any]) -> dict[str, Any]:
    rows = bundle.get("forecast_history") or []
    findings = [
        f"Forecast history rows on file: {len(rows)} (append-only).",
    ]
    if rows:
        latest = rows[-1]
        findings.append(
            f"Latest stored forecast as_of {latest.get('as_of') or latest.get('generated_at') or 'n/a'} "
            f"status={latest.get('status') or 'n/a'}."
        )
    else:
        findings.append("No prior forecast versions yet — this run becomes the first history entry when persisted.")
    conf = section_confidence(required_hits=1, required_total=1, observations=len(rows))
    return _block(
        "Forecast Timeline",
        findings,
        observed=[f"history_rows={len(rows)}"],
        derived=[],
        assumed=[],
        evidence=[{"source": "warehouse.forecast_history"}],
        confidence=conf,
        history=rows[-20:],
    )


def accuracy_module(bundle: dict[str, Any]) -> dict[str, Any]:
    rows = bundle.get("forecast_accuracy") or []
    findings = [
        f"Forecast accuracy comparisons on file: {len(rows)}.",
        "Accuracy engine compares prior forecasts vs actual statements without rewriting history.",
    ]
    if not rows:
        findings.append("No accuracy rows yet — available after actuals land for a prior forecast vintage.")
    conf = section_confidence(required_hits=1 if rows else 0, required_total=1, observations=len(rows))
    return _block(
        "Forecast Accuracy",
        findings,
        observed=[f"accuracy_rows={len(rows)}"],
        derived=["error_tracking"],
        assumed=[],
        evidence=[{"source": "warehouse.forecast_accuracy"}],
        confidence=conf,
        accuracy=rows[-20:],
    )


MODULE_BUILDERS = {
    "executive": executive,
    "business": business,
    "growth": growth,
    "profitability": profitability,
    "balance_sheet": balance_sheet,
    "valuation": valuation,
    "scenarios": scenarios,
    "sensitivity": sensitivity,
    "risks": risks,
    "catalysts": catalysts,
    "history": history_module,
    "accuracy": accuracy_module,
}
