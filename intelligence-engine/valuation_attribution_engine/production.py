"""VARIE production surface — explain why valuation is where it is.

Composes Warehouse → UVE attribution → HVIE → VPAE context → Market Intelligence.
No vendor calls. No recommendation language. No invented causes.
"""

from __future__ import annotations

from typing import Any, Optional

from historical_valuation_intelligence.statistics import regime_from_percentile
from valuation_attribution_engine.evidence import (
    ENGINE_CODE,
    MATERIAL_PCT,
    VERSION,
    annual_pair,
    confidence_score,
    daily_attribution,
    decompose_premium,
    factor,
    industry_members,
    load_flows,
    load_hvie,
    load_hvie_history,
    load_hvie_rerating,
    load_universe_row,
    load_warehouse_company,
    now,
    num,
    ownership_pair,
    pct_change,
    research_timeline_rows,
    sector_members,
)


def health() -> dict[str, Any]:
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "role": "valuation_attribution_research_intelligence",
        "rule": "no_invented_causes_no_buy_sell_no_ui_calculations",
        "reads": [
            "institutional_warehouse",
            "valuation_engine.attribution",
            "historical_valuation_intelligence",
            "market_intelligence_engine.universe",
            "market_intelligence_engine.flows",
            "valuation_terminal.sector_lens / VPAE context via MI",
        ],
        "endpoints": [
            "/v1/valuation/attribution/company/{symbol}",
            "/v1/valuation/attribution/sector/{sector}",
            "/v1/valuation/attribution/industry/{industry}",
            "/v1/valuation/attribution/market",
            "/v1/valuation/attribution/peer/{symbol}",
            "/v1/valuation/attribution/history/{symbol}",
            "/v1/valuation/attribution/timeline/{symbol}",
            "/v1/valuation/attribution/opportunities",
            "/v1/valuation/attribution/leaders",
        ],
        "language": "analysis_only",
        "checked_at": now(),
    }


def _collect_company_factors(
    row: dict[str, Any],
    wh: dict[str, Any],
    hvie: dict[str, Any],
    rerating: dict[str, Any],
    flows: dict[str, Any],
) -> list[dict[str, Any]]:
    factors: list[dict[str, Any]] = []
    premium = num(hvie.get("premium_to_median_pct"))
    if premium is None:
        premium = num(row.get("sector_premium_pct"))

    # 1) ROE — annual pair when available
    latest_a, prior_a = annual_pair(wh)
    roe_now = num((latest_a or {}).get("roe")) or num(row.get("roe"))
    roe_prev = num((prior_a or {}).get("roe"))
    roe_chg = pct_change(roe_prev, roe_now) if roe_prev is not None else None
    if roe_now is not None and roe_chg is not None and abs(roe_chg) >= MATERIAL_PCT:
        factors.append(factor(
            key="roe",
            label="ROE",
            direction="supporting_premium" if roe_chg > 0 else "supporting_discount",
            statement=(
                f"ROE {'improved' if roe_chg > 0 else 'declined'} "
                f"{abs(roe_chg):.1f}% ({roe_prev} → {roe_now})."
            ),
            evidence_kind="observed",
            strength=min(1.0, abs(roe_chg) / 20.0),
            current=roe_now,
            previous=roe_prev,
            change_pct=roe_chg,
            source="warehouse.financials_annual",
        ))
    elif roe_now is not None and roe_now >= 18:
        factors.append(factor(
            key="roe",
            label="ROE",
            direction="supporting_premium",
            statement=f"Current ROE is elevated at {roe_now}%.",
            evidence_kind="observed",
            strength=0.35,
            current=roe_now,
            source="warehouse / market_intelligence universe",
        ))

    # 2) Operating margin
    om_now = num((latest_a or {}).get("operating_margin"))
    om_prev = num((prior_a or {}).get("operating_margin"))
    om_chg = pct_change(om_prev, om_now) if om_prev is not None else None
    if om_now is not None and om_chg is not None and abs(om_chg) >= MATERIAL_PCT:
        factors.append(factor(
            key="operating_margin",
            label="Operating margin",
            direction="supporting_premium" if om_chg > 0 else "supporting_discount",
            statement=(
                f"Operating margin {'expanded' if om_chg > 0 else 'compressed'} "
                f"{abs(om_chg):.1f}% ({om_prev} → {om_now})."
            ),
            evidence_kind="observed",
            strength=min(1.0, abs(om_chg) / 25.0),
            current=om_now,
            previous=om_prev,
            change_pct=om_chg,
            source="warehouse.financials_annual",
        ))

    # 3) Institutional ownership
    own_now, own_prev = ownership_pair(wh)
    inst_now = num((own_now or {}).get("institutional_holding") or (own_now or {}).get("fii"))
    inst_prev = num((own_prev or {}).get("institutional_holding") or (own_prev or {}).get("fii"))
    inst_chg = None
    if inst_now is not None and inst_prev is not None:
        inst_chg = round(inst_now - inst_prev, 2)  # percentage-point change
    if inst_now is not None and inst_chg is not None and abs(inst_chg) >= 0.5:
        factors.append(factor(
            key="institutional_ownership",
            label="Institutional ownership",
            direction="supporting_premium" if inst_chg > 0 else "supporting_discount",
            statement=(
                f"Institutional ownership {'increased' if inst_chg > 0 else 'decreased'} "
                f"{abs(inst_chg):.1f} pp ({inst_prev}% → {inst_now}%)."
            ),
            evidence_kind="observed",
            strength=min(1.0, abs(inst_chg) / 5.0),
            current=inst_now,
            previous=inst_prev,
            change_pct=inst_chg,
            source="warehouse.ownership",
        ))

    # 4) Multiple move (universe PE change)
    pe_chg = num(row.get("pe_change_pct"))
    if pe_chg is not None and abs(pe_chg) >= MATERIAL_PCT:
        factors.append(factor(
            key="multiple_move",
            label="Multiple move",
            direction="supporting_premium" if pe_chg > 0 else "supporting_discount",
            statement=f"P/E {'expanded' if pe_chg > 0 else 'compressed'} {abs(pe_chg):.1f}% vs prior observation.",
            evidence_kind="observed",
            strength=min(1.0, abs(pe_chg) / 15.0),
            current=row.get("pe"),
            previous=row.get("prev_pe"),
            change_pct=pe_chg,
            source="market_intelligence_engine.universe",
        ))

    # 5) HVIE re-rating / de-rating
    if rerating.get("ok") and rerating.get("kind") in {"expansion", "compression"}:
        chg = num(rerating.get("change_pct")) or 0
        factors.append(factor(
            key="historical_rerating",
            label="Historical multiple path",
            direction="supporting_premium" if rerating["kind"] == "expansion" else "supporting_discount",
            statement=rerating.get("sentence") or f"HVIE reports {rerating['kind']} of {chg:+.1f}%.",
            evidence_kind="derived",
            strength=min(1.0, abs(chg) / 40.0),
            current=rerating.get("late_median"),
            previous=rerating.get("early_median"),
            change_pct=chg,
            source="historical_valuation_intelligence.rerating",
        ))

    # 6) Sector premium context
    sector_prem = num(row.get("sector_premium_pct"))
    if sector_prem is not None and abs(sector_prem) >= 5:
        factors.append(factor(
            key="sector_relative",
            label="Sector relative premium",
            direction="supporting_premium" if sector_prem > 0 else "supporting_discount",
            statement=(
                f"Trades at a {abs(sector_prem):.1f}% "
                f"{'premium' if sector_prem > 0 else 'discount'} to the sector benchmark."
            ),
            evidence_kind="observed",
            strength=min(1.0, abs(sector_prem) / 40.0),
            current=row.get("primary_value") or row.get("pe"),
            previous=row.get("sector_median_pe") or row.get("sector_median_pb"),
            change_pct=sector_prem,
            source="warehouse provider ratios / MI universe",
        ))

    # 7) Market FII/DII flows (market-level inferred support)
    if flows.get("available") and flows.get("net_institutional_flow") is not None:
        net = num(flows.get("net_institutional_flow")) or 0
        if abs(net) > 0:
            factors.append(factor(
                key="market_institutional_flows",
                label="Market institutional flows",
                direction="supporting_premium" if net > 0 else "supporting_discount",
                statement=(
                    f"Latest market FII/DII combined net flow is "
                    f"{'positive' if net > 0 else 'negative'} ({net})."
                ),
                evidence_kind="inferred",
                strength=0.2,
                current=net,
                source="warehouse.institutional_flow",
            ))

    # 8) Historical percentile context
    pct = num(hvie.get("historical_percentile")) or num(row.get("percentile"))
    if pct is not None:
        if pct >= 70:
            factors.append(factor(
                key="historical_percentile",
                label="Historical percentile",
                direction="supporting_premium",
                statement=f"Historical percentile is elevated at {pct:.0f}.",
                evidence_kind="observed",
                strength=min(1.0, (pct - 50) / 50.0),
                current=pct,
                source="HVIE / warehouse historical_valuation",
            ))
        elif pct <= 30:
            factors.append(factor(
                key="historical_percentile",
                label="Historical percentile",
                direction="supporting_discount",
                statement=f"Historical percentile is compressed at {pct:.0f}.",
                evidence_kind="observed",
                strength=min(1.0, (50 - pct) / 50.0),
                current=pct,
                source="HVIE / warehouse historical_valuation",
            ))

    return sorted(factors, key=lambda f: -float(f.get("strength") or 0))


def _research_note(symbol: str, factors: list[dict[str, Any]], premium: Optional[float], confidence: int) -> dict[str, Any]:
    if not factors:
        return {
            "title": "Valuation attribution",
            "body": "Primary driver cannot be determined from available data.",
            "confidence": confidence,
            "language": "analysis_only",
        }
    top = factors[0]
    side = "expanded" if (premium or 0) >= 0 else "compressed"
    body = (
        f"Valuation {side} with the strongest observed evidence being "
        f"{top['label'].lower()}: {top['statement']}"
    )
    if len(factors) > 1:
        body += f" Supporting evidence includes {factors[1]['label'].lower()}."
    return {
        "title": f"{symbol} valuation research note",
        "body": body,
        "confidence": confidence,
        "language": "analysis_only",
        "export": {
            "markdown": (
                f"# {symbol} Valuation Attribution\n\n"
                f"{body}\n\n"
                f"**Confidence:** {confidence}%\n\n"
                f"_Analysis only — not a recommendation._\n"
            ),
            "summary": body,
        },
    }


def _risk_panel(premium: Optional[float], factors: list[dict[str, Any]]) -> dict[str, Any]:
    if premium is None:
        return {
            "supported": None,
            "statement": "Premium/discount not available to assess support.",
            "risks": [],
        }
    supporting = [f for f in factors if f.get("direction") == ("supporting_premium" if premium >= 0 else "supporting_discount")]
    observed = [f for f in supporting if f.get("evidence_kind") == "observed"]
    supported = bool(observed) and abs(premium) >= 5
    risks = []
    if premium >= 10:
        risks = [
            "Valuation depends on continued ROE durability" if any(f["key"] == "roe" for f in factors) else "Premium may depend on earnings durability",
            "Margin trajectory must remain supportive" if any(f["key"] == "operating_margin" for f in factors) else "Multiple may compress if growth slows",
            "Sector re-rating can reverse without company-specific deterioration",
        ]
    elif premium <= -10:
        risks = [
            "Discount may reflect unresolved earnings or quality concerns",
            "Re-rating requires observable improvement in fundamentals or ownership",
        ]
    return {
        "supported": supported,
        "statement": (
            "Current premium is supported by observed warehouse evidence."
            if supported and premium >= 0 else
            "Current discount is associated with observed warehouse evidence."
            if supported else
            "Support for the current premium/discount is limited in available data."
        ),
        "risks": risks,
        "language": "analysis_only",
    }


def company(symbol: str, *, window: str = "10y", universe_limit: int = 5000) -> dict[str, Any]:
    ticker = str(symbol or "").strip().upper()
    if not ticker:
        return {"ok": False, "error": "symbol_required", "engine": ENGINE_CODE}

    row = load_universe_row(ticker, universe_limit=universe_limit) or {}
    wh = load_warehouse_company(ticker)
    metric = row.get("primary_metric") or "pe"
    hvie = load_hvie(ticker, metric=metric if metric in {"pe", "pb", "ev_ebitda"} else "pe", window=window)
    rerating = load_hvie_rerating(ticker, metric=hvie.get("metric") or "pe", window="max")
    flows = load_flows()

    factors = _collect_company_factors(row, wh if wh.get("ok") else {}, hvie, rerating, flows)
    premium = num(hvie.get("premium_to_median_pct"))
    if premium is None:
        premium = num(row.get("sector_premium_pct"))
    pct = num(hvie.get("historical_percentile")) or num(row.get("percentile"))
    current = num(hvie.get("current")) or num(row.get("primary_value")) or num(row.get("pe"))
    hist_median = num(hvie.get("median"))
    confidence = confidence_score(
        factors,
        hvie_ok=bool(hvie.get("ok")),
        coverage=int(row.get("provider_coverage") or 0),
    )
    premium_breakdown = decompose_premium(premium, factors)
    daily = daily_attribution(row, wh if wh.get("ok") else {})
    note = _research_note(ticker, factors, premium, confidence)
    risk = _risk_panel(premium, factors)
    largest = factors[0] if factors else None

    why = [f["statement"] for f in factors[:8]]
    if not why:
        why = ["Primary driver cannot be determined from available data."]

    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "symbol": ticker,
        "company_name": row.get("company_name") or (wh.get("master") or {}).get("company_name"),
        "sector": row.get("sector") or (wh.get("master") or {}).get("sector"),
        "industry": row.get("industry") or (wh.get("master") or {}).get("industry"),
        "as_of": (row.get("_universe_meta") or {}).get("valuation_date") or hvie.get("statistics", {}).get("stats", {}).get("last"),
        "metric": hvie.get("metric") or metric,
        "window": window,
        "snapshot": {
            "current": current,
            "historical_median": hist_median,
            "premium_pct": premium,
            "historical_percentile": pct,
            "regime": hvie.get("regime") or regime_from_percentile(pct).get("regime"),
            "valuation_status": None,
        },
        "why": why,
        "factors": factors,
        "largest_contributor": {
            "key": largest["key"],
            "label": largest["label"],
            "statement": largest["statement"],
            "evidence_kind": largest["evidence_kind"],
            "source": largest["source"],
        } if largest else None,
        "premium_attribution": premium_breakdown,
        "discount_attribution": premium_breakdown if (premium or 0) < 0 else [],
        "daily_change": daily,
        "rerating": rerating if rerating.get("ok") else None,
        "opportunity": {
            "label": (
                "Historically Cheap" if pct is not None and pct <= 30 else
                "Historically Expensive" if pct is not None and pct >= 70 else
                "Fair / Mid-range" if pct is not None else "Unknown"
            ),
            "reason": why[:4],
            "note": "Research context only — not a recommendation.",
        },
        "risk": risk,
        "research_note": note,
        "confidence": confidence,
        "provenance": {
            "universe": "market_intelligence_engine.universe",
            "warehouse": "institutional_warehouse.read_company",
            "hvie": "historical_valuation_intelligence",
            "uve_attribution": "valuation_engine.attribution",
            "flows": "warehouse.institutional_flow",
        },
        "language": "analysis_only",
        "checked_at": now(),
    }


def sector(sector_name: str, *, universe_limit: int = 5000) -> dict[str, Any]:
    pack = sector_members(sector_name, universe_limit=universe_limit)
    members = pack.get("members") or []
    if not members:
        return {"ok": False, "error": "sector_not_found", "sector": sector_name, "engine": ENGINE_CODE}
    valuation = pack.get("valuation") or {}
    name = pack["sector"]
    median_pe = num(valuation.get("median_pe") or valuation.get("current"))
    median_pb = num(valuation.get("median_pb"))
    hist = num(valuation.get("historical_median") or valuation.get("sector_benchmark"))
    premium = num(valuation.get("premium_pct"))
    if premium is None and median_pe is not None and hist:
        premium = round(100.0 * (median_pe - hist) / abs(hist), 1)
    pct = num(valuation.get("historical_percentile"))

    # Aggregate member evidence
    pe_chgs = [num(m.get("pe_change_pct")) for m in members if num(m.get("pe_change_pct")) is not None]
    avg_pe_chg = round(sum(pe_chgs) / len(pe_chgs), 2) if pe_chgs else None
    roes = [num(m.get("roe")) for m in members if num(m.get("roe")) is not None]
    median_roe = sorted(roes)[len(roes) // 2] if roes else None

    factors = []
    if median_roe is not None:
        factors.append(factor(
            key="sector_roe",
            label="Sector ROE",
            direction="supporting_premium" if median_roe >= 15 else "neutral",
            statement=f"Median ROE across covered names is {median_roe:.1f}%.",
            evidence_kind="observed",
            strength=0.55 if median_roe >= 15 else 0.25,
            current=median_roe,
            source="market_intelligence_engine.universe",
        ))
    if avg_pe_chg is not None and abs(avg_pe_chg) >= MATERIAL_PCT:
        factors.append(factor(
            key="sector_multiple_move",
            label="Sector multiple move",
            direction="supporting_premium" if avg_pe_chg > 0 else "supporting_discount",
            statement=f"Average P/E change across members is {avg_pe_chg:+.1f}%.",
            evidence_kind="observed",
            strength=min(1.0, abs(avg_pe_chg) / 12.0),
            change_pct=avg_pe_chg,
            source="market_intelligence_engine.universe",
        ))
    if premium is not None and abs(premium) >= 5:
        factors.append(factor(
            key="sector_premium",
            label="Sector premium vs benchmark",
            direction="supporting_premium" if premium > 0 else "supporting_discount",
            statement=f"Sector sits at a {abs(premium):.1f}% {'premium' if premium > 0 else 'discount'} to its benchmark.",
            evidence_kind="observed",
            strength=min(1.0, abs(premium) / 35.0),
            change_pct=premium,
            source="market_intelligence_engine.aggregation",
        ))
    if pct is not None:
        factors.append(factor(
            key="historical_percentile",
            label="Historical percentile",
            direction="supporting_premium" if pct >= 60 else "supporting_discount" if pct <= 40 else "neutral",
            statement=f"Median company historical percentile is {pct:.0f}.",
            evidence_kind="observed",
            strength=0.4,
            current=pct,
            source="HVIE / warehouse percentiles via MI",
        ))

    factors = sorted(factors, key=lambda f: -float(f.get("strength") or 0))
    confidence = confidence_score(factors, hvie_ok=pct is not None, coverage=len(members))
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "sector": name,
        "companies": len(members),
        "as_of": pack.get("as_of"),
        "snapshot": {
            "current_pb": median_pb,
            "current_pe": median_pe,
            "historical_pb_or_bench": hist,
            "premium_pct": premium,
            "historical_percentile": pct,
            "median_roe": median_roe,
        },
        "why": [f["statement"] for f in factors] or ["Primary driver cannot be determined from available data."],
        "factors": factors,
        "premium_attribution": decompose_premium(premium, factors),
        "largest_contributor": factors[0] if factors else None,
        "confidence": confidence,
        "comparison_note": "Sector attribution uses warehouse-backed medians only.",
        "language": "analysis_only",
        "checked_at": now(),
    }


def industry(industry_name: str, *, universe_limit: int = 5000) -> dict[str, Any]:
    pack = industry_members(industry_name, universe_limit=universe_limit)
    if not pack.get("ok"):
        return {"ok": False, "error": pack.get("error") or "industry_not_found", "industry": industry_name}
    members = pack["members"]
    name = pack["industry"]
    pes = [num(m.get("pe")) for m in members if num(m.get("pe")) is not None]
    pbs = [num(m.get("pb")) for m in members if num(m.get("pb")) is not None]
    roes = [num(m.get("roe")) for m in members if num(m.get("roe")) is not None]
    pcts = [num(m.get("percentile")) for m in members if num(m.get("percentile")) is not None]
    premiums = [num(m.get("sector_premium_pct")) for m in members if num(m.get("sector_premium_pct")) is not None]

    def _med(vals: list[float]) -> Optional[float]:
        return round(sorted(vals)[len(vals) // 2], 2) if vals else None

    median_pe = _med(pes)
    median_pb = _med(pbs)
    median_roe = _med(roes)
    median_pct = _med(pcts)
    premium = _med(premiums)
    pe_chgs = [num(m.get("pe_change_pct")) for m in members if num(m.get("pe_change_pct")) is not None]
    avg_pe_chg = round(sum(pe_chgs) / len(pe_chgs), 2) if pe_chgs else None

    factors = []
    if median_roe is not None:
        factors.append(factor(
            key="industry_roe",
            label="Industry ROE",
            direction="supporting_premium" if median_roe >= 15 else "neutral",
            statement=f"Industry median ROE is {median_roe:.1f}%.",
            evidence_kind="observed",
            strength=0.5,
            current=median_roe,
            source="market_intelligence_engine.universe",
        ))
    if avg_pe_chg is not None and abs(avg_pe_chg) >= MATERIAL_PCT:
        factors.append(factor(
            key="industry_rerating",
            label="Industry re-rating",
            direction="supporting_premium" if avg_pe_chg > 0 else "supporting_discount",
            statement=f"Average industry P/E change is {avg_pe_chg:+.1f}%.",
            evidence_kind="observed",
            strength=min(1.0, abs(avg_pe_chg) / 12.0),
            change_pct=avg_pe_chg,
            source="market_intelligence_engine.universe",
        ))
    if premium is not None:
        factors.append(factor(
            key="industry_premium",
            label="Industry premium vs sector",
            direction="supporting_premium" if premium > 0 else "supporting_discount",
            statement=f"Median sector-relative premium is {premium:+.1f}%.",
            evidence_kind="observed",
            strength=min(1.0, abs(premium) / 30.0),
            change_pct=premium,
            source="market_intelligence_engine.universe",
        ))
    factors = sorted(factors, key=lambda f: -float(f.get("strength") or 0))
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "industry": name,
        "sector": pack.get("sector"),
        "companies": len(members),
        "as_of": pack.get("as_of"),
        "snapshot": {
            "median_pe": median_pe,
            "median_pb": median_pb,
            "median_roe": median_roe,
            "premium_pct": premium,
            "historical_percentile": median_pct,
        },
        "why": [f["statement"] for f in factors] or ["Primary driver cannot be determined from available data."],
        "factors": factors,
        "premium_attribution": decompose_premium(premium, factors),
        "confidence": confidence_score(factors, hvie_ok=median_pct is not None, coverage=len(members)),
        "language": "analysis_only",
        "checked_at": now(),
    }


def market(*, universe_limit: int = 5000) -> dict[str, Any]:
    from market_intelligence_engine import aggregation, universe

    uni = universe.load_universe(limit=universe_limit)
    if not uni.get("ok"):
        return {"ok": False, "error": uni.get("error"), "engine": ENGINE_CODE}
    overview = aggregation.market_overview(uni)
    table = aggregation.sector_table(uni)
    # Contribution of each sector's premium to market premium — relative weights by market cap.
    contributions = []
    total_mcap = 0.0
    for s in table:
        members = [r for r in (uni.get("rows") or []) if r.get("sector") == s.get("sector")]
        mcap = sum(num(r.get("market_cap")) or 0 for r in members)
        total_mcap += mcap
        prem = num(s.get("premium_pct"))
        contributions.append({
            "sector": s.get("sector"),
            "premium_pct": prem,
            "historical_percentile": s.get("historical_percentile"),
            "market_cap": mcap or None,
            "companies": s.get("companies"),
            "weight_proxy": mcap,
        })
    # Derived market premium = mcap-weighted sector premiums when available
    weighted = 0.0
    weight_sum = 0.0
    for c in contributions:
        if c["premium_pct"] is not None and c["weight_proxy"]:
            weighted += c["premium_pct"] * c["weight_proxy"]
            weight_sum += c["weight_proxy"]
    market_premium = round(weighted / weight_sum, 1) if weight_sum else None

    # Rank drivers by absolute contribution = premium * weight share
    drivers = []
    for c in contributions:
        if c["premium_pct"] is None or not weight_sum:
            continue
        share = (c["weight_proxy"] or 0) / weight_sum
        contrib = round((c["premium_pct"] or 0) * share, 1)
        drivers.append({
            "sector": c["sector"],
            "contribution_pct": contrib,
            "premium_pct": c["premium_pct"],
            "historical_percentile": c["historical_percentile"],
            "evidence_kind": "derived",
            "source": "market_intelligence_engine.aggregation",
        })
    drivers.sort(key=lambda d: -abs(d["contribution_pct"] or 0))

    avgs = overview.get("averages") or {}
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "market": "Indian Market",
        "as_of": uni.get("valuation_date"),
        "snapshot": {
            "median_pe": avgs.get("pe"),
            "median_pb": avgs.get("pb"),
            "median_ev_ebitda": avgs.get("ev_ebitda"),
            "premium_pct": market_premium,
            "companies": overview.get("companies"),
        },
        "drivers": drivers[:12],
        "largest_contributor": drivers[0] if drivers else None,
        "sector_comparison": [
            {
                "sector": c["sector"],
                "premium_pct": c["premium_pct"],
                "historical_percentile": c["historical_percentile"],
                "stance": (
                    "Premium" if (c["premium_pct"] or 0) >= 5 else
                    "Discount" if (c["premium_pct"] or 0) <= -5 else
                    "Near fair"
                ),
            }
            for c in sorted(contributions, key=lambda x: -(x["premium_pct"] or 0))
        ],
        "why": (
            [f"{drivers[0]['sector']} is the largest derived contributor to market premium."]
            if drivers else
            ["Primary market driver cannot be determined from available data."]
        ),
        "confidence": 85 if drivers else 40,
        "provenance": {
            "universe": "market_intelligence_engine.universe",
            "aggregation": "market_intelligence_engine.aggregation",
        },
        "language": "analysis_only",
        "checked_at": now(),
    }


def peer(symbol: str, *, peer_symbol: Optional[str] = None, universe_limit: int = 5000) -> dict[str, Any]:
    """Compare symbol vs one peer (or top same-industry peer)."""
    ticker = str(symbol or "").strip().upper()
    row = load_universe_row(ticker, universe_limit=universe_limit)
    if not row:
        return {"ok": False, "error": "symbol_not_found", "symbol": ticker}

    other = None
    if peer_symbol:
        other = load_universe_row(str(peer_symbol).upper(), universe_limit=universe_limit)
    if not other:
        # pick largest same-industry peer by market cap
        from market_intelligence_engine import universe

        uni = universe.load_universe(limit=universe_limit)
        industry = row.get("industry")
        candidates = [
            r for r in (uni.get("rows") or [])
            if r.get("industry") == industry and str(r.get("symbol")).upper() != ticker
        ]
        candidates.sort(key=lambda r: -(num(r.get("market_cap")) or 0))
        other = candidates[0] if candidates else None
    if not other:
        return {"ok": False, "error": "peer_not_found", "symbol": ticker}

    pe_a, pe_b = num(row.get("pe")), num(other.get("pe"))
    diff = None
    if pe_a is not None and pe_b:
        diff = round(100.0 * (pe_a - pe_b) / abs(pe_b), 1)

    reasons = []
    for key, label in (("roe", "ROE"), ("roce", "ROCE"), ("ev_ebitda", "EV/EBITDA"), ("pb", "P/B")):
        a, b = num(row.get(key)), num(other.get(key))
        if a is None or b is None:
            continue
        delta = round(a - b, 2)
        if abs(delta) < 0.2 and key != "roe":
            continue
        if key in {"roe", "roce"} and abs(delta) < 0.5:
            continue
        reasons.append({
            "metric": key,
            "label": label,
            "symbol_value": a,
            "peer_value": b,
            "delta": delta,
            "statement": (
                f"{ticker} {label} is {'higher' if delta > 0 else 'lower'} "
                f"({a} vs {b})."
            ),
            "evidence_kind": "observed",
            "source": "market_intelligence_engine.universe",
        })
    reasons.sort(key=lambda r: -abs(r.get("delta") or 0))

    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "symbol": ticker,
        "peer": other.get("symbol"),
        "peer_name": other.get("company_name"),
        "snapshot": {
            "symbol_pe": pe_a,
            "peer_pe": pe_b,
            "difference_pct": diff,
            "symbol_roe": row.get("roe"),
            "peer_roe": other.get("roe"),
        },
        "reasons": reasons[:8],
        "largest_reasons": [r["statement"] for r in reasons[:4]] or [
            "Primary peer difference cannot be determined from available data."
        ],
        "language": "analysis_only",
        "checked_at": now(),
    }


def history(symbol: str, *, metric: str = "pe", window: str = "max") -> dict[str, Any]:
    ticker = str(symbol or "").strip().upper()
    rerating = load_hvie_rerating(ticker, metric=metric, window=window)
    hist = load_hvie_history(ticker, metric=metric, window=window)
    points = hist.get("points") or hist.get("series") or hist.get("history") or []
    if not points and isinstance(hist.get("rows"), list):
        points = hist["rows"]

    early = num(rerating.get("early_median"))
    late = num(rerating.get("late_median"))
    change = num(rerating.get("change_pct"))
    kind = rerating.get("kind")

    drivers = []
    # Company factors for narrative context (current evidence, not historical reconstruction of each year)
    row = load_universe_row(ticker) or {}
    wh = load_warehouse_company(ticker)
    hvie = load_hvie(ticker, metric=metric, window="10y")
    factors = _collect_company_factors(row, wh if wh.get("ok") else {}, hvie, rerating, load_flows())
    for f in factors[:5]:
        drivers.append({
            "label": f["label"],
            "statement": f["statement"],
            "evidence_kind": f["evidence_kind"],
            "source": f["source"],
        })

    title = "Historical multiple expansion" if kind == "expansion" else (
        "Historical multiple compression" if kind == "compression" else "Historical multiple path"
    )
    return {
        "ok": bool(rerating.get("ok") or points),
        "engine": ENGINE_CODE,
        "version": VERSION,
        "symbol": ticker,
        "metric": metric,
        "window": window,
        "title": title,
        "from_value": early,
        "to_value": late,
        "change_pct": change,
        "kind": kind,
        "direction": rerating.get("direction"),
        "sentence": rerating.get("sentence"),
        "cheapest": rerating.get("cheapest"),
        "richest": rerating.get("richest"),
        "daily_change": rerating.get("daily_change"),
        "drivers": drivers or [{
            "label": "Insufficient evidence",
            "statement": "Primary driver cannot be determined from available data.",
            "evidence_kind": "inferred",
            "source": ENGINE_CODE,
        }],
        "observation_count": len(points) if points else rerating.get("observation_count"),
        "language": "analysis_only",
        "checked_at": now(),
    }


def timeline(symbol: str, *, metric: str = "pe", window: str = "max") -> dict[str, Any]:
    """Historical regime timeline + research_timeline valuation events."""
    from historical_valuation_intelligence.statistics import compute_stats

    ticker = str(symbol or "").strip().upper()
    hist = load_hvie_history(ticker, metric=metric, window=window)
    raw_points = hist.get("points") or hist.get("series") or hist.get("history") or hist.get("rows") or []
    # Normalize
    points = []
    for p in raw_points:
        period = p.get("period") or p.get("date")
        value = num(p.get("value") if "value" in p else p.get(metric))
        if period and value is not None:
            points.append({"period": str(period)[:10], "value": value})
    points = sorted(points, key=lambda p: p["period"])

    transitions = []
    if len(points) >= 12:
        # Yearly regime snapshots using expanding history up to year-end
        by_year: dict[str, list[dict[str, Any]]] = {}
        for p in points:
            year = p["period"][:4]
            by_year.setdefault(year, []).append(p)
        years = sorted(by_year.keys())
        prev_regime = None
        for year in years:
            window_points = [p for p in points if p["period"][:4] <= year]
            if len(window_points) < 8:
                continue
            stats = compute_stats(window_points)
            if not stats.get("ok"):
                continue
            # Use last value in year vs full history to date
            year_last = by_year[year][-1]["value"]
            values = [p["value"] for p in window_points]
            pct = round(100.0 * sum(1 for v in values if v <= year_last) / len(values), 1)
            regime = regime_from_percentile(pct).get("regime")
            label = {
                "VERY_CHEAP": "Historically Cheap",
                "CHEAP": "Cheap",
                "FAIR": "Fair",
                "EXPENSIVE": "Premium",
                "VERY_EXPENSIVE": "Bubble / Very Expensive",
            }.get(regime or "", regime or "Unknown")
            event = {
                "year": year,
                "date": by_year[year][-1]["period"],
                "regime": regime,
                "label": label,
                "percentile": pct,
                "value": year_last,
                "median": stats.get("median"),
                "transition_from": prev_regime,
                "clickable": True,
                "evidence_kind": "derived",
                "source": "HVIE reconstructed history",
            }
            if prev_regime and prev_regime != regime:
                event["why"] = f"Regime transition {prev_regime} → {regime} as of {year}."
            else:
                event["why"] = f"Regime {regime} at year-end {year}."
            transitions.append(event)
            prev_regime = regime

    # Research timeline valuation events
    rt = research_timeline_rows(ticker, limit=50)
    research_events = []
    for r in rt:
        event_text = str(r.get("event") or "")
        if "valuation" not in event_text.lower() and "valuation" not in str(r.get("guidance") or "").lower():
            # Still include HVIE-written rows; skip unrelated noise lightly
            if not event_text.startswith("valuation_"):
                continue
        research_events.append({
            "date": r.get("date"),
            "event": event_text,
            "summary": r.get("guidance") or r.get("results"),
            "source": "warehouse.research_timeline",
            "evidence_kind": "observed",
        })

    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "symbol": ticker,
        "metric": metric,
        "window": window,
        "regime_timeline": transitions,
        "research_events": research_events[:30],
        "note": "Timeline derived from HVIE history percentiles and warehouse research_timeline — analysis only.",
        "language": "analysis_only",
        "checked_at": now(),
    }


def opportunities(*, universe_limit: int = 5000, top: int = 10) -> dict[str, Any]:
    from market_intelligence_engine import universe

    uni = universe.load_universe(limit=universe_limit)
    rows = uni.get("rows") or []
    cheap = sorted(
        [r for r in rows if num(r.get("percentile")) is not None and num(r.get("percentile")) <= 25],
        key=lambda r: num(r.get("percentile")) or 0,
    )[:top]
    rich = sorted(
        [r for r in rows if num(r.get("percentile")) is not None and num(r.get("percentile")) >= 75],
        key=lambda r: -(num(r.get("percentile")) or 0),
    )[:top]

    def _attr_card(r: dict[str, Any], stance: str) -> dict[str, Any]:
        pe_chg = num(r.get("pe_change_pct"))
        reasons = []
        if pe_chg is not None and abs(pe_chg) >= MATERIAL_PCT:
            reasons.append(
                f"Multiple {'compressed' if pe_chg < 0 else 'expanded'} {abs(pe_chg):.1f}% vs prior observation."
            )
        if num(r.get("roe")) is not None:
            reasons.append(f"ROE observed at {r.get('roe')}%.")
        if num(r.get("sector_premium_pct")) is not None:
            sp = num(r.get("sector_premium_pct"))
            reasons.append(f"Sector-relative premium {sp:+.1f}%.")
        if not reasons:
            reasons = ["Primary driver cannot be determined from available data."]
        return {
            "symbol": r.get("symbol"),
            "company_name": r.get("company_name"),
            "sector": r.get("sector"),
            "stance": stance,
            "historical_percentile": r.get("percentile"),
            "pe": r.get("pe"),
            "roe": r.get("roe"),
            "reasons": reasons,
            "note": "Potential research candidate — not a recommendation.",
            "evidence_kind": "observed",
            "source": "market_intelligence_engine.universe",
        }

    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "as_of": uni.get("valuation_date"),
        "historically_cheap": [_attr_card(r, "Historically Cheap") for r in cheap],
        "historically_expensive": [_attr_card(r, "Historically Expensive") for r in rich],
        "language": "analysis_only",
        "checked_at": now(),
    }


def leaders(*, universe_limit: int = 5000, top: int = 10) -> dict[str, Any]:
    from market_intelligence_engine import universe

    uni = universe.load_universe(limit=universe_limit)
    rows = [r for r in (uni.get("rows") or []) if r.get("symbol")]

    def top_by(field: str, *, reverse: bool = True):
        pool = [r for r in rows if num(r.get(field)) is not None]
        pool.sort(key=lambda r: num(r.get(field)) or 0, reverse=reverse)
        return [
            {
                "symbol": r.get("symbol"),
                "company_name": r.get("company_name"),
                "sector": r.get("sector"),
                "value": r.get(field),
                "pe": r.get("pe"),
                "historical_percentile": r.get("percentile"),
            }
            for r in pool[:top]
        ]

    # ROE improvement proxy: high ROE + pe expansion as "improving quality + re-rating"
    improving = [
        r for r in rows
        if num(r.get("roe")) is not None and num(r.get("pe_change_pct")) is not None
    ]
    improving.sort(key=lambda r: (num(r.get("roe")) or 0) + max(0, num(r.get("pe_change_pct")) or 0), reverse=True)

    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "as_of": uni.get("valuation_date"),
        "leaders": {
            "largest_rerating": top_by("pe_change_pct", reverse=True),
            "largest_derating": top_by("pe_change_pct", reverse=False),
            "most_improving_roe": [
                {
                    "symbol": r.get("symbol"),
                    "company_name": r.get("company_name"),
                    "sector": r.get("sector"),
                    "roe": r.get("roe"),
                    "pe_change_pct": r.get("pe_change_pct"),
                }
                for r in improving[:top]
            ],
            "most_improving_roce": top_by("roce", reverse=True),
            "largest_premium_expansion": top_by("sector_premium_pct", reverse=True),
            "largest_discount_expansion": top_by("sector_premium_pct", reverse=False),
        },
        "note": "Leaderboards from warehouse observations — research ranking only.",
        "language": "analysis_only",
        "checked_at": now(),
    }
