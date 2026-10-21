"""Pillar scorers — primary outputs; overall score is derived elsewhere."""

from __future__ import annotations

from typing import Any

from business_quality.metrics_util import (
    clamp_score,
    direction_points,
    make_finding,
    multi_year_direction,
    series_volatility,
)
from business_quality.schema import (
    CONF_HIGH,
    CONF_LOW,
    CONF_MEDIUM,
    PILLAR_BALANCE,
    PILLAR_CAPITAL,
    PILLAR_CASH,
    PILLAR_EXECUTION,
    PILLAR_GROWTH,
    PILLAR_MODEL,
    PILLAR_PROFIT,
    PILLAR_TITLES,
)
from evidence_fusion.signals import check_expectation


def _conf(evidence_n: int, coverage_pct: float | None) -> str:
    pts = 0
    if evidence_n >= 4:
        pts += 2
    elif evidence_n >= 2:
        pts += 1
    if coverage_pct is not None:
        if coverage_pct >= 80:
            pts += 1
        elif coverage_pct < 40:
            pts -= 1
    if pts >= 3:
        return CONF_HIGH
    if pts >= 1:
        return CONF_MEDIUM
    return CONF_LOW


def score_growth(
    series_map: dict[str, list[dict[str, Any]]],
    signals: dict[str, dict[str, Any]],
    *,
    fire01: list[dict[str, Any]],
    fire03: list[dict[str, Any]],
    coverage_pct: float | None,
) -> dict[str, Any]:
    evid: list[dict[str, Any]] = []
    points = 50.0
    rev = signals.get("revenue")
    if rev and rev.get("comparable"):
        d = rev.get("direction")
        points += direction_points(d, favorable="up")
        evid.append({"metric": "revenue", "direction": d, "pct_change": rev.get("pct_change")})
    my = multi_year_direction(series_map.get("revenue"))
    if my:
        points += direction_points(my, favorable="up") * 0.75
        evid.append({"metric": "revenue", "multi_year_direction": my})
    vol = series_volatility(series_map.get("revenue"))
    if vol is not None:
        # Lower volatility → higher consistency contribution
        if vol < 0.5:
            points += 10
        elif vol < 1.0:
            points += 5
        elif vol > 2.0:
            points -= 8
        evid.append({"metric": "revenue", "volatility_cv": round(vol, 4)})
    seg_facts = [f for f in fire03 if f.get("category") in {"Business Segments", "Segment Analysis"}]
    if seg_facts:
        points += min(8.0, 2.0 * len(seg_facts))
        evid.append({"source": "FIRE-03", "segment_facts_n": len(seg_facts)})
    rev_findings = [f for f in fire01 if f.get("metric") == "revenue"]
    if rev_findings:
        evid.append({"source": "FIRE-01", "findings_n": len(rev_findings)})
        if any(f.get("severity") == "positive" for f in rev_findings):
            points += 5
        if any(f.get("severity") in {"warning", "negative"} for f in rev_findings):
            points -= 5

    score = clamp_score(points) if evid else None
    return make_finding(
        pillar_id=PILLAR_GROWTH,
        title=PILLAR_TITLES[PILLAR_GROWTH],
        score=score,
        evidence=evid,
        confidence=_conf(len(evid), coverage_pct),
        supporting_modules=["warehouse", "FIRE-01", "FIRE-03"],
        narrative=(
            f"Growth Quality score {score} from revenue trend, consistency, and disclosed segment evidence."
            if score is not None
            else "Growth Quality cannot be scored — insufficient revenue evidence."
        ),
        components={"latest_direction": (rev or {}).get("direction"), "multi_year": my, "volatility_cv": vol},
    )


def score_profitability(
    series_map: dict[str, list[dict[str, Any]]],
    signals: dict[str, dict[str, Any]],
    *,
    coverage_pct: float | None,
) -> dict[str, Any]:
    evid: list[dict[str, Any]] = []
    points = 50.0
    for metric, fav in (
        ("operating_margin", "up"),
        ("gross_margin", "up"),
        ("net_margin", "up"),
        ("roe", "up"),
        ("roce", "up"),
        ("roic", "up"),
    ):
        sig = signals.get(metric)
        if not sig or not sig.get("comparable"):
            continue
        d = sig.get("direction")
        points += direction_points(d, favorable=fav) * (1.0 if metric.endswith("margin") else 0.8)
        evid.append({"metric": metric, "direction": d, "pct_change": sig.get("pct_change")})
        # Stability: flat is mildly constructive for margins
        if metric.endswith("margin") and d == "flat":
            points += 2

    score = clamp_score(points) if evid else None
    return make_finding(
        pillar_id=PILLAR_PROFIT,
        title=PILLAR_TITLES[PILLAR_PROFIT],
        score=score,
        evidence=evid,
        confidence=_conf(len(evid), coverage_pct),
        supporting_modules=["warehouse", "DME"],
        narrative=(
            f"Profitability Quality score {score} from margin and return metric evidence."
            if score is not None
            else "Profitability Quality cannot be scored — insufficient margin/return evidence."
        ),
    )


def score_cash(
    series_map: dict[str, list[dict[str, Any]]],
    signals: dict[str, dict[str, Any]],
    *,
    coverage_pct: float | None,
) -> dict[str, Any]:
    evid: list[dict[str, Any]] = []
    points = 50.0
    for metric, fav in (
        ("operating_cash_flow", "up"),
        ("free_cash_flow", "up"),
    ):
        sig = signals.get(metric)
        if sig and sig.get("comparable"):
            d = sig.get("direction")
            points += direction_points(d, favorable=fav)
            evid.append({"metric": metric, "direction": d, "pct_change": sig.get("pct_change")})
    wc = signals.get("working_capital")
    if wc and wc.get("comparable"):
        # WC rising often pressures cash — treat down/flat as constructive
        outcome = check_expectation(wc, "down_or_flat")
        if outcome == "support":
            points += 8
        elif outcome == "conflict":
            points -= 8
        evid.append({"metric": "working_capital", "direction": wc.get("direction"), "outcome": outcome})

    # Cash conversion: OCF vs net income when both latest available
    ocf = (signals.get("operating_cash_flow") or {}).get("latest")
    ni_series = series_map.get("net_income") or []
    from financial_intelligence.trends import normalize_series

    ni_rows = normalize_series(ni_series)
    if ocf and ni_rows:
        ni_val = float(ni_rows[-1]["value"])
        ocf_val = float(ocf.get("value"))
        if ni_val != 0:
            conv = ocf_val / abs(ni_val)
            evid.append({"metric": "cash_conversion_ocf_pat", "value": round(conv, 4)})
            if conv >= 1.0:
                points += 10
            elif conv >= 0.7:
                points += 4
            elif conv < 0.4:
                points -= 8

    score = clamp_score(points) if evid else None
    return make_finding(
        pillar_id=PILLAR_CASH,
        title=PILLAR_TITLES[PILLAR_CASH],
        score=score,
        evidence=evid,
        confidence=_conf(len(evid), coverage_pct),
        supporting_modules=["warehouse", "DME", "FKB"],
        narrative=(
            f"Cash Flow Quality score {score} from operating/free cash flow, working capital, and conversion evidence."
            if score is not None
            else "Cash Flow Quality cannot be scored — insufficient cash evidence."
        ),
    )


def score_balance_sheet(
    signals: dict[str, dict[str, Any]],
    *,
    coverage_pct: float | None,
) -> dict[str, Any]:
    evid: list[dict[str, Any]] = []
    points = 50.0
    for metric, fav in (
        ("net_debt", "down"),
        ("total_debt", "down"),
        ("interest_coverage", "up"),
        ("cash", "up"),
    ):
        sig = signals.get(metric)
        if not sig or not sig.get("comparable"):
            continue
        # Prefer net_debt over total_debt when both present
        if metric == "total_debt" and signals.get("net_debt", {}).get("comparable"):
            continue
        d = sig.get("direction")
        points += direction_points(d, favorable=fav)
        evid.append({"metric": metric, "direction": d, "pct_change": sig.get("pct_change")})

    score = clamp_score(points) if evid else None
    return make_finding(
        pillar_id=PILLAR_BALANCE,
        title=PILLAR_TITLES[PILLAR_BALANCE],
        score=score,
        evidence=evid,
        confidence=_conf(len(evid), coverage_pct),
        supporting_modules=["warehouse", "DME"],
        narrative=(
            f"Balance Sheet Quality score {score} from leverage, coverage, and liquidity evidence."
            if score is not None
            else "Balance Sheet Quality cannot be scored — insufficient leverage/liquidity evidence."
        ),
    )


def score_capital_allocation(
    signals: dict[str, dict[str, Any]],
    *,
    fire04: list[dict[str, Any]],
    fire03: list[dict[str, Any]],
    coverage_pct: float | None,
) -> dict[str, Any]:
    evid: list[dict[str, Any]] = []
    points = 50.0
    for metric in ("capex", "dividends", "share_buybacks"):
        sig = signals.get(metric)
        if not sig:
            continue
        if metric == "capex" and sig.get("comparable"):
            # Capex presence with non-collapse is neutral-positive for allocation capacity
            d = sig.get("direction")
            points += 4 if d in {"up", "flat"} else -2
            evid.append({"metric": metric, "direction": d, "pct_change": sig.get("pct_change")})
        elif metric in {"dividends", "share_buybacks"}:
            latest = (sig.get("latest") or {}).get("value")
            if isinstance(latest, (int, float)) and latest > 0:
                points += 6
                evid.append({"metric": metric, "value": latest, "present_positive": True})

    capital_facts = [
        f
        for f in fire03
        if f.get("category")
        in {"Dividends", "Buybacks", "Cash Deployment", "Capital Expenditure", "Debt Reduction"}
    ]
    if capital_facts:
        points += min(8.0, len(capital_facts))
        evid.append({"source": "FIRE-03", "capital_facts_n": len(capital_facts)})

    # Soft use FIRE-04 capital fusion outcomes (no duplicated fusion logic)
    capital_fusion = [
        f
        for f in fire04
        if f.get("consistency_bucket") == "capital_allocation_consistency"
        or f.get("topic_id") in {"debt_reduction", "capital_returns", "capacity_expansion", "liquidity"}
    ]
    if capital_fusion:
        supported = sum(1 for f in capital_fusion if f.get("fusion_result") == "Supported")
        unsupported = sum(1 for f in capital_fusion if f.get("fusion_result") == "Not Supported")
        points += 4 * supported
        points -= 4 * unsupported
        evid.append(
            {
                "source": "FIRE-04",
                "capital_fusion_n": len(capital_fusion),
                "supported": supported,
                "not_supported": unsupported,
            }
        )

    score = clamp_score(points) if evid else None
    return make_finding(
        pillar_id=PILLAR_CAPITAL,
        title=PILLAR_TITLES[PILLAR_CAPITAL],
        score=score,
        evidence=evid,
        confidence=_conf(len(evid), coverage_pct),
        supporting_modules=["warehouse", "FIRE-03", "FIRE-04"],
        narrative=(
            f"Capital Allocation Quality score {score} from capex/returns evidence and FIRE-03/04 capital signals."
            if score is not None
            else "Capital Allocation Quality cannot be scored — insufficient capital evidence."
        ),
    )


def score_management_execution(
    *,
    fire05_score: dict[str, Any] | None,
    fire05_findings: list[dict[str, Any]] | None,
    coverage_pct: float | None,
) -> dict[str, Any]:
    """Reuse FIRE-05 Management Execution Score — do not duplicate evaluation logic."""
    evid: list[dict[str, Any]] = []
    score_val = None
    if fire05_score and fire05_score.get("management_execution_score") is not None:
        score_val = float(fire05_score["management_execution_score"])
        evid.append(
            {
                "source": "FIRE-05",
                "management_execution_score": score_val,
                "delivered": fire05_score.get("delivered"),
                "outstanding": fire05_score.get("outstanding"),
                "objectives_tracked": fire05_score.get("objectives_tracked"),
            }
        )
    if fire05_findings:
        evid.append({"source": "FIRE-05", "findings_n": len(fire05_findings)})

    return make_finding(
        pillar_id=PILLAR_EXECUTION,
        title=PILLAR_TITLES[PILLAR_EXECUTION],
        score=round(score_val, 2) if score_val is not None else None,
        evidence=evid,
        confidence=_conf(len(evid), coverage_pct),
        supporting_modules=["FIRE-05"],
        narrative=(
            f"Management Execution pillar reuses FIRE-05 score {score_val}."
            if score_val is not None
            else "Management Execution pillar unavailable — FIRE-05 score not present."
        ),
        components={"reused_fire05": True, "duplicated_logic": False},
    )


def score_business_model(
    fire03: list[dict[str, Any]],
    *,
    coverage_pct: float | None,
) -> dict[str, Any]:
    evid: list[dict[str, Any]] = []
    points = 45.0
    segments = [f for f in fire03 if f.get("category") in {"Business Segments", "Segment Analysis"}]
    geos = [f for f in fire03 if f.get("category") == "Geographic Exposure"]
    customers = [f for f in fire03 if f.get("category") == "Customer Profile"]
    recurring = [
        f
        for f in fire03
        if f.get("category") == "Revenue Model"
        or "recurring" in str(f.get("statement") or "").lower()
        or "subscription" in str(f.get("statement") or "").lower()
    ]
    concentration = [
        f
        for f in fire03
        if "concentration" in str(f.get("statement") or "").lower()
        or "concentration" in str(f.get("evidence") or "").lower()
    ]

    if segments:
        points += min(15.0, 3.0 * len(segments))
        evid.append({"source": "FIRE-03", "segment_facts_n": len(segments), "theme": "segment_diversification"})
    if geos:
        points += min(12.0, 4.0 * len(geos))
        evid.append({"source": "FIRE-03", "geographic_facts_n": len(geos), "theme": "geographic_diversification"})
    if customers:
        evid.append({"source": "FIRE-03", "customer_facts_n": len(customers)})
        points += 4
    if concentration:
        # Disclosed concentration is a stability caution (not a judgment of badness)
        points -= min(10.0, 3.0 * len(concentration))
        evid.append(
            {
                "source": "FIRE-03",
                "customer_concentration_disclosed": True,
                "facts_n": len(concentration),
                "note": "only_if_disclosed",
            }
        )
    if recurring:
        points += min(12.0, 4.0 * len(recurring))
        evid.append(
            {
                "source": "FIRE-03",
                "recurring_revenue_disclosed": True,
                "facts_n": len(recurring),
                "note": "only_if_disclosed",
            }
        )

    score = clamp_score(points) if evid else None
    return make_finding(
        pillar_id=PILLAR_MODEL,
        title=PILLAR_TITLES[PILLAR_MODEL],
        score=score,
        evidence=evid,
        confidence=_conf(len(evid), coverage_pct),
        supporting_modules=["FIRE-03"],
        narrative=(
            f"Business Model Stability score {score} from disclosed diversification / revenue-model evidence only."
            if score is not None
            else "Business Model Stability cannot be scored — no disclosed diversification evidence."
        ),
    )


def score_all_pillars(
    *,
    series_map: dict[str, list[dict[str, Any]]],
    signals: dict[str, dict[str, Any]],
    fire01: list[dict[str, Any]],
    fire03: list[dict[str, Any]],
    fire04: list[dict[str, Any]],
    fire05_score: dict[str, Any] | None,
    fire05_findings: list[dict[str, Any]] | None,
    coverage_pct: float | None,
) -> dict[str, dict[str, Any]]:
    return {
        PILLAR_GROWTH: score_growth(
            series_map, signals, fire01=fire01, fire03=fire03, coverage_pct=coverage_pct
        ),
        PILLAR_PROFIT: score_profitability(series_map, signals, coverage_pct=coverage_pct),
        PILLAR_CASH: score_cash(series_map, signals, coverage_pct=coverage_pct),
        PILLAR_BALANCE: score_balance_sheet(signals, coverage_pct=coverage_pct),
        PILLAR_CAPITAL: score_capital_allocation(
            signals, fire04=fire04, fire03=fire03, coverage_pct=coverage_pct
        ),
        PILLAR_EXECUTION: score_management_execution(
            fire05_score=fire05_score, fire05_findings=fire05_findings, coverage_pct=coverage_pct
        ),
        PILLAR_MODEL: score_business_model(fire03, coverage_pct=coverage_pct),
    }
