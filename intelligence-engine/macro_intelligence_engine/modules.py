"""MIE modules — evidence-backed macro intelligence, no recommendations."""

from __future__ import annotations

from typing import Any, Callable, Optional

from macro_intelligence_engine.confidence import section_confidence
from macro_intelligence_engine.indicators import (
    classify_regime,
    company_sensitivity,
    industry_impacts,
    regime_label,
    scenario_probabilities,
    sector_impacts,
)
from macro_intelligence_engine.models import FORBIDDEN_TOKENS, SECTORS


def _resolve_regime(bundle: dict[str, Any]) -> dict[str, Any]:
    """Prefer deterministic cycle rules; use HMAI only when it exposes a clean label."""
    snap = bundle.get("snapshot") or {}
    pack = classify_regime(snap)
    hmai = bundle.get("hmai_regime") or {}
    upstream = regime_label(
        hmai.get("regime") or hmai.get("current_regime") or (hmai.get("data") or {}).get("regime")
    )
    # Ignore verbose catalog labels like "India 2026 current regime"
    if upstream and upstream.lower() not in {"current regime"} and " current regime" not in upstream.lower():
        return {**pack, "regime": upstream, "upstream_label": upstream}
    return pack


def _block(
    title: str,
    findings: list[str],
    *,
    observed: list[str],
    derived: list[str],
    inferred: list[str],
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
                "explainability": {"observed": observed, "derived": derived, "inferred": []},
                "evidence": evidence,
                "confidence": {"confidence": "Low", "score": 0.0, "missing": ["language_policy"]},
            }
    out = {
        "ok": True,
        "title": title,
        "status": status,
        "findings": findings,
        "summary": " ".join(findings)[:1600],
        "explainability": {
            "observed": observed,
            "derived": derived,
            "inferred": inferred,
        },
        "evidence": evidence,
        "confidence": confidence,
    }
    out.update(extra)
    return out


def _val(snapshot: dict[str, Any], key: str) -> Any:
    row = snapshot.get(key) or {}
    return row.get("value")


def _dir(snapshot: dict[str, Any], key: str) -> Optional[str]:
    row = snapshot.get(key) or {}
    return row.get("direction")


def _fmt(v: Any) -> str:
    if v is None:
        return "n/a"
    try:
        return f"{float(v):.2f}"
    except Exception:
        return str(v)


def _domain_section(
    title: str,
    keys: list[str],
    bundle: dict[str, Any],
    *,
    narrative: str,
) -> dict[str, Any]:
    snap = bundle.get("snapshot") or {}
    observed = []
    findings = [narrative]
    hits = 0
    for key in keys:
        row = snap.get(key) or {}
        if row.get("value") is not None:
            hits += 1
            observed.append(f"{key}={_fmt(row.get('value'))} ({row.get('direction') or 'dir n/a'})")
            findings.append(
                f"{key}: {_fmt(row.get('value'))}"
                + (f", direction {row.get('direction')}" if row.get("direction") else "")
                + "."
            )
        elif row.get("status") == "waiting_series":
            findings.append(f"{key}: waiting on warehouse / CMKP series.")
    missing = [k for k in keys if (snap.get(k) or {}).get("value") is None]
    conf = section_confidence(
        required_hits=hits,
        required_total=max(len(keys), 1),
        observations=hits,
        missing=missing,
    )
    return _block(
        title,
        findings,
        observed=observed[:8],
        derived=[f"coverage={hits}/{len(keys)}"],
        inferred=["Domain reading uses warehouse + CMKP snapshot only; no vendor refresh at compose time."],
        evidence=[{"source": "macro_latest/cmkp", "keys": keys}],
        confidence=conf,
        series={k: snap.get(k) for k in keys},
    )


def executive(bundle: dict[str, Any]) -> dict[str, Any]:
    country = bundle.get("country") or "India"
    snap = bundle.get("snapshot") or {}
    regime_pack = _resolve_regime(bundle)
    regime = str(regime_pack.get("regime") or "Recovery")
    cycle = str(regime_pack.get("cycle") or "Early Cycle")
    impacts = sector_impacts(snap)
    pos = [i["sector"] for i in impacts if i["impact"] == "Positive"]
    neg = [i["sector"] for i in impacts if i["impact"] == "Negative"]
    inputs = bundle.get("inputs_present") or {}
    missing = [k for k, v in inputs.items() if not v]
    findings = [
        f"Macro environment for {country}: regime {regime}, cycle {cycle}.",
        f"Growth pulse: GDP {_fmt(_val(snap, 'gdp_growth'))}, PMI mfg {_fmt(_val(snap, 'pmi_manufacturing'))}.",
        f"Inflation / policy: CPI {_fmt(_val(snap, 'cpi'))}, repo {_fmt(_val(snap, 'repo_rate'))}.",
        f"Sectors with positive macro transmission: {', '.join(pos[:5]) or 'none clear'}.",
        f"Sectors facing pressure: {', '.join(neg[:5]) or 'none clear'}.",
        "This is contextual intelligence for research — not a market call.",
    ]
    if missing:
        findings.append(f"Monitoring gaps: {', '.join(missing[:5])}.")
    conf = section_confidence(
        required_hits=sum(1 for k in ("cmkp", "hmai_regime", "mfi_forecast") if inputs.get(k)),
        required_total=3,
        observations=int(bundle.get("observed_series_count") or 0),
        missing=missing,
    )
    return _block(
        "Executive Macro Summary",
        findings,
        observed=[
            f"cpi={_fmt(_val(snap, 'cpi'))}",
            f"repo={_fmt(_val(snap, 'repo_rate'))}",
            f"gdp={_fmt(_val(snap, 'gdp_growth'))}",
        ],
        derived=[f"regime={regime}", f"cycle={cycle}"],
        inferred=[
            "Sector tilts follow deterministic transmission rules from rates, inflation, oil, FX, growth, liquidity.",
        ],
        evidence=[{"source": "cmkp/hmai/mfi"}, {"source": "warehouse.macro_*"}],
        confidence=conf,
        regime=regime,
        cycle=cycle,
        sector_tilts={"positive": pos, "negative": neg},
    )


def dashboard(bundle: dict[str, Any]) -> dict[str, Any]:
    snap = bundle.get("snapshot") or {}
    regime_pack = _resolve_regime(bundle)
    cards = {
        "regime": str(regime_pack.get("regime") or ""),
        "cycle": str(regime_pack.get("cycle") or ""),
        "growth": {"gdp": _val(snap, "gdp_growth"), "pmi_mfg": _val(snap, "pmi_manufacturing"), "direction": _dir(snap, "gdp_growth")},
        "inflation": {"cpi": _val(snap, "cpi"), "wpi": _val(snap, "wpi"), "direction": _dir(snap, "cpi")},
        "liquidity": {"credit_growth": _val(snap, "credit_growth"), "banking_liquidity": _val(snap, "banking_liquidity")},
        "interest_rates": {"repo": _val(snap, "repo_rate"), "india_10y": _val(snap, "india_10y"), "fed_funds": _val(snap, "fed_funds")},
        "currency": {"usdinr": _val(snap, "usdinr"), "dxy": _val(snap, "dxy")},
        "commodities": {"brent": _val(snap, "brent"), "gold": _val(snap, "gold"), "copper": _val(snap, "copper")},
    }
    findings = [
        f"Current macro regime: {regime_pack['regime']} ({regime_pack['cycle']}).",
        f"Dashboard covers growth, inflation, liquidity, rates, currency, commodities.",
        f"Observed series with values: {bundle.get('observed_series_count')}/{bundle.get('catalogue_size')}.",
    ]
    conf = section_confidence(
        required_hits=int(bundle.get("observed_series_count") or 0),
        required_total=max(int(bundle.get("catalogue_size") or 1), 1),
        observations=int(bundle.get("observed_series_count") or 0),
    )
    return _block(
        "Macro Dashboard",
        findings,
        observed=[f"observed_series={bundle.get('observed_series_count')}"],
        derived=[f"regime={regime_pack['regime']}"],
        inferred=["Dashboard aggregates warehouse/CMKP snapshots; no UI calculations."],
        evidence=[{"source": "macro_latest"}],
        confidence=conf,
        cards=cards,
    )


def regime(bundle: dict[str, Any]) -> dict[str, Any]:
    pack = _resolve_regime(bundle)
    regime_name = str(pack.get("regime") or "Recovery")
    cycle_name = str(pack.get("cycle") or "Early Cycle")
    findings = [
        f"Macro regime classified as {regime_name}.",
        f"Economic cycle stage: {cycle_name}.",
        f"Classification basis: {pack.get('basis')}.",
    ]
    if pack.get("upstream_label"):
        findings.append(f"HMAI label available: {pack.get('upstream_label')}.")
    conf = section_confidence(
        required_hits=1 if regime_name else 0,
        required_total=1,
        observations=1 if (bundle.get("inputs_present") or {}).get("hmai_regime") else 0,
    )
    return _block(
        "Macro Regime",
        findings,
        observed=[f"hmai_label={pack.get('upstream_label')}", f"drivers={pack.get('drivers')}"],
        derived=[f"regime={regime_name}", f"cycle={cycle_name}"],
        inferred=["Regime is explainable state classification, not a GDP point forecast."],
        evidence=[{"source": "hmai.current_regime"}, {"source": "directional_rules"}],
        confidence=conf,
        regime=regime_name,
        cycle=cycle_name,
        drivers=pack.get("drivers"),
    )


def cycle(bundle: dict[str, Any]) -> dict[str, Any]:
    pack = _resolve_regime(bundle)
    cycle_name = str(pack.get("cycle") or "Early Cycle")
    findings = [
        f"Economic cycle: {cycle_name}.",
        "Cycle uses growth / inflation / rates directional transmission rules.",
        "Early/Mid/Late/Contraction/Recovery labels are research context, not trading signals.",
    ]
    conf = section_confidence(required_hits=1, required_total=1, observations=1)
    return _block(
        "Economic Cycle",
        findings,
        observed=[str(pack.get("drivers"))],
        derived=[f"cycle={cycle_name}"],
        inferred=["Cycle stage informs sector impact and forecast scenario weights."],
        evidence=[{"source": "classify_regime"}],
        confidence=conf,
        cycle=cycle_name,
    )


def economy(bundle: dict[str, Any]) -> dict[str, Any]:
    return _domain_section(
        "Economic Growth",
        ["gdp_growth", "gva_growth", "iip", "pmi_manufacturing", "pmi_services", "capacity_utilisation"],
        bundle,
        narrative="Growth block tracks GDP/GVA, industrial production, PMI and capacity utilisation.",
    )


def inflation(bundle: dict[str, Any]) -> dict[str, Any]:
    return _domain_section(
        "Inflation",
        ["cpi", "core_cpi", "wpi", "food_inflation", "fuel_inflation"],
        bundle,
        narrative="Inflation block tracks CPI/WPI and food/fuel components for margin and policy context.",
    )


def rates(bundle: dict[str, Any]) -> dict[str, Any]:
    return _domain_section(
        "Interest Rates",
        ["repo_rate", "reverse_repo", "fed_funds", "ecb_rate", "india_10y", "us_10y"],
        bundle,
        narrative="Rates block tracks RBI policy and global policy rates plus sovereign yields.",
    )


def liquidity(bundle: dict[str, Any]) -> dict[str, Any]:
    return _domain_section(
        "Liquidity",
        ["banking_liquidity", "money_supply", "credit_growth", "deposit_growth"],
        bundle,
        narrative="Liquidity block tracks banking liquidity, money supply, credit and deposit growth.",
    )


def currency(bundle: dict[str, Any]) -> dict[str, Any]:
    return _domain_section(
        "Currency",
        ["usdinr", "dxy", "reer"],
        bundle,
        narrative="Currency block tracks USDINR, DXY and REER for export/import transmission.",
    )


def commodities(bundle: dict[str, Any]) -> dict[str, Any]:
    return _domain_section(
        "Commodities",
        ["brent", "wti", "gold", "copper"],
        bundle,
        narrative="Commodities block tracks oil, metals and gold as cost and inflation transmitters.",
    )


def bonds(bundle: dict[str, Any]) -> dict[str, Any]:
    return _domain_section(
        "Bond Market",
        ["india_10y", "us_10y"],
        bundle,
        narrative="Bond block tracks sovereign yields as duration and financials transmission channels.",
    )


def fiscal(bundle: dict[str, Any]) -> dict[str, Any]:
    return _domain_section(
        "Fiscal",
        ["fiscal_deficit", "tax_collection"],
        bundle,
        narrative="Fiscal block tracks deficit and tax collection as policy and growth context.",
    )


def external(bundle: dict[str, Any]) -> dict[str, Any]:
    return _domain_section(
        "External Sector",
        ["trade_balance", "current_account", "fx_reserves"],
        bundle,
        narrative="External block tracks trade balance, current account and FX reserves.",
    )


def sector_impact(bundle: dict[str, Any]) -> dict[str, Any]:
    impacts = sector_impacts(bundle.get("snapshot") or {})
    findings = [
        "Sector impact uses deterministic transmission from rates, inflation, oil, FX, growth and liquidity.",
    ]
    for row in impacts:
        findings.append(f"{row['sector']}: {row['impact']} (evidence: {', '.join(row['evidence'][:3]) or 'neutral drivers'}).")
    conf = section_confidence(required_hits=len(SECTORS), required_total=len(SECTORS), observations=len(impacts))
    return _block(
        "Sector Impact",
        findings,
        observed=[f"sectors={len(impacts)}"],
        derived=[f"{r['sector']}={r['impact']}" for r in impacts[:6]],
        inferred=["Impacts are contextual research tilts, not portfolio instructions."],
        evidence=[{"source": "sector_transmission_rules"}],
        confidence=conf,
        impacts=impacts,
    )


def industry_impact(bundle: dict[str, Any]) -> dict[str, Any]:
    impacts = industry_impacts(bundle.get("snapshot") or {})
    findings = ["Industry impact inherits mapped sector transmission with industry labels."]
    for row in impacts[:12]:
        findings.append(f"{row['industry']} ({row['sector']}): {row['impact']}.")
    conf = section_confidence(required_hits=min(len(impacts), 10), required_total=10, observations=len(impacts))
    return _block(
        "Industry Impact",
        findings,
        observed=[f"industries={len(impacts)}"],
        derived=[f"{r['industry']}={r['impact']}" for r in impacts[:6]],
        inferred=["Industry mapping is deterministic from AGIB sector taxonomy."],
        evidence=[{"source": "industry_sector_map"}],
        confidence=conf,
        impacts=impacts,
    )


def company_exposure(bundle: dict[str, Any], *, company: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    company = company or {}
    sector = company.get("sector")
    industry = company.get("industry")
    symbol = company.get("symbol") or "universe"
    sens = company_sensitivity(sector, industry)
    findings = [
        f"Company exposure for {symbol}: sector mapped to {sens['sector']}.",
        f"Interest-rate sensitivity: {sens['interest_rate_sensitivity']}.",
        f"Oil sensitivity: {sens['oil_sensitivity']}; FX sensitivity: {sens['fx_sensitivity']}.",
        f"Commodity sensitivity: {sens['commodity_sensitivity']}; credit: {sens['credit_sensitivity']}.",
        f"Consumer demand sensitivity: {sens['consumer_demand_sensitivity']}.",
    ]
    conf = section_confidence(
        required_hits=1 if sector or industry else 0,
        required_total=1,
        observations=1 if sector else 0,
        missing=[] if sector else ["sector"],
    )
    return _block(
        "Company Exposure",
        findings,
        observed=[f"sector={sector}", f"industry={industry}"],
        derived=[str(sens)],
        inferred=["Sensitivities are structural exposure labels for research monitoring."],
        evidence=[{"source": "company_master"}, {"source": "sensitivity_map"}],
        confidence=conf,
        exposures=sens,
        symbol=symbol,
    )


def attribution(bundle: dict[str, Any]) -> dict[str, Any]:
    events = (bundle.get("warehouse") or {}).get("macro_events") or []
    pack = _resolve_regime(bundle)
    regime_name = str(pack.get("regime") or "Recovery")
    findings = [
        f"Macro change attribution for regime {regime_name}.",
        f"Observed drivers: {pack.get('drivers')}.",
    ]
    if events:
        findings.append(f"Recent macro events in warehouse: {len(events)}.")
        for ev in events[:3]:
            findings.append(f"Event: {ev.get('title') or ev.get('event') or ev.get('name')}.")
    else:
        findings.append("No recent macro_events rows — attribution relies on directional series.")
    conf = section_confidence(
        required_hits=1,
        required_total=1,
        observations=len(events),
    )
    return _block(
        "Macro Attribution",
        findings,
        observed=[f"events={len(events)}", f"drivers={pack.get('drivers')}"],
        derived=[f"regime={regime_name}"],
        inferred=["Attribution separates observed series moves from derived regime labels."],
        evidence=[{"source": "macro_events"}, {"source": "snapshot_directions"}],
        confidence=conf,
    )


def forecast(bundle: dict[str, Any]) -> dict[str, Any]:
    mfi = bundle.get("mfi_forecast") or {}
    pack = _resolve_regime(bundle)
    drivers = pack.get("drivers") or {}
    regime_name = str(pack.get("regime") or "Recovery")
    findings = [
        "Macro forecast is scenario-directional (not point GDP prediction).",
        f"Current regime context: {regime_name}.",
        "Directions covered: growth, inflation, rates, liquidity, currency, commodities.",
    ]
    if mfi and mfi.get("ok") is not False and not mfi.get("error"):
        findings.append("Upstream MFI forecast pack consumed for scenario scaffolding.")
        summary = mfi.get("summary") or mfi.get("executive_summary")
        if summary:
            findings.append(str(summary)[:280])
    else:
        findings.append("MFI forecast unavailable — using regime-conditioned directional outlook.")
    directions = {
        "gdp": "stable_to_improving" if drivers.get("growth_up") else "softening",
        "inflation": "elevated" if drivers.get("inflation_up") else "easing",
        "rates": "restrictive" if drivers.get("rates_up") else "accommodative_bias",
        "liquidity": "tight" if drivers.get("liquidity_tight") else "adequate",
        "currency": "usd_firm" if drivers.get("usd_up") else "mixed",
        "commodities": "oil_firm" if drivers.get("oil_up") else "mixed",
    }
    conf = section_confidence(
        required_hits=1 if (bundle.get("inputs_present") or {}).get("mfi_forecast") else 0,
        required_total=1,
        observations=int(bundle.get("observed_series_count") or 0),
        missing=[] if (bundle.get("inputs_present") or {}).get("mfi_forecast") else ["mfi_forecast"],
    )
    return _block(
        "Macro Forecast",
        findings,
        observed=[f"regime={regime_name}"],
        derived=[str(directions)],
        inferred=["Forecasts are directional scenarios for research adjustment, not point estimates."],
        evidence=[{"source": "mfi.forecast"}, {"source": "regime_rules"}],
        confidence=conf,
        directions=directions,
    )


def scenarios(bundle: dict[str, Any]) -> dict[str, Any]:
    pack = _resolve_regime(bundle)
    mfi_sc = bundle.get("mfi_scenarios") or {}
    inputs = bundle.get("inputs_present") or {}
    conf_score = 0.65 if inputs.get("mfi_scenarios") else 0.45
    regime_name = str(pack.get("regime") or "Recovery")
    probs = scenario_probabilities(regime_name, conf_score)
    scen = {
        "bull": {
            "economy": "Growth reaccelerates with disinflation",
            "rates": "Policy easing path becomes credible",
            "inflation": "CPI moves toward comfort zone",
            "growth": "PMI expansion sustained",
            "liquidity": "Credit growth supports demand",
        },
        "base": {
            "economy": "Soft-landing / muddle-through",
            "rates": "Policy stays data-dependent",
            "inflation": "Sticky but manageable",
            "growth": "Moderate expansion",
            "liquidity": "Adequate system liquidity",
        },
        "bear": {
            "economy": "Growth slows with persistent inflation or external shock",
            "rates": "Higher-for-longer policy",
            "inflation": "Reacceleration risk",
            "growth": "PMI contraction risk",
            "liquidity": "Tightening / credit stress",
        },
    }
    if mfi_sc and isinstance(mfi_sc.get("scenarios"), dict):
        findings_extra = "Upstream MFI scenarios merged as evidence."
    else:
        findings_extra = "Scenarios synthesized from regime rules when MFI scenarios are thin."
    findings = [
        f"Bull/Base/Bear probabilities: {probs['bull']}/{probs['base']}/{probs['bear']} (sum 100).",
        findings_extra,
        "Scenarios cover economy, rates, inflation, growth and liquidity — no security recommendations.",
    ]
    conf = section_confidence(
        required_hits=1,
        required_total=1,
        observations=1 if inputs.get("mfi_scenarios") else 0,
    )
    return _block(
        "Macro Scenarios",
        findings,
        observed=[f"regime={regime_name}"],
        derived=[f"probabilities={probs}"],
        inferred=["Probabilities are confidence-weighted and always normalized to 100%."],
        evidence=[{"source": "mfi.scenarios"}, {"source": "scenario_probabilities"}],
        confidence=conf,
        probabilities=probs,
        scenarios=scen,
    )


def risks(bundle: dict[str, Any]) -> dict[str, Any]:
    drivers = (_resolve_regime(bundle).get("drivers") or {})
    risk_rows = [
        {"risk": "Inflation Risk", "level": "High" if drivers.get("inflation_up") else "Medium"},
        {"risk": "Policy Risk", "level": "High" if drivers.get("rates_up") else "Medium"},
        {"risk": "Commodity Risk", "level": "High" if drivers.get("oil_up") else "Medium"},
        {"risk": "FX Risk", "level": "High" if drivers.get("usd_up") else "Medium"},
        {"risk": "Liquidity Risk", "level": "High" if drivers.get("liquidity_tight") else "Low"},
        {"risk": "Credit Risk", "level": "Medium"},
        {"risk": "Fiscal Risk", "level": "Medium"},
        {"risk": "Geopolitical Risk", "level": "Medium"},
    ]
    findings = ["Macro risk monitor (contextual, not a trading book):"]
    findings.extend([f"{r['risk']}: {r['level']}." for r in risk_rows])
    conf = section_confidence(required_hits=len(risk_rows), required_total=len(risk_rows), observations=len(risk_rows))
    return _block(
        "Macro Risks",
        findings,
        observed=[str(drivers)],
        derived=[f"{r['risk']}={r['level']}" for r in risk_rows[:4]],
        inferred=["Risk levels are research monitoring flags for RIE/FIE/Portfolio Office."],
        evidence=[{"source": "driver_rules"}],
        confidence=conf,
        risks=risk_rows,
    )


def relationships(bundle: dict[str, Any]) -> dict[str, Any]:
    mri = bundle.get("mri") or {}
    rel_rows = (bundle.get("warehouse") or {}).get("macro_relationships") or []
    built_ins = [
        {"pair": "GDP vs Earnings", "strength": "Medium", "confidence": "Medium", "observations": None},
        {"pair": "Rates vs PE", "strength": "High", "confidence": "Medium", "observations": None},
        {"pair": "Inflation vs Margins", "strength": "High", "confidence": "Medium", "observations": None},
        {"pair": "Oil vs Chemicals", "strength": "High", "confidence": "Medium", "observations": None},
        {"pair": "FX vs IT", "strength": "High", "confidence": "Medium", "observations": None},
        {"pair": "Yield vs Banks", "strength": "High", "confidence": "Medium", "observations": None},
        {"pair": "Commodity vs Metals", "strength": "High", "confidence": "Medium", "observations": None},
    ]
    findings = [
        "Relationship engine exposes macro→market transmission pairs with strength and confidence.",
    ]
    if rel_rows:
        findings.append(f"Warehouse macro_relationships rows: {len(rel_rows)}.")
    if mri and mri.get("ok") is not False and not mri.get("error"):
        findings.append("Upstream MRI dashboard consumed when available.")
    findings.extend([f"{r['pair']}: strength {r['strength']}." for r in built_ins])
    conf = section_confidence(
        required_hits=1 if (rel_rows or (mri and not mri.get("error"))) else 0,
        required_total=1,
        observations=len(rel_rows),
        missing=[] if rel_rows or mri else ["macro_relationships"],
    )
    return _block(
        "Macro Relationships",
        findings,
        observed=[f"warehouse_rels={len(rel_rows)}"],
        derived=[r["pair"] for r in built_ins[:4]],
        inferred=["Pairs are institutional research priors pending denser MRI observation counts."],
        evidence=[{"source": "mri"}, {"source": "macro_relationships"}],
        confidence=conf,
        relationships=built_ins,
    )


def confidence_module(bundle: dict[str, Any], quality: dict[str, Any]) -> dict[str, Any]:
    findings = [
        f"Macro confidence: {quality.get('macro_confidence')} (score {quality.get('score')}).",
        f"Input coverage: {quality.get('coverage_pct')}%.",
        f"Observed series: {bundle.get('observed_series_count')}/{bundle.get('catalogue_size')}.",
        "Confidence reflects freshness proxies, coverage, and upstream engine availability — not forecast accuracy claims.",
    ]
    return _block(
        "Macro Confidence",
        findings,
        observed=[f"coverage_pct={quality.get('coverage_pct')}"],
        derived=[f"macro_confidence={quality.get('macro_confidence')}"],
        inferred=["Low confidence means research should emphasize monitoring gaps."],
        evidence=[{"source": "pack_quality"}],
        confidence={
            "confidence": quality.get("macro_confidence") or "Low",
            "score": quality.get("score") or 0,
        },
        quality=quality,
    )


MODULE_BUILDERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "executive": executive,
    "dashboard": dashboard,
    "regime": regime,
    "cycle": cycle,
    "economy": economy,
    "inflation": inflation,
    "rates": rates,
    "liquidity": liquidity,
    "currency": currency,
    "commodities": commodities,
    "bonds": bonds,
    "fiscal": fiscal,
    "external": external,
    "sector_impact": sector_impact,
    "industry_impact": industry_impact,
    "company_exposure": company_exposure,
    "attribution": attribution,
    "forecast": forecast,
    "scenarios": scenarios,
    "risks": risks,
    "relationships": relationships,
}
