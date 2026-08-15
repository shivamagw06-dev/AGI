"""Fail-closed Phase 2A IT Services valuation evaluator."""
from __future__ import annotations
from datetime import date
from statistics import median
from typing import Any

from causal_research_engine.service import ask_context
from causal_research_engine.technology_templates import it_services_templates
from financial_engine import calculate
from technology_valuation.classification import classify_technology_subsector
from technology_valuation.model import IT_SERVICES_MODEL

REQUIRED_INPUTS = (
    "market_price", "normalized_eps", "enterprise_value", "ebitda", "revenue", "ebit", "fcf",
    "opening_headcount", "closing_headcount", "utilization", "billing_rate", "billable_periods",
    "total_contract_value", "roic", "attrition", "client_concentration", "cost_of_equity",
    "payout_ratio", "agi_growth_expectation", "tax_rate", "shares_outstanding", "target_pe",
)


def _issue(item: Any, as_of: str) -> str | None:
    if not isinstance(item, dict) or not isinstance(item.get("value"), (int, float)) or isinstance(item.get("value"), bool):
        return "MISSING_OR_INVALID"
    if not item.get("source_id") or not item.get("period") or not item.get("available_at"):
        return "PROVENANCE_REQUIRED"
    if str(item["available_at"])[:10] > as_of[:10]:
        return "POINT_IN_TIME_VIOLATION"
    return None


def _calc(calc_id: str, inputs: dict[str, Any], keys: tuple[str, ...], as_of: str, assumption: str | None = None) -> dict[str, Any]:
    return calculate(calculation_id=calc_id, inputs={key:inputs[key] for key in keys}, as_of=as_of,
                     assumptions=[{"text":assumption}] if assumption else [])


def _scenario(inputs: dict[str, Any], as_of: str, assumptions: dict[str, Any]) -> dict[str, Any]:
    keys=("revenue","revenue_growth","ebit_margin","tax_rate","shares_outstanding","target_pe")
    missing=[key for key in keys if key not in assumptions and key not in inputs]
    if missing:
        return {"status":"DATA_UNAVAILABLE","missing":missing,"epistemic_label":"SCENARIO","probability":None}
    wrapped={}
    for key in keys:
        source=inputs.get(key) or inputs["revenue"]
        wrapped[key]={**source,"value":float(assumptions[key])} if key in assumptions else dict(source)
    result=_calc("IT_SERVICES_SCENARIO_PRICE",wrapped,keys,as_of,"Scenario, not reported fact")
    return {"status":result.get("status"),"epistemic_label":"SCENARIO","assumptions":assumptions,
            "price_per_share":result.get("calculated_value"),"probability":None,"calculation":result}


def _sensitivity(inputs: dict[str, Any], as_of: str) -> list[dict[str, Any]]:
    rows=[]
    base_growth=float(inputs["agi_growth_expectation"]["value"])
    base_margin=float(inputs["ebit"]["value"])/float(inputs["revenue"]["value"])
    for growth_delta in (-.02,0,.02):
        for margin_delta in (-.02,0,.02):
            assumptions={"revenue_growth":base_growth+growth_delta,"ebit_margin":base_margin+margin_delta}
            result=_scenario(inputs,as_of,assumptions)
            rows.append({**assumptions,"price_per_share":result.get("price_per_share"),"status":result.get("status")})
    return rows


def _expectation(implied: float | None, expected: float) -> str:
    if implied is None or expected == 0: return "DATA_INSUFFICIENT"
    ratio=implied/expected
    return "EXPECTATIONS_STRETCHED" if ratio>1.10 else "EXPECTATIONS_FAVORABLE" if ratio<.90 else "EXPECTATIONS_NEUTRAL"


def _evaluate_it_services(*, company: dict[str, Any], inputs: dict[str, Any], as_of: str,
                                peers: list[dict[str, Any]] | None = None,
                                history: list[dict[str, Any]] | None = None,
                                scenarios: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    try: date.fromisoformat(str(as_of)[:10])
    except (TypeError,ValueError):
        return {"status":"DATA_UNAVAILABLE","reason":"A valid ISO as-of date is required.","execution_eligible":False,"certified":False}
    classification=classify_technology_subsector(company)
    if classification.get("subsector")!="IT_SERVICES":
        return {"status":"CLASSIFICATION_UNAVAILABLE","classification":classification,"execution_eligible":False,"certified":False}
    issues={key:issue for key in REQUIRED_INPUTS if (issue:=_issue(inputs.get(key),as_of))}
    if issues:
        status="POINT_IN_TIME_VIOLATION" if "POINT_IN_TIME_VIOLATION" in issues.values() else "DATA_UNAVAILABLE"
        return {"status":status,"input_issues":issues,"classification":classification,"execution_eligible":False,"certified":False}
    positive=("market_price","normalized_eps","enterprise_value","ebitda","revenue","opening_headcount","closing_headcount","billing_rate","billable_periods","total_contract_value","shares_outstanding","target_pe")
    ratios=("utilization","roic","attrition","client_concentration","cost_of_equity","payout_ratio","agi_growth_expectation","tax_rate")
    risks=[f"{key.upper()}_MUST_BE_POSITIVE" for key in positive if float(inputs[key]["value"])<=0]
    risks.extend(f"{key.upper()}_OUT_OF_DECIMAL_RANGE" for key in ratios if not 0<=float(inputs[key]["value"])<=1)
    if risks:
        return {"status":"VALIDATION_FAILED","risk_flags":risks,"classification":classification,"execution_eligible":False,"certified":False}
    current_pe=_calc("TECH_PRICE_TO_EARNINGS",inputs,("market_price","normalized_eps"),as_of)
    ev_ebitda=_calc("EV_EBITDA",inputs,("enterprise_value","ebitda"),as_of)
    rev_employee=_calc("REVENUE_PER_EMPLOYEE",inputs,("revenue","opening_headcount","closing_headcount"),as_of)
    book_bill=_calc("BOOK_TO_BILL",inputs,("total_contract_value","revenue"),as_of)
    ebit_margin=_calc("EBIT_MARGIN",inputs,("ebit","revenue"),as_of)
    fcf_margin=_calc("FCF_MARGIN",inputs,("fcf","revenue"),as_of)
    capacity=_calc("UTILIZATION_REVENUE_CAPACITY",inputs,("opening_headcount","closing_headcount","utilization","billing_rate","billable_periods"),as_of,"Capacity bridge")
    calculations=(current_pe,ev_ebitda,rev_employee,book_bill,ebit_margin,fcf_margin,capacity)
    if any(row.get("status")!="SUCCESS" for row in calculations):
        return {"status":"VALUATION_UNAVAILABLE","calculations":calculations,"classification":classification,"execution_eligible":False,"certified":False}
    implied=calculate(calculation_id="IMPLIED_GROWTH_FROM_PE",inputs={"cost_of_equity":inputs["cost_of_equity"],"payout_ratio":inputs["payout_ratio"],"price_to_earnings":{**inputs["market_price"],"value":current_pe["calculated_value"]}},as_of=as_of)
    implied_growth=implied.get("calculated_value") if implied.get("status")=="SUCCESS" else None
    peer_values=[float(row["pe"]) for row in (peers or []) if row.get("subsector")=="IT_SERVICES" and isinstance(row.get("pe"),(int,float))]
    historical=[float(row["pe"]) for row in (history or []) if isinstance(row.get("pe"),(int,float)) and str(row.get("available_at") or "")[:10]<=as_of[:10]]
    scenario_rows={name:_scenario(inputs,as_of,(scenarios or {}).get(name) or {}) for name in ("BEAR","BASE","BULL")}
    symbol=str(company.get("symbol") or company.get("company_id") or "IT_SERVICES")
    generic=ask_context(entity=symbol,question=f"What drives sustainable value in IT Services for {symbol}?",industry="IT Services",analysis_as_of=as_of)
    templates=[row.to_dict() for row in it_services_templates(symbol)]
    return {"status":"OPERATIONAL_NOT_CERTIFIED","lifecycle_status":"OPERATIONAL","company_id":symbol,"as_of":as_of,
        "classification":classification,"model":IT_SERVICES_MODEL.to_dict(),
        "business_economics":{"revenue_model":"headcount x utilization x billing rate, reconciled to contracts and mix","revenue_types":["project","managed_service","transactional","recurring contract"],
            "competitive_advantage":{"status":"EVIDENCE_REQUIRED","candidate_mechanisms":["delivery scale","client relationships","switching costs","talent and domain expertise"],"moat_claim_allowed":False},
            "ai_analysis":{"benefit":"delivery productivity and new demand","risk":"hours compression, pricing pressure and cannibalization","net_impact":"EVIDENCE_REQUIRED"}},
        "kpis":{"revenue_per_employee":rev_employee["calculated_value"],"book_to_bill":book_bill["calculated_value"],"ebit_margin":ebit_margin["calculated_value"],"fcf_margin":fcf_margin["calculated_value"],"utilization_revenue_capacity":capacity["calculated_value"]},
        "valuation":{"primary_method":"TECH_PRICE_TO_EARNINGS","current_pe":current_pe["calculated_value"],"ev_ebitda":ev_ebitda["calculated_value"],"peer_median_pe":median(peer_values) if peer_values else None,"historical_median_pe":median(historical) if historical else None},
        "market_expectations":{"classification":_expectation(implied_growth,float(inputs["agi_growth_expectation"]["value"])),"implied_growth":implied_growth,"agi_growth_expectation":inputs["agi_growth_expectation"]["value"],"calculation":implied},
        "scenarios":scenario_rows,"sensitivity":{"variables":["revenue_growth","ebit_margin"],"grid":_sensitivity(inputs,as_of)},
        "causal_context":{"templates":templates,"existing_graph":generic.get("causal_research",{}),"status":"PROPOSED_NOT_TRUSTED"},
        "monitoring":list(IT_SERVICES_MODEL.monitoring_variables),"risk_flags":[],
        "provenance":{key:{k:inputs[key].get(k) for k in ("source_id","available_at","period","unit","currency")} for key in REQUIRED_INPUTS},
        "evidence_gaps":[name for name,present in (("peer_valuation",bool(peer_values)),("historical_valuation",bool(historical)),("trusted_causal_evidence",False)) if not present],
        "confidence":"MEDIUM" if peer_values and historical else "LOW","investment_attractiveness":"RESEARCH_ONLY",
        "execution_eligible":False,"certified":False,"investment_certified":False}


def evaluate_technology_company(*, company: dict[str, Any], inputs: dict[str, Any], as_of: str,
                                peers: list[dict[str, Any]] | None = None,
                                history: list[dict[str, Any]] | None = None,
                                scenarios: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """Single Technology entry point; classification selects the reviewed model."""
    classification=classify_technology_subsector(company)
    if classification.get("model_family")=="SOFTWARE_SAAS":
        from technology_valuation.saas_service import evaluate_software_saas
        return {**evaluate_software_saas(company=company,inputs=inputs,as_of=as_of,peers=peers,history=history,scenarios=scenarios),"classification":classification}
    return _evaluate_it_services(company=company,inputs=inputs,as_of=as_of,peers=peers,history=history,scenarios=scenarios)
