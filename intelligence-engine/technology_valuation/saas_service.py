"""Fail-closed Phase 2B Software/SaaS evaluator."""
from __future__ import annotations
from datetime import date
from statistics import median
from typing import Any
from causal_research_engine.service import ask_context
from causal_research_engine.technology_templates import software_saas_templates
from financial_engine import calculate
from technology_valuation.saas_model import SOFTWARE_SAAS_MODEL

REQUIRED_SAAS_INPUTS=("enterprise_value","arr","opening_arr","closing_arr","churned_arr","contraction_arr","expansion_arr",
    "gross_profit","revenue","customer_acquisition_cost","monthly_revenue_per_new_customer","gross_margin",
    "annual_revenue_per_customer","annual_logo_churn","fcf","terminal_ev_arr","horizon_years","agi_arr_growth_expectation","target_ev_arr")


def _issue(item:Any,as_of:str)->str|None:
    if not isinstance(item,dict) or not isinstance(item.get("value"),(int,float)) or isinstance(item.get("value"),bool): return "MISSING_OR_INVALID"
    if not item.get("source_id") or not item.get("period") or not item.get("available_at"): return "PROVENANCE_REQUIRED"
    if str(item["available_at"])[:10]>as_of[:10]: return "POINT_IN_TIME_VIOLATION"
    return None


def _calc(calc_id,inputs,keys,as_of,assumption=None):
    return calculate(calculation_id=calc_id,inputs={k:inputs[k] for k in keys},as_of=as_of,assumptions=[{"text":assumption}] if assumption else [])


def _scenario(inputs,as_of,assumptions):
    if not all(key in assumptions for key in ("arr_growth","target_ev_arr")):
        return {"status":"DATA_UNAVAILABLE","missing":[k for k in ("arr_growth","target_ev_arr") if k not in assumptions],"epistemic_label":"SCENARIO","probability":None}
    result=calculate(calculation_id="SAAS_SCENARIO_EV",inputs={"arr":inputs["arr"],"arr_growth":{**inputs["arr"],"value":float(assumptions["arr_growth"])},"target_ev_arr":{**inputs["target_ev_arr"],"value":float(assumptions["target_ev_arr"])}},as_of=as_of,assumptions=[{"text":"Scenario, not reported fact"}])
    return {"status":result.get("status"),"epistemic_label":"SCENARIO","assumptions":assumptions,"enterprise_value":result.get("calculated_value"),"probability":None,"calculation":result}


def _sensitivity(inputs,as_of):
    growth=float(inputs["agi_arr_growth_expectation"]["value"]); multiple=float(inputs["target_ev_arr"]["value"]); rows=[]
    for g in (growth-.05,growth,growth+.05):
        for m in (multiple*.8,multiple,multiple*1.2):
            result=_scenario(inputs,as_of,{"arr_growth":g,"target_ev_arr":m})
            rows.append({"arr_growth":g,"target_ev_arr":m,"enterprise_value":result.get("enterprise_value"),"status":result.get("status")})
    return rows


def evaluate_software_saas(*,company:dict[str,Any],inputs:dict[str,Any],as_of:str,peers:list[dict[str,Any]]|None=None,
                           history:list[dict[str,Any]]|None=None,scenarios:dict[str,dict[str,Any]]|None=None)->dict[str,Any]:
    try: date.fromisoformat(str(as_of)[:10])
    except (TypeError,ValueError): return {"status":"DATA_UNAVAILABLE","reason":"A valid ISO as-of date is required.","execution_eligible":False,"certified":False}
    issues={key:issue for key in REQUIRED_SAAS_INPUTS if (issue:=_issue(inputs.get(key),as_of))}
    if issues:
        status="POINT_IN_TIME_VIOLATION" if "POINT_IN_TIME_VIOLATION" in issues.values() else "DATA_UNAVAILABLE"
        return {"status":status,"input_issues":issues,"execution_eligible":False,"certified":False}
    positive=("enterprise_value","arr","opening_arr","closing_arr","gross_profit","revenue","monthly_revenue_per_new_customer","gross_margin","annual_revenue_per_customer","annual_logo_churn","terminal_ev_arr","horizon_years","target_ev_arr")
    nonnegative=("churned_arr","contraction_arr","expansion_arr","customer_acquisition_cost")
    risks=[f"{k.upper()}_MUST_BE_POSITIVE" for k in positive if float(inputs[k]["value"])<=0]
    risks.extend(f"{k.upper()}_MUST_BE_NONNEGATIVE" for k in nonnegative if float(inputs[k]["value"])<0)
    for k in ("gross_margin","annual_logo_churn"):
        if not 0<float(inputs[k]["value"])<=1: risks.append(f"{k.upper()}_OUT_OF_RANGE")
    if float(inputs["churned_arr"]["value"])+float(inputs["contraction_arr"]["value"])>float(inputs["opening_arr"]["value"]): risks.append("RETENTION_BRIDGE_EXCEEDS_OPENING_ARR")
    if risks: return {"status":"VALIDATION_FAILED","risk_flags":risks,"execution_eligible":False,"certified":False}
    specs=(("ev_arr","EV_ARR",("enterprise_value","arr")),("ev_gross_profit","EV_GROSS_PROFIT",("enterprise_value","gross_profit")),
        ("ev_sales","EV_SALES",("enterprise_value","revenue")),("arr_growth","ARR_GROWTH",("opening_arr","closing_arr")),
        ("nrr","NET_REVENUE_RETENTION",("opening_arr","churned_arr","contraction_arr","expansion_arr")),
        ("grr","GROSS_REVENUE_RETENTION",("opening_arr","churned_arr","contraction_arr")),
        ("cac_payback_months","CAC_PAYBACK_MONTHS",("customer_acquisition_cost","monthly_revenue_per_new_customer","gross_margin")),
        ("ltv","CUSTOMER_LTV",("annual_revenue_per_customer","gross_margin","annual_logo_churn")),
        ("fcf_margin","FCF_MARGIN",("fcf","revenue")))
    calculations={name:_calc(cid,inputs,keys,as_of) for name,cid,keys in specs}
    if any(row.get("status")!="SUCCESS" for row in calculations.values()): return {"status":"VALUATION_UNAVAILABLE","calculations":calculations,"execution_eligible":False,"certified":False}
    ltv_cac=calculate(calculation_id="LTV_CAC",inputs={"customer_lifetime_value":{**inputs["annual_revenue_per_customer"],"value":calculations["ltv"]["calculated_value"]},"customer_acquisition_cost":inputs["customer_acquisition_cost"]},as_of=as_of)
    rule40=calculate(calculation_id="RULE_OF_40",inputs={"arr_growth":{**inputs["opening_arr"],"value":calculations["arr_growth"]["calculated_value"]},"fcf_margin":{**inputs["fcf"],"value":calculations["fcf_margin"]["calculated_value"]}},as_of=as_of)
    current=float(calculations["ev_arr"]["calculated_value"])
    selected_method="EV_ARR"; selected_value=current; selector_reason="Recurring economics are evidenced; EV/ARR still requires retention and gross-margin context."
    if str(company.get("business_maturity") or "").upper()=="MATURE_PROFITABLE":
        optional_issues={key:_issue(inputs.get(key),as_of) for key in ("market_price","normalized_eps")}
        if not any(optional_issues.values()) and float(inputs["normalized_eps"]["value"])>0:
            pe=_calc("TECH_PRICE_TO_EARNINGS",inputs,("market_price","normalized_eps"),as_of)
            if pe.get("status")=="SUCCESS":
                selected_method="TECH_PRICE_TO_EARNINGS"; selected_value=pe["calculated_value"]
                selector_reason="Company is explicitly classified mature and profitable; normalized P/E is primary while recurring-unit economics remain cross-checks."
    implied=calculate(calculation_id="IMPLIED_GROWTH_FROM_MULTIPLE",inputs={"current_multiple":{**inputs["enterprise_value"],"value":current},"terminal_multiple":inputs["terminal_ev_arr"],"horizon_years":inputs["horizon_years"]},as_of=as_of)
    implied_growth=implied.get("calculated_value") if implied.get("status")=="SUCCESS" else None; expected=float(inputs["agi_arr_growth_expectation"]["value"])
    label="DATA_INSUFFICIENT" if implied_growth is None or expected==0 else "EXPECTATIONS_STRETCHED" if implied_growth/expected>1.10 else "EXPECTATIONS_FAVORABLE" if implied_growth/expected<.90 else "EXPECTATIONS_NEUTRAL"
    peer_values=[float(r["ev_arr"]) for r in (peers or []) if isinstance(r.get("ev_arr"),(int,float))]
    historical=[float(r["ev_arr"]) for r in (history or []) if isinstance(r.get("ev_arr"),(int,float)) and str(r.get("available_at") or "")[:10]<=as_of[:10]]
    scenario_rows={name:_scenario(inputs,as_of,(scenarios or {}).get(name) or {}) for name in ("BEAR","BASE","BULL")}
    symbol=str(company.get("symbol") or company.get("company_id") or "SOFTWARE_SAAS")
    graph=ask_context(entity=symbol,question=f"What drives sustainable Software/SaaS value for {symbol}?",industry="Software and SaaS",analysis_as_of=as_of)
    return {"status":"OPERATIONAL_NOT_CERTIFIED","lifecycle_status":"OPERATIONAL","company_id":symbol,"as_of":as_of,"model":SOFTWARE_SAAS_MODEL.to_dict(),
        "business_economics":{"revenue_model":"customers -> ARR -> retention and expansion -> revenue -> gross profit -> operating leverage -> FCF","recurring_revenue_quality":{"status":"EVIDENCE_REQUIRED","contracted_is_not_recurring":True,"recurring_is_not_committed":True},"competitive_advantage":{"status":"EVIDENCE_REQUIRED","moat_claim_allowed":False},"ai_analysis":{"benefit":"product utility and development productivity","risk":"feature commoditization, compute cost and pricing pressure","net_impact":"EVIDENCE_REQUIRED"}},
        "kpis":{name:row["calculated_value"] for name,row in calculations.items()}|{"ltv_cac":ltv_cac.get("calculated_value"),"rule_of_40":rule40.get("calculated_value")},
        "valuation":{"primary_method":selected_method,"primary_value":selected_value,"current_ev_arr":current,"ev_gross_profit":calculations["ev_gross_profit"]["calculated_value"],"ev_sales":calculations["ev_sales"]["calculated_value"],"peer_median_ev_arr":median(peer_values) if peer_values else None,"historical_median_ev_arr":median(historical) if historical else None,"selector_reason":selector_reason},
        "market_expectations":{"classification":label,"implied_arr_growth":implied_growth,"agi_arr_growth_expectation":expected,"calculation":implied},
        "scenarios":scenario_rows,"sensitivity":{"variables":["arr_growth","target_ev_arr"],"grid":_sensitivity(inputs,as_of)},
        "causal_context":{"templates":[r.to_dict() for r in software_saas_templates(symbol)],"existing_graph":graph.get("causal_research",{}),"status":"PROPOSED_NOT_TRUSTED"},
        "monitoring":list(SOFTWARE_SAAS_MODEL.monitoring_variables),"risk_flags":[],"provenance":{key:{k:inputs[key].get(k) for k in ("source_id","available_at","period","unit","currency")} for key in REQUIRED_SAAS_INPUTS},
        "evidence_gaps":[name for name,present in (("peer_valuation",bool(peer_values)),("historical_valuation",bool(historical)),("trusted_causal_evidence",False)) if not present],
        "confidence":"MEDIUM" if peer_values and historical else "LOW","investment_attractiveness":"RESEARCH_ONLY","execution_eligible":False,"certified":False,"investment_certified":False}
