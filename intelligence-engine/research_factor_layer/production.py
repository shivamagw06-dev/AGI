"""Warehouse-backed Quality Compounder and Relative Mispricing factors."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
import time
from typing import Any, Optional

from institutional_warehouse import store

from .config import (
    BALANCE_SHEET_RISK_VERSION, BALANCE_SHEET_RISK_WEIGHTS,
    CAPITAL_ALLOCATION_VERSION, CAPITAL_ALLOCATION_WEIGHTS,
    EARNINGS_QUALITY_VERSION, EARNINGS_QUALITY_WEIGHTS,
    INVESTED_CAPITAL_METHOD,
    MIN_QUALITY_COMPONENTS,
    MIN_VALUATION_OBSERVATIONS,
    MISPRICING_VERSION,
    MISPRICING_WEIGHTS,
    QUALITY_VERSION,
    QUALITY_WEIGHTS,
    SUSTAINABLE_GROWTH_VERSION, SUSTAINABLE_GROWTH_WEIGHTS,
)
from .math import (
    cagr,
    change_volatility,
    effective_tax_rate,
    free_cash_flow,
    invested_capital,
    median,
    nopat,
    number,
    percentile_rank,
    ratio,
    reinvestment_rate,
    weighted_score,
    trend,
    volatility,
    z_score,
)

FACTOR_LAYER_VERSION = "research-factor-layer-v2.0.0"
_COMPUTE_CACHE: dict[str, tuple[float, dict[str, dict[str, Any]]]] = {}
_CACHE_TTL_SECONDS = 900


def _today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _calculated_at() -> str:
    return datetime.now(timezone.utc).isoformat()


def _eligible(row: dict[str, Any], cutoff: str) -> tuple[bool, bool]:
    available = row.get("filing_date") or row.get("effective_date") or row.get("last_updated")
    if not available:
        return True, False
    return str(available)[:10] <= cutoff, True


def _annual_rows(symbol: str, cutoff: str, source_rows: Optional[list[dict[str, Any]]] = None) -> tuple[list[dict[str, Any]], bool]:
    rows, pit_complete = [], True
    candidates = source_rows if source_rows is not None else (store.all_rows("financials_annual", entity=symbol, limit=100) or [])
    for row in candidates:
        allowed, exact = _eligible(row, cutoff)
        pit_complete = pit_complete and exact
        if allowed:
            rows.append(row)
    detailed_capiq = [row for row in rows if str(row.get("statement_version") or "").startswith("capiq_master_10y_")]
    consolidated = [row for row in rows if str(row.get("statement_type") or "").upper() == "CONSOLIDATED"]
    selected = detailed_capiq or consolidated or [row for row in rows if str(row.get("statement_type") or "").upper() in {"STANDALONE", "UNKNOWN", ""}]
    selected.sort(key=lambda row: str(row.get("fiscal_year") or ""))
    return selected[-10:], pit_complete


def _quality_raw(symbol: str, cutoff: str, source_rows: Optional[list[dict[str, Any]]] = None) -> dict[str, Any]:
    rows, pit_complete = _annual_rows(symbol, cutoff, source_rows)
    observations = []
    for row in rows:
        tax = effective_tax_rate(row.get("pbt"), row.get("pat"))
        operating_nopat = nopat(row.get("ebit"), tax)
        capital = invested_capital(row.get("equity"), row.get("debt"), row.get("cash"))
        fcf = number(row.get("free_cash_flow"))
        if fcf is None:
            fcf = free_cash_flow(row.get("cfo"), row.get("capex"))
        debt, cash = number(row.get("debt")), number(row.get("cash"))
        revenue, pat, ebitda = number(row.get("revenue")), number(row.get("pat")), number(row.get("ebitda"))
        receivables = number(row.get("accounts_receivable"))
        inventory = number(row.get("inventory"))
        exceptional = number(row.get("exceptional_items"))
        finance_cost = number(row.get("finance_cost"))
        acquisitions = number(row.get("acquisition_spending"))
        dividends = number(row.get("dividends_paid"))
        buybacks = number(row.get("buybacks"))
        issued = number(row.get("debt_issuance"))
        repaid = number(row.get("debt_repayment"))
        metrics = {
            "period": row.get("fiscal_year"),
            "revenue": revenue, "ebitda": ebitda, "pat": pat,
            "roic": ratio(operating_nopat, capital),
            "fcf_margin": ratio(fcf, row.get("revenue")),
            "fcf_conversion": ratio(fcf, row.get("pat")),
            "cfo_pat": ratio(row.get("cfo"), pat), "cfo_ebitda": ratio(row.get("cfo"), ebitda),
            "ebitda_margin": ratio(ebitda, revenue),
            "reinvestment_rate": reinvestment_rate(row.get("capex"), row.get("research_and_development"), row.get("depreciation"), operating_nopat),
            "net_debt": debt - cash if debt is not None and cash is not None else None,
            "net_debt_ebitda": ratio(debt - cash if debt is not None and cash is not None else None, ebitda),
            "debt_equity": ratio(debt, row.get("equity")), "cash_debt": ratio(cash, debt),
            "cfo_debt": ratio(row.get("cfo"), debt), "liabilities_equity": ratio(row.get("total_liabilities"), row.get("equity")),
            "interest_coverage": ratio(row.get("ebit"), abs(finance_cost) if finance_cost else None),
            "receivables_intensity": ratio(receivables, revenue), "inventory_intensity": ratio(inventory, revenue),
            "goodwill_assets": ratio(row.get("goodwill"), row.get("assets")),
            "exceptional_pbt": ratio(abs(exceptional) if exceptional is not None else None, abs(number(row.get("pbt"))) if number(row.get("pbt")) else None),
            "acquisition_intensity": ratio(abs(acquisitions) if acquisitions is not None else None, abs(number(row.get("cfo"))) if number(row.get("cfo")) else None),
            "capex_intensity": ratio(abs(number(row.get("capex"))) if number(row.get("capex")) is not None else None, abs(number(row.get("cfo"))) if number(row.get("cfo")) else None),
            "shareholder_distribution": ratio(abs(dividends or 0) + abs(buybacks or 0), abs(number(row.get("cfo"))) if number(row.get("cfo")) else None) if dividends is not None or buybacks is not None else None,
            "net_debt_funding": ratio(abs(issued or 0) - abs(repaid or 0), abs(number(row.get("cfo"))) if number(row.get("cfo")) else None) if issued is not None or repaid is not None else None,
            "fcf_retention": ratio(fcf - abs(dividends or 0) - abs(buybacks or 0), abs(number(row.get("cfo"))) if number(row.get("cfo")) else None) if fcf is not None and (dividends is not None or buybacks is not None) else None,
            "nopat": operating_nopat,
            "invested_capital": capital,
            "source": row.get("source"),
            "filing_date": row.get("filing_date"),
        }
        observations.append(metrics)
    keys = {key for item in observations for key in item if key not in {"period", "source", "filing_date"}}
    series = {key: [item.get(key) for item in observations] for key in keys}
    for key in ("roic", "fcf_margin", "fcf_conversion", "cfo_pat", "cfo_ebitda", "revenue", "ebitda", "pat",
                "ebitda_margin", "reinvestment_rate", "net_debt_ebitda", "interest_coverage",
                "receivables_intensity", "inventory_intensity", "exceptional_pbt", "net_debt",
                "acquisition_intensity", "capex_intensity", "shareholder_distribution", "net_debt_funding",
                "fcf_retention", "debt_equity", "cash_debt", "cfo_debt", "liabilities_equity", "goodwill_assets"):
        series.setdefault(key, [])
    def delta(key: str) -> Optional[float]:
        clean = [number(v) for v in series.get(key, []) if number(v) is not None]
        return clean[-1] - clean[0] if len(clean) >= 2 else None
    raw = {
        "roic_5y_median": median(series["roic"][-5:]),
        "roic_10y_median": median(series["roic"]),
        "roic_trend": trend(series["roic"]),
        "roic_change_volatility": change_volatility(series["roic"]),
        "fcf_margin_5y_median": median(series["fcf_margin"][-5:]),
        "fcf_conversion_5y_median": median(series["fcf_conversion"][-5:]),
        "cfo_pat_median": median(series["cfo_pat"]), "cfo_ebitda_median": median(series["cfo_ebitda"]),
        "revenue_cagr": cagr(series["revenue"]), "ebitda_cagr": cagr(series["ebitda"]), "pat_cagr": cagr(series["pat"]),
        "margin_volatility": volatility(series["ebitda_margin"]), "margin_change": delta("ebitda_margin"),
        "reinvestment_5y_median": median(series["reinvestment_rate"][-5:]),
        "net_debt_ebitda_5y_median": median(series["net_debt_ebitda"][-5:]),
        "interest_coverage_median": median(series["interest_coverage"]),
        "receivables_growth_gap": delta("receivables_intensity"), "inventory_growth_gap": delta("inventory_intensity"),
        "exceptional_dependence": median(series["exceptional_pbt"]),
        "accrual_proxy": None if median(series["cfo_pat"]) is None else 1.0 - median(series["cfo_pat"]),
        "sustainable_growth": None,
        "net_debt_change": delta("net_debt"), "acquisition_intensity": median(series["acquisition_intensity"]),
        "capex_intensity": median(series["capex_intensity"]), "shareholder_distribution": median(series["shareholder_distribution"]),
        "net_debt_funding": median(series["net_debt_funding"]), "fcf_retention": median(series["fcf_retention"]),
        "debt_equity": median(series["debt_equity"]), "cash_debt": median(series["cash_debt"]),
        "cfo_debt": median(series["cfo_debt"]), "liabilities_equity": median(series["liabilities_equity"]),
        "receivables_intensity": median(series["receivables_intensity"]), "inventory_intensity": median(series["inventory_intensity"]),
        "goodwill_assets": median(series["goodwill_assets"]), "leverage_change": delta("net_debt_ebitda"),
    }
    if raw["roic_10y_median"] is not None and raw["reinvestment_5y_median"] is not None:
        raw["sustainable_growth"] = raw["roic_10y_median"] * raw["reinvestment_5y_median"]
    missing = sorted(key for key, value in raw.items() if value is None)
    return {"symbol": symbol, "rows": observations, "raw": raw, "missing": missing, "pit_complete": pit_complete, "observations": len(observations)}


def _master_rows() -> dict[str, dict[str, Any]]:
    return {str(row.get("symbol") or "").upper(): row for row in store.all_rows("company_master", limit=10000) or [] if row.get("symbol")}


def _valuation_rows(cutoff: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in store.all_rows("historical_valuation", limit=250000) or []:
        symbol = str(row.get("symbol") or "").upper()
        if symbol and str(row.get("date") or "") <= cutoff:
            grouped[symbol].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda row: str(row.get("date") or ""))
    return grouped


def _is_financial(master: dict[str, Any]) -> bool:
    identity = " ".join(str(master.get(key) or "") for key in ("sector", "industry", "business_type")).lower()
    return any(word in identity for word in ("bank", "insurance", "financial services", "nbfc"))


def _multiple_valid(metric: str, value: Any, latest: dict[str, Any], master: dict[str, Any]) -> tuple[bool, str]:
    parsed = number(value)
    if parsed is None or parsed <= 0:
        return False, "negative_or_missing_denominator"
    if metric == "ev_ebitda" and _is_financial(master):
        return False, "company_type_incompatible"
    if metric == "pe" and parsed > 250:
        return False, "near_zero_earnings_denominator"
    if metric == "ev_ebitda" and parsed > 100:
        return False, "near_zero_ebitda_denominator"
    return True, "pass"


def _ev_reconciliation(latest: dict[str, Any]) -> tuple[Optional[bool], Optional[float]]:
    reported = number(latest.get("enterprise_value"))
    market_cap = number(latest.get("market_cap"))
    debt = number(latest.get("debt"))
    cash = number(latest.get("cash"))
    if None in (reported, market_cap, debt, cash) or reported == 0:
        return None, None
    implied = market_cap + debt - cash
    difference = abs(reported - implied) / abs(reported)
    return difference <= 0.10, difference


def _quality_results(cutoff: str, symbols: list[str], annual_by_symbol: Optional[dict[str, list[dict[str, Any]]]] = None) -> dict[str, dict[str, Any]]:
    raw = {symbol: _quality_raw(symbol, cutoff, (annual_by_symbol or {}).get(symbol) if annual_by_symbol is not None else None) for symbol in symbols}
    distributions = {key: [pack["raw"].get(key) for pack in raw.values()] for key in next(iter(raw.values()), {"raw": {}})["raw"]}
    results: dict[str, dict[str, Any]] = {}
    def rank(metric: str, value: Any, inverse: bool = False) -> Optional[float]:
        score = percentile_rank(distributions.get(metric, []), value)
        return None if score is None else (100.0 - score if inverse else score)
    specifications = {
        "quality_compounder": (QUALITY_VERSION, QUALITY_WEIGHTS, {
            "roic_quality": [("roic_5y_median", False), ("roic_10y_median", False), ("roic_trend", False)],
            "roic_stability": [("roic_change_volatility", True)],
            "fcf_quality": [("fcf_margin_5y_median", False), ("fcf_conversion_5y_median", False)],
            "growth_quality": [("revenue_cagr", False), ("ebitda_cagr", False), ("pat_cagr", False)],
            "margin_quality": [("margin_volatility", True), ("margin_change", False)],
            "reinvestment_efficiency": [("sustainable_growth", False)],
            "balance_sheet_quality": [("net_debt_ebitda_5y_median", True), ("interest_coverage_median", False)],
        }),
        "earnings_quality": (EARNINGS_QUALITY_VERSION, EARNINGS_QUALITY_WEIGHTS, {
            "cash_conversion": [("cfo_pat_median", False), ("cfo_ebitda_median", False)],
            "working_capital_quality": [("receivables_growth_gap", True), ("inventory_growth_gap", True)],
            "fcf_conversion": [("fcf_conversion_5y_median", False)], "exceptional_quality": [("exceptional_dependence", True)],
            "accrual_quality": [("accrual_proxy", True)],
        }),
        "sustainable_growth": (SUSTAINABLE_GROWTH_VERSION, SUSTAINABLE_GROWTH_WEIGHTS, {
            "growth": [("revenue_cagr", False), ("ebitda_cagr", False), ("pat_cagr", False)],
            "sustainable_growth": [("sustainable_growth", False)], "margin_change": [("margin_change", False)],
            "internal_funding": [("fcf_retention", False), ("leverage_change", True)],
            "capital_efficiency": [("roic_10y_median", False)],
        }),
        "capital_allocation": (CAPITAL_ALLOCATION_VERSION, CAPITAL_ALLOCATION_WEIGHTS, {
            "reinvestment_returns": [("roic_10y_median", False), ("sustainable_growth", False)],
            "cash_discipline": [("fcf_retention", False), ("capex_intensity", True)],
            "acquisition_discipline": [("acquisition_intensity", True)],
            "shareholder_distribution": [("shareholder_distribution", False)],
            "debt_discipline": [("net_debt_funding", True), ("leverage_change", True)],
        }),
        "balance_sheet_risk": (BALANCE_SHEET_RISK_VERSION, BALANCE_SHEET_RISK_WEIGHTS, {
            "leverage": [("net_debt_ebitda_5y_median", True), ("debt_equity", True), ("leverage_change", True)],
            "coverage": [("interest_coverage_median", False)], "cash_debt": [("cash_debt", False)],
            "cfo_debt": [("cfo_debt", False)], "liabilities_equity": [("liabilities_equity", True)],
            "working_capital_risk": [("receivables_intensity", True), ("inventory_intensity", True)],
            "asset_risk": [("goodwill_assets", True)],
        }),
    }
    for symbol, pack in raw.items():
        values = pack["raw"]
        factors = {}
        for name, (version, weights, component_map) in specifications.items():
            components = {}
            for component, metrics in component_map.items():
                ranked = [rank(metric, values.get(metric), inverse) for metric, inverse in metrics]
                components[component] = median(ranked)
            factor_score = weighted_score(components, weights, minimum=max(2, min(3, len(weights))))
            available = sum(value is not None for value in components.values())
            factors[name] = {"factor_name": name, "factor_version": version, "company_id": symbol,
                "as_of_date": cutoff, "data_cutoff": cutoff, "score": round(factor_score, 1) if factor_score is not None else None,
                "raw_score": round(factor_score / 100.0, 4) if factor_score is not None else None, "calculated_at": _calculated_at(),
                "percentile": None, "raw_metrics": values, "metric_history": pack["rows"],
                "component_scores": {key: round(value, 1) if value is not None else None for key, value in components.items()},
                "component_weights": weights, "evidence": [], "missing_data": pack["missing"],
                "coverage": round(available / len(components), 3), "data_quality": round(100 * available / len(components), 1),
                "confidence": "HIGH" if available / len(components) >= .8 else "MEDIUM" if available / len(components) >= .6 else "LOW",
                "methodology_status": "IN_DEVELOPMENT", "validation_status": "POINT_IN_TIME_LIMITED",
                "signal_label": "Annual fundamental signal — PIT limited", "methodology": {"invested_capital": INVESTED_CAPITAL_METHOD},
                "provenance": [{"period": row.get("period"), "source": row.get("source"), "filing_date": row.get("filing_date")} for row in pack["rows"]]}
        quality = factors["quality_compounder"]
        if values.get("roic_10y_median") is not None: quality["evidence"].append(f"10Y median ROIC {values['roic_10y_median'] * 100:.1f}%")
        if values.get("fcf_conversion_5y_median") is not None: quality["evidence"].append(f"FCF conversion {values['fcf_conversion_5y_median'] * 100:.1f}%")
        results[symbol] = factors
    for factor_name in specifications:
        scores = [pack[factor_name]["score"] for pack in results.values()]
        for pack in results.values():
            factor = pack[factor_name]
            factor["percentile"] = round(percentile_rank(scores, factor["score"]), 1) if factor["score"] is not None else None
    return results


def _mispricing_result(symbol: str, cutoff: str, master: dict[str, Any], rows: list[dict[str, Any]], quality: dict[str, Any], peer_latest: list[dict[str, Any]]) -> dict[str, Any]:
    latest = rows[-1] if rows else {}
    raw_metrics, component_scores, evidence, missing, gates = {}, {}, [], [], {}
    ev_matches, ev_difference = _ev_reconciliation(latest)
    gates["enterprise_value_reconciliation"] = "unavailable" if ev_matches is None else ("pass" if ev_matches else "fail")
    for metric in ("pe", "ev_ebitda", "pb"):
        current = latest.get(metric)
        valid, reason = _multiple_valid(metric, current, latest, master)
        if metric == "ev_ebitda" and ev_matches is False:
            valid, reason = False, "enterprise_value_reconciliation_failed"
        gates[metric] = reason
        history = [number(row.get(metric)) for row in rows if number(row.get(metric)) is not None and number(row.get(metric)) > 0]
        if not valid or len(history) < MIN_VALUATION_OBSERVATIONS:
            missing.append(metric if valid else f"{metric}:{reason}")
            raw_metrics[metric] = {"current": number(current), "observations": len(history), "z_score": None, "historical_percentile": None}
            component_scores[metric] = None
            continue
        percentile = percentile_rank(history, current)
        z = z_score(history, current)
        raw_metrics[metric] = {"current": number(current), "observations": len(history), "z_score": round(z, 3) if z is not None else None, "historical_percentile": round(percentile, 1)}
        component_scores[metric] = 100.0 - percentile
        evidence.append(f"{metric.upper()} at its {percentile:.0f}th historical percentile" + (f" (z {z:.2f})" if z is not None else ""))
    industry = str(master.get("industry") or "")
    eligible_peers = [row for row in peer_latest if row.get("symbol") != symbol and str(row.get("industry") or "") == industry]
    primary = "pb" if _is_financial(master) else "ev_ebitda"
    peer_values = [number(row.get(primary)) for row in eligible_peers if number(row.get(primary)) and number(row.get(primary)) > 0]
    peer_median = median(peer_values)
    current_primary = number(latest.get(primary))
    peer_discount = 1.0 - current_primary / peer_median if current_primary and peer_median else None
    peer_gate = "pass" if industry and len(peer_values) >= 3 else "insufficient_valid_peers"
    gates["peer_selection"] = peer_gate
    gates["accounting_period_alignment"] = "limited_latest_observation_only"
    raw_metrics["enterprise_value_reconciliation"] = {"within_tolerance": ev_matches, "difference": ev_difference, "tolerance": 0.10}
    raw_metrics["peer_relative"] = {"metric": primary, "industry": industry or None, "peer_count": len(peer_values), "peer_median": peer_median, "discount": peer_discount}
    component_scores["peer_relative"] = max(0.0, min(100.0, 50.0 + peer_discount * 100.0)) if peer_discount is not None and len(peer_values) >= 3 else None
    component_scores["quality_support"] = quality.get("score")
    score = weighted_score(component_scores, MISPRICING_WEIGHTS, minimum=2)
    if peer_discount is not None:
        evidence.append(f"{primary.upper()} is {abs(peer_discount) * 100:.1f}% {'below' if peer_discount >= 0 else 'above'} the industry median")
    return {
        "factor_name": "relative_mispricing", "factor_version": MISPRICING_VERSION, "company_id": symbol,
        "as_of_date": cutoff, "data_cutoff": cutoff, "score": round(score, 1) if score is not None else None,
        "calculated_at": _calculated_at(),
        "percentile": None, "raw_metrics": raw_metrics, "metric_history": {"valuation_observations": len(rows), "latest_date": latest.get("date")},
        "component_scores": {k: round(v, 1) if v is not None else None for k, v in component_scores.items()},
        "component_weights": MISPRICING_WEIGHTS, "evidence": evidence, "missing_data": missing,
        "data_quality": round(100.0 * sum(1 for value in component_scores.values() if value is not None) / len(component_scores), 1),
        "methodology_status": "IN_DEVELOPMENT", "validation_status": "POINT_IN_TIME_LIMITED",
        "validation_gates": gates,
        "provenance": {"source": latest.get("source"), "period": latest.get("date")},
    }


def _compute(cutoff: str, limit: int = 5000) -> dict[str, dict[str, Any]]:
    cached = _COMPUTE_CACHE.get(cutoff)
    if cached and time.monotonic() - cached[0] < _CACHE_TTL_SECONDS:
        return cached[1]
    masters = _master_rows()
    valuations = _valuation_rows(cutoff)
    annual_by_symbol: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in store.all_rows("financials_annual", limit=100000) or []:
        symbol = str(row.get("symbol") or "").upper()
        if symbol:
            annual_by_symbol[symbol].append(row)
    financial_symbols = set(annual_by_symbol)
    symbols = sorted(set(masters) & (set(valuations) | financial_symbols))[:max(1, limit)]
    accounting = _quality_results(cutoff, symbols, annual_by_symbol)
    peer_latest = [{**masters.get(symbol, {}), **rows[-1]} for symbol, rows in valuations.items() if rows]
    out = {}
    for symbol in symbols:
        factor_pack = accounting.get(symbol, {})
        mispricing = _mispricing_result(symbol, cutoff, masters.get(symbol, {}), valuations.get(symbol, []), factor_pack.get("quality_compounder", {}), peer_latest)
        out[symbol] = {"company": masters.get(symbol, {}), **factor_pack, "relative_mispricing": mispricing}
    mispricing_scores = [pack["relative_mispricing"]["score"] for pack in out.values()]
    for pack in out.values():
        factor = pack["relative_mispricing"]
        factor["percentile"] = round(percentile_rank(mispricing_scores, factor["score"]), 1) if factor["score"] is not None else None
    _COMPUTE_CACHE[cutoff] = (time.monotonic(), out)
    return out


def company(symbol: str, *, as_of: Optional[str] = None) -> dict[str, Any]:
    ticker, cutoff = str(symbol or "").upper(), str(as_of or _today())[:10]
    result = _compute(cutoff).get(ticker)
    return {"ok": bool(result), "layer_version": FACTOR_LAYER_VERSION, "as_of": cutoff, "result": result, "policy": "Research factors only; no recommendation or execution."}


def audit(*, as_of: Optional[str] = None, limit: int = 20) -> dict[str, Any]:
    cutoff = str(as_of or _today())[:10]
    results = _compute(cutoff)
    rows = []
    for symbol, pack in results.items():
        quality, value = pack["quality_compounder"], pack["relative_mispricing"]
        factor_labels = (("Quality Compounder", quality.get("score")),
                         ("Earnings Quality", pack.get("earnings_quality", {}).get("score")),
                         ("Sustainable Growth", pack.get("sustainable_growth", {}).get("score")),
                         ("Capital Allocation", pack.get("capital_allocation", {}).get("score")),
                         ("Balance-Sheet Quality", pack.get("balance_sheet_risk", {}).get("score")),
                         ("Relative Mispricing", value.get("score")))
        available_factors = [(name, score) for name, score in factor_labels if score is not None]
        rows.append({
            "symbol": symbol, "company_name": pack["company"].get("company_name"),
            "quality_score": quality.get("score"), "roic_5y": quality.get("raw_metrics", {}).get("roic_5y_median"),
            "roic_percentile": quality.get("component_scores", {}).get("roic_5y"),
            "fcf_margin": quality.get("raw_metrics", {}).get("fcf_margin_5y_median"),
            "mispricing_score": value.get("score"), "valuation_percentile": value.get("percentile"),
            "earnings_quality_score": pack.get("earnings_quality", {}).get("score"),
            "sustainable_growth_score": pack.get("sustainable_growth", {}).get("score"),
            "capital_allocation_score": pack.get("capital_allocation", {}).get("score"),
            "balance_sheet_risk_score": pack.get("balance_sheet_risk", {}).get("score"),
            "data_quality": round((quality.get("data_quality", 0) + value.get("data_quality", 0)) / 2, 1),
            "validation_status": "POINT_IN_TIME_LIMITED" if any("LIMITED" in str(status) for status in (quality.get("validation_status"), value.get("validation_status"))) else "POINT_IN_TIME_READY",
            "primary_evidence": (value.get("evidence") or quality.get("evidence") or [])[:3],
            "primary_factor": max(available_factors, key=lambda item: item[1])[0] if available_factors else "Unavailable",
            "supporting_factors": [name for name, _ in available_factors],
            "contradictory_evidence": (quality.get("missing_data") or [])[:2] + (value.get("missing_data") or [])[:2],
            "key_risk": "Valuation history is not fully publication-vintaged; do not treat this as a backtest-ready signal.",
        })
    rows.sort(key=lambda row: (-(row.get("quality_score") or -1), -(row.get("mispricing_score") or -1)))
    return {"ok": True, "layer_version": FACTOR_LAYER_VERSION, "as_of": cutoff, "universe": len(results), "rows": rows[:max(1, min(limit, 100))], "status": "IN_DEVELOPMENT"}


def health() -> dict[str, Any]:
    return {"ok": True, "layer": "AGI Research Factor Layer", "version": FACTOR_LAYER_VERSION,
            "factors": {name: "IN_DEVELOPMENT" for name in ("quality_compounder", "earnings_quality", "sustainable_growth", "capital_allocation", "balance_sheet_risk", "relative_mispricing")},
            "pit_policy": "Annual fundamental signal — PIT limited"}
