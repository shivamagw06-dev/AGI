"""Fail-closed evaluator for non-commercial-bank financial subsectors."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import median
from typing import Any

from causal_research_engine.service import ask_context
from financial_engine import calculate
from financials_valuation.classification import classify_financial_subsector
from financials_valuation.nonbank_models import MODELS


@dataclass(frozen=True)
class Profile:
    required: tuple[str, ...]
    calculation: str
    calculation_inputs: tuple[str, ...]
    risk_ratios: tuple[str, ...] = ()
    positive: tuple[str, ...] = ()


PROFILES = {
    "SMALL_FINANCE_BANK": Profile(("market_price","book_value_per_share","normalized_eps","roe","growth","cost_of_equity","gnpa","credit_cost","capital_adequacy"), "FINANCIAL_PRICE_TO_BOOK", ("market_price","book_value_per_share"), ("gnpa","credit_cost","capital_adequacy"), ("market_price","book_value_per_share","normalized_eps")),
    "NBFC": Profile(("market_price","book_value_per_share","normalized_eps","roe","growth","cost_of_equity","gnpa","credit_cost","capital_adequacy","leverage"), "FINANCIAL_PRICE_TO_BOOK", ("market_price","book_value_per_share"), ("gnpa","credit_cost","capital_adequacy"), ("market_price","book_value_per_share","normalized_eps","leverage")),
    "HOUSING_FINANCE": Profile(("market_price","book_value_per_share","normalized_eps","roe","growth","cost_of_equity","gnpa","credit_cost","capital_adequacy","ltv"), "FINANCIAL_PRICE_TO_BOOK", ("market_price","book_value_per_share"), ("gnpa","credit_cost","capital_adequacy","ltv"), ("market_price","book_value_per_share","normalized_eps")),
    "LIFE_INSURANCE": Profile(("market_price","embedded_value_per_share","normalized_eps","vnb","ape","persistency","solvency","cost_of_equity","payout_ratio","agi_growth_expectation"), "PRICE_TO_EMBEDDED_VALUE", ("market_price","embedded_value_per_share"), ("persistency","solvency","payout_ratio"), ("market_price","embedded_value_per_share","normalized_eps","vnb","ape")),
    "GENERAL_INSURANCE": Profile(("market_price","book_value_per_share","normalized_eps","claims_ratio","expense_ratio","solvency","cost_of_equity","payout_ratio","agi_growth_expectation"), "FINANCIAL_PRICE_TO_BOOK", ("market_price","book_value_per_share"), ("claims_ratio","expense_ratio","solvency","payout_ratio"), ("market_price","book_value_per_share","normalized_eps")),
    "HEALTH_INSURANCE": Profile(("market_price","book_value_per_share","normalized_eps","claims_ratio","expense_ratio","solvency","cost_of_equity","payout_ratio","agi_growth_expectation"), "FINANCIAL_PRICE_TO_BOOK", ("market_price","book_value_per_share"), ("claims_ratio","expense_ratio","solvency","payout_ratio"), ("market_price","book_value_per_share","normalized_eps")),
    "ASSET_MANAGEMENT": Profile(("market_price","normalized_eps","aum","net_flows","fee_yield","operating_margin","retention","cost_of_equity","payout_ratio","agi_growth_expectation"), "FINANCIAL_PRICE_TO_EARNINGS", ("market_price","normalized_eps"), ("fee_yield","operating_margin","retention","payout_ratio"), ("market_price","normalized_eps","aum")),
    "BROKER": Profile(("market_price","normalized_eps","active_clients","trading_volume","market_share","revenue_per_client","operating_margin","cost_of_equity","payout_ratio","agi_growth_expectation"), "FINANCIAL_PRICE_TO_EARNINGS", ("market_price","normalized_eps"), ("market_share","operating_margin","payout_ratio"), ("market_price","normalized_eps","active_clients","trading_volume","revenue_per_client")),
    "EXCHANGE_INFRASTRUCTURE": Profile(("market_price","normalized_eps","trading_volume","market_share","operating_margin","fcf_per_share","cost_of_equity","payout_ratio","agi_growth_expectation"), "FINANCIAL_PRICE_TO_EARNINGS", ("market_price","normalized_eps"), ("market_share","operating_margin","payout_ratio"), ("market_price","normalized_eps","trading_volume","fcf_per_share")),
    "FINTECH_PAYMENTS": Profile(("enterprise_value","revenue","gross_profit","tpv","contribution_profit","cash_burn","terminal_multiple","horizon_years","agi_growth_expectation"), "EV_GROSS_PROFIT", ("enterprise_value","gross_profit"), (), ("enterprise_value","revenue","gross_profit","tpv","terminal_multiple","horizon_years")),
    "PAYMENTS_BANK": Profile(("enterprise_value","revenue","gross_profit","tpv","contribution_profit","cash_burn","terminal_multiple","horizon_years","agi_growth_expectation"), "EV_GROSS_PROFIT", ("enterprise_value","gross_profit"), (), ("enterprise_value","revenue","gross_profit","tpv","terminal_multiple","horizon_years")),
    "DIVERSIFIED_FINANCIALS": Profile(("segment_1_value","segment_2_value","segment_3_value","net_debt","holdco_discount","market_cap"), "SOTP_3_SEGMENT", ("segment_1_value","segment_2_value","segment_3_value","net_debt","holdco_discount"), ("holdco_discount",), ("segment_1_value","segment_2_value","segment_3_value","market_cap")),
}


def _issue(item: Any, as_of: str) -> str | None:
    if not isinstance(item, dict) or not isinstance(item.get("value"), (int, float)) or isinstance(item.get("value"), bool):
        return "MISSING_OR_INVALID"
    if not item.get("source_id") or not item.get("period") or not item.get("available_at"):
        return "PROVENANCE_REQUIRED"
    if str(item["available_at"])[:10] > as_of[:10]:
        return "POINT_IN_TIME_VIOLATION"
    return None


def _run(calc_id: str, inputs: dict[str, Any], keys: tuple[str, ...], as_of: str, assumption: str | None = None) -> dict[str, Any]:
    return calculate(calculation_id=calc_id, inputs={key: inputs[key] for key in keys}, as_of=as_of,
                     assumptions=[{"text": assumption}] if assumption else [])


def _scenario(profile: Profile, base: dict[str, Any], as_of: str, assumptions: dict[str, Any]) -> dict[str, Any]:
    missing = [key for key in profile.calculation_inputs if key not in assumptions]
    if missing:
        return {"status":"DATA_UNAVAILABLE", "missing":missing, "epistemic_label":"SCENARIO", "probability":None}
    wrapped = {key: {**base[key], "value": float(assumptions[key])} for key in profile.calculation_inputs}
    result = _run(profile.calculation, wrapped, profile.calculation_inputs, as_of, "Scenario, not reported fact")
    return {"status":result.get("status"), "epistemic_label":"SCENARIO", "assumptions":assumptions,
            "primary_value":result.get("calculated_value"), "probability":None}


def _sensitivity(profile: Profile, inputs: dict[str, Any], as_of: str) -> list[dict[str, Any]]:
    keys = profile.calculation_inputs
    first, second = keys[0], keys[1]
    rows = []
    for a in (.9, 1.0, 1.1):
        for b in (.9, 1.0, 1.1):
            wrapped = {key: dict(inputs[key]) for key in keys}
            wrapped[first]["value"] = float(inputs[first]["value"]) * a
            wrapped[second]["value"] = float(inputs[second]["value"]) * b
            result = _run(profile.calculation, wrapped, keys, as_of, "Sensitivity, not forecast")
            rows.append({first:wrapped[first]["value"], second:wrapped[second]["value"],
                         "primary_value":result.get("calculated_value"), "status":result.get("status")})
    return rows


def _expectation_label(implied: float, expected: float, *, higher_is_stretched: bool = True) -> str:
    if expected == 0:
        return "DATA_INSUFFICIENT"
    ratio = implied / expected
    if higher_is_stretched:
        return "EXPECTATIONS_STRETCHED" if ratio > 1.10 else "EXPECTATIONS_FAVORABLE" if ratio < .90 else "EXPECTATIONS_NEUTRAL"
    return "EXPECTATIONS_FAVORABLE" if ratio > 1.10 else "EXPECTATIONS_STRETCHED" if ratio < .90 else "EXPECTATIONS_NEUTRAL"


def _reverse_expectations(subsector: str, inputs: dict[str, Any], primary_value: float, as_of: str) -> dict[str, Any]:
    if subsector in {"SMALL_FINANCE_BANK","NBFC","HOUSING_FINANCE"}:
        calc = calculate(calculation_id="BANK_IMPLIED_ROE", inputs={
            "price_to_book":{**inputs["market_price"],"value":primary_value},
            "cost_of_equity":inputs["cost_of_equity"],"growth":inputs["growth"]}, as_of=as_of)
        implied = calc.get("calculated_value") if calc.get("status")=="SUCCESS" else None
        return {"classification":_expectation_label(float(implied),float(inputs["roe"]["value"])) if implied is not None else "DATA_INSUFFICIENT",
                "implied_roe":implied,"agi_roe_expectation":inputs["roe"]["value"],"calculation":calc}
    if subsector in {"LIFE_INSURANCE","GENERAL_INSURANCE","HEALTH_INSURANCE","ASSET_MANAGEMENT","BROKER","EXCHANGE_INFRASTRUCTURE"}:
        pe = calculate(calculation_id="FINANCIAL_PRICE_TO_EARNINGS", inputs={"market_price":inputs["market_price"],"normalized_eps":inputs["normalized_eps"]},as_of=as_of)
        calc = calculate(calculation_id="IMPLIED_GROWTH_FROM_PE", inputs={
            "cost_of_equity":inputs["cost_of_equity"],"payout_ratio":inputs["payout_ratio"],
            "price_to_earnings":{**inputs["market_price"],"value":pe.get("calculated_value")}},as_of=as_of) if pe.get("status")=="SUCCESS" else pe
        implied=calc.get("calculated_value") if calc.get("status")=="SUCCESS" else None
        return {"classification":_expectation_label(float(implied),float(inputs["agi_growth_expectation"]["value"])) if implied is not None else "DATA_INSUFFICIENT",
                "implied_growth":implied,"agi_growth_expectation":inputs["agi_growth_expectation"]["value"],"current_pe":pe.get("calculated_value"),"calculation":calc}
    if subsector in {"FINTECH_PAYMENTS","PAYMENTS_BANK"}:
        calc=calculate(calculation_id="IMPLIED_GROWTH_FROM_MULTIPLE",inputs={
            "current_multiple":{**inputs["enterprise_value"],"value":primary_value},
            "terminal_multiple":inputs["terminal_multiple"],"horizon_years":inputs["horizon_years"]},as_of=as_of)
        implied=calc.get("calculated_value") if calc.get("status")=="SUCCESS" else None
        return {"classification":_expectation_label(float(implied),float(inputs["agi_growth_expectation"]["value"])) if implied is not None else "DATA_INSUFFICIENT",
                "implied_growth":implied,"agi_growth_expectation":inputs["agi_growth_expectation"]["value"],"calculation":calc}
    if subsector=="DIVERSIFIED_FINANCIALS":
        calc=calculate(calculation_id="IMPLIED_HOLDCO_DISCOUNT",inputs={key:inputs[key] for key in ("market_cap","segment_1_value","segment_2_value","segment_3_value","net_debt")},as_of=as_of)
        implied=calc.get("calculated_value") if calc.get("status")=="SUCCESS" else None
        return {"classification":_expectation_label(float(implied),float(inputs["holdco_discount"]["value"]),higher_is_stretched=False) if implied is not None else "DATA_INSUFFICIENT",
                "implied_holdco_discount":implied,"agi_holdco_discount":inputs["holdco_discount"]["value"],"calculation":calc}
    return {"classification":"DATA_INSUFFICIENT"}


def evaluate_financial_subsector(*, company: dict[str, Any], inputs: dict[str, Any], as_of: str,
                                 peers: list[dict[str, Any]] | None = None,
                                 history: list[dict[str, Any]] | None = None,
                                 scenarios: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    try:
        date.fromisoformat(str(as_of)[:10])
    except (TypeError, ValueError):
        return {"status":"DATA_UNAVAILABLE", "reason":"A valid ISO as-of date is required.", "execution_eligible":False, "certified":False}
    classification = classify_financial_subsector(company)
    subsector = classification.get("subsector")
    profile = PROFILES.get(str(subsector))
    model = MODELS.get(str(subsector))
    if profile is None or model is None:
        return {"status":"CLASSIFICATION_UNAVAILABLE", "classification":classification, "execution_eligible":False, "certified":False}
    issues = {key: issue for key in profile.required if (issue := _issue(inputs.get(key), as_of))}
    if issues:
        status = "POINT_IN_TIME_VIOLATION" if "POINT_IN_TIME_VIOLATION" in issues.values() else "DATA_UNAVAILABLE"
        return {"status":status, "input_issues":issues, "classification":classification, "execution_eligible":False, "certified":False}
    risks = []
    for key in profile.positive:
        if float(inputs[key]["value"]) <= 0: risks.append(f"{key.upper()}_MUST_BE_POSITIVE")
    for key in profile.risk_ratios:
        if not 0 <= float(inputs[key]["value"]) <= 1: risks.append(f"{key.upper()}_OUT_OF_DECIMAL_RANGE")
    if subsector in {"GENERAL_INSURANCE","HEALTH_INSURANCE"}:
        combined = float(inputs["claims_ratio"]["value"]) + float(inputs["expense_ratio"]["value"])
        if combined > 3: risks.append("COMBINED_RATIO_IMPLAUSIBLE")
    if subsector == "DIVERSIFIED_FINANCIALS" and float(inputs["holdco_discount"]["value"]) > .75:
        risks.append("HOLDCO_DISCOUNT_REQUIRES_EXCEPTIONAL_EVIDENCE")
    if risks:
        return {"status":"VALIDATION_FAILED", "risk_flags":risks, "classification":classification, "execution_eligible":False, "certified":False}
    primary = _run(profile.calculation, inputs, profile.calculation_inputs, as_of)
    if primary.get("status") != "SUCCESS":
        return {"status":"VALUATION_UNAVAILABLE", "calculation":primary, "classification":classification, "execution_eligible":False, "certified":False}
    value = float(primary["calculated_value"])
    expectations = _reverse_expectations(str(subsector), inputs, value, as_of)
    peer_values = [float(row["primary_multiple"]) for row in (peers or [])
                   if row.get("subsector") == subsector and isinstance(row.get("primary_multiple"),(int,float))]
    historical = [float(row["primary_multiple"]) for row in (history or [])
                  if isinstance(row.get("primary_multiple"),(int,float)) and str(row.get("available_at") or "")[:10] <= as_of[:10]]
    scenario_rows = {name:_scenario(profile, inputs, as_of, (scenarios or {}).get(name) or {}) for name in ("BEAR","BASE","BULL")}
    causal = ask_context(entity=str(company.get("symbol") or company.get("company_id") or subsector),
                         question=f"What drives sustainable value in {model.sector_name}?",
                         industry=model.sector_name, analysis_as_of=as_of)
    evidence_gaps = [name for name, present in (("peer_valuation",bool(peer_values)),("historical_valuation",bool(historical))) if not present]
    return {"status":"OPERATIONAL_NOT_CERTIFIED", "company_id":company.get("symbol") or company.get("company_id"),
        "as_of":as_of, "classification":classification, "model":model.to_dict(),
        "valuation":{"primary_method":profile.calculation, "primary_value":value,
                     "peer_median":median(peer_values) if peer_values else None,
                     "historical_median":median(historical) if historical else None},
        "market_expectations":expectations,
        "scenarios":scenario_rows, "sensitivity":{"variables":list(profile.calculation_inputs[:2]), "grid":_sensitivity(profile, inputs, as_of)},
        "causal_context":causal.get("causal_research",{}), "risk_flags":[], "monitoring":list(model.monitoring_variables),
        "provenance":{key:{k:inputs[key].get(k) for k in ("source_id","available_at","period","unit","currency")} for key in profile.required},
        "confidence":"MEDIUM" if peer_values and historical else "LOW", "evidence_gaps":evidence_gaps,
        "calculation":primary, "investment_attractiveness":"RESEARCH_ONLY", "execution_eligible":False, "certified":False}
