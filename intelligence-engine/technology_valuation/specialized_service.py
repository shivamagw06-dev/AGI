"""Shared fail-closed evaluator for reviewed specialized Technology curricula."""
from __future__ import annotations
from datetime import date
from statistics import median
from typing import Any
from causal_research_engine.service import ask_context
from financial_engine import calculate
from technology_valuation.specialized_model import SPECIALIZED_MODELS

COMMON=("enterprise_value","revenue","ebitda","gross_profit","fcf","capex","net_debt","terminal_ev_ebitda","horizon_years","target_ev_ebitda","scenario_revenue_growth","scenario_ebitda_margin")
FAMILY_FIELDS={
"ERD_TECHNOLOGY_SERVICES":("opening_revenue","closing_revenue","order_intake","opening_engineers","closing_engineers","utilization","embedded_revenue","client_concentration"),
"HARDWARE_ELECTRONICS":("opening_units","closing_units","inventory","cogs","local_value_add","order_book"),
"DATA_CENTRES":("operational_mw","contracted_mw","pipeline_mw","preleased_mw","facility_power","it_power","added_mw"),
"FINTECH_PAYMENTS":("opening_tpv","closing_tpv","tpv","transactions","active_merchants","contribution_profit","fraud_losses"),
"CYBERSECURITY_CLOUD":("opening_arr","closing_arr","retained_expanded_arr","segment_arr","customer_concentration","rpo","rnd"),
}
REQUIRED_SPECIALIZED={key:COMMON+fields for key,fields in FAMILY_FIELDS.items()}
def _issue(item,as_of):
    if not isinstance(item,dict) or not isinstance(item.get("value"),(int,float)) or isinstance(item.get("value"),bool):return "MISSING_OR_INVALID"
    if not item.get("source_id") or not item.get("period") or not item.get("available_at"):return "PROVENANCE_REQUIRED"
    if str(item["available_at"])[:10]>as_of[:10]:return "POINT_IN_TIME_VIOLATION"
def _wrapped(source,value):return {**source,"value":float(value)}
def _ratio(inputs,as_of,numerator,denominator):return calculate(calculation_id="TECH_SPECIALIZED_RATIO",inputs={"numerator":inputs[numerator],"denominator":inputs[denominator]},as_of=as_of)
def _growth(inputs,as_of,opening,closing):return calculate(calculation_id="TECH_SPECIALIZED_GROWTH",inputs={"opening":inputs[opening],"closing":inputs[closing]},as_of=as_of)
def _scenario(inputs,as_of,assumptions):
    required=("revenue_growth","ebitda_margin","target_ev_ebitda");missing=[k for k in required if k not in assumptions]
    if missing:return {"status":"DATA_UNAVAILABLE","missing":missing,"epistemic_label":"SCENARIO","probability":None}
    payload={"revenue":inputs["revenue"],"revenue_growth":_wrapped(inputs["scenario_revenue_growth"],assumptions["revenue_growth"]),"ebitda_margin":_wrapped(inputs["scenario_ebitda_margin"],assumptions["ebitda_margin"]),"target_ev_ebitda":_wrapped(inputs["target_ev_ebitda"],assumptions["target_ev_ebitda"]),"net_debt":inputs["net_debt"]}
    result=calculate(calculation_id="TECH_SPECIALIZED_SCENARIO_EQUITY",inputs=payload,as_of=as_of,assumptions=[{"text":"Specialized technology scenario, not fact"}])
    return {"status":result.get("status"),"epistemic_label":"SCENARIO","assumptions":assumptions,"equity_value":result.get("calculated_value"),"probability":None,"calculation":result}
def _family_kpis(family,inputs,as_of):
    common={"ebitda_margin":_ratio(inputs,as_of,"ebitda","revenue"),"gross_margin":_ratio(inputs,as_of,"gross_profit","revenue"),"fcf_margin":_ratio(inputs,as_of,"fcf","revenue"),"capex_intensity":_ratio(inputs,as_of,"capex","revenue")}
    if family=="ERD_TECHNOLOGY_SERVICES": extra={"revenue_growth":_growth(inputs,as_of,"opening_revenue","closing_revenue"),"book_to_bill":_ratio(inputs,as_of,"order_intake","revenue"),"revenue_per_engineer":calculate(calculation_id="TECH_SPECIALIZED_RATIO",inputs={"numerator":inputs["revenue"],"denominator":_wrapped(inputs["opening_engineers"],(inputs["opening_engineers"]["value"]+inputs["closing_engineers"]["value"])/2)},as_of=as_of),"embedded_mix":_ratio(inputs,as_of,"embedded_revenue","revenue")};reported={"utilization":inputs["utilization"]["value"],"client_concentration":inputs["client_concentration"]["value"]}
    elif family=="HARDWARE_ELECTRONICS": extra={"unit_growth":_growth(inputs,as_of,"opening_units","closing_units"),"asp":_ratio(inputs,as_of,"revenue","closing_units"),"inventory_turns":_ratio(inputs,as_of,"cogs","inventory"),"local_value_add":_ratio(inputs,as_of,"local_value_add","revenue"),"order_book_ratio":_ratio(inputs,as_of,"order_book","revenue")};reported={}
    elif family=="DATA_CENTRES": extra={"occupancy":_ratio(inputs,as_of,"contracted_mw","operational_mw"),"pue":_ratio(inputs,as_of,"facility_power","it_power"),"preleased_ratio":_ratio(inputs,as_of,"preleased_mw","pipeline_mw"),"capex_per_mw":_ratio(inputs,as_of,"capex","added_mw"),"revenue_per_mw":_ratio(inputs,as_of,"revenue","contracted_mw"),"net_debt_ebitda":_ratio(inputs,as_of,"net_debt","ebitda")};reported={"operational_mw":inputs["operational_mw"]["value"]}
    elif family=="FINTECH_PAYMENTS": extra={"tpv_growth":_growth(inputs,as_of,"opening_tpv","closing_tpv"),"take_rate":_ratio(inputs,as_of,"revenue","tpv"),"transactions_per_merchant":_ratio(inputs,as_of,"transactions","active_merchants"),"revenue_per_transaction":_ratio(inputs,as_of,"revenue","transactions"),"contribution_margin":_ratio(inputs,as_of,"contribution_profit","revenue"),"fraud_loss_rate":_ratio(inputs,as_of,"fraud_losses","tpv")};reported={"active_merchants":inputs["active_merchants"]["value"]}
    else: extra={"arr_growth":_growth(inputs,as_of,"opening_arr","closing_arr"),"nrr":_ratio(inputs,as_of,"retained_expanded_arr","opening_arr"),"security_arr_mix":_ratio(inputs,as_of,"segment_arr","closing_arr"),"rpo_coverage":_ratio(inputs,as_of,"rpo","closing_arr"),"rnd_intensity":_ratio(inputs,as_of,"rnd","revenue")};reported={"customer_concentration":inputs["customer_concentration"]["value"]}
    calculations={**common,**extra};return calculations,reported
def evaluate_specialized(*,family:str,company:dict[str,Any],inputs:dict[str,Any],as_of:str,peers:list[dict[str,Any]]|None=None,history:list[dict[str,Any]]|None=None,scenarios:dict[str,dict[str,Any]]|None=None)->dict[str,Any]:
    model=SPECIALIZED_MODELS.get(family)
    if model is None:return {"status":"CLASSIFICATION_UNAVAILABLE","execution_eligible":False,"certified":False}
    try:date.fromisoformat(str(as_of)[:10])
    except (TypeError,ValueError):return {"status":"DATA_UNAVAILABLE","execution_eligible":False,"certified":False}
    required=REQUIRED_SPECIALIZED[family];issues={k:v for k in required if (v:=_issue(inputs.get(k),as_of))}
    if issues:return {"status":"POINT_IN_TIME_VIOLATION" if "POINT_IN_TIME_VIOLATION" in issues.values() else "DATA_UNAVAILABLE","input_issues":issues,"execution_eligible":False,"certified":False}
    positive=[k for k in required if k not in {"net_debt","scenario_revenue_growth","client_concentration","customer_concentration"}];risks=[f"{k.upper()}_MUST_BE_POSITIVE" for k in positive if float(inputs[k]["value"])<=0]
    decimals=[k for k in ("scenario_ebitda_margin","utilization","client_concentration","customer_concentration") if k in inputs]
    risks += [f"{k.upper()}_OUT_OF_RANGE" for k in decimals if not 0<=float(inputs[k]["value"])<=1]
    if family=="DATA_CENTRES" and inputs["contracted_mw"]["value"]>inputs["operational_mw"]["value"]:risks.append("CONTRACTED_MW_EXCEEDS_OPERATIONAL_MW")
    if risks:return {"status":"VALIDATION_FAILED","risk_flags":risks,"execution_eligible":False,"certified":False}
    calculations,reported=_family_kpis(family,inputs,as_of);ev_sales=calculate(calculation_id="EV_SALES",inputs={k:inputs[k] for k in ("enterprise_value","revenue")},as_of=as_of);ev_ebitda=calculate(calculation_id="EV_EBITDA",inputs={k:inputs[k] for k in ("enterprise_value","ebitda")},as_of=as_of)
    if any(x.get("status")!="SUCCESS" for x in [*calculations.values(),ev_sales,ev_ebitda]):return {"status":"VALUATION_UNAVAILABLE","execution_eligible":False,"certified":False}
    kpis={k:v["calculated_value"] for k,v in calculations.items()}|reported;current=float(ev_ebitda["calculated_value"]);implied=calculate(calculation_id="IMPLIED_GROWTH_FROM_MULTIPLE",inputs={"current_multiple":_wrapped(inputs["enterprise_value"],current),"terminal_multiple":inputs["terminal_ev_ebitda"],"horizon_years":inputs["horizon_years"]},as_of=as_of)
    peer=[float(x["ev_ebitda"]) for x in (peers or []) if isinstance(x.get("ev_ebitda"),(int,float))];hist=[float(x["ev_ebitda"]) for x in (history or []) if isinstance(x.get("ev_ebitda"),(int,float)) and str(x.get("available_at") or "")[:10]<=as_of[:10]];scenario_rows={n:_scenario(inputs,as_of,(scenarios or {}).get(n) or {}) for n in ("BEAR","BASE","BULL")};growth=float(inputs["scenario_revenue_growth"]["value"]);margin=float(inputs["scenario_ebitda_margin"]["value"]);target=float(inputs["target_ev_ebitda"]["value"]);grid=[{"revenue_growth":g,"ebitda_margin":m,"equity_value":_scenario(inputs,as_of,{"revenue_growth":g,"ebitda_margin":m,"target_ev_ebitda":target}).get("equity_value")} for g in (max(-.99,growth-.05),growth,growth+.05) for m in (max(0,margin-.05),margin,min(1,margin+.05))]
    symbol=str(company.get("symbol") or family);context=ask_context(entity=symbol,question=f"What drives sustainable value for {symbol} in {model.sector_name}?",industry=model.sector_name,analysis_as_of=as_of)
    return {"status":"OPERATIONAL_NOT_CERTIFIED","lifecycle_status":"OPERATIONAL","company_id":symbol,"as_of":as_of,"model":model.to_dict(),"business_economics":{"revenue_model":model.economic_structure,"competitive_advantage":{"status":"EVIDENCE_REQUIRED","moat_claim_allowed":False},"ai_analysis":{"benefit":"productivity, automation and new demand","risk":"pricing compression, compute cost and disruption","net_impact":"EVIDENCE_REQUIRED"}},"kpis":kpis,"valuation":{"primary_method":"EV_EBITDA","current_ev_ebitda":current,"current_ev_sales":ev_sales["calculated_value"],"peer_median_ev_ebitda":median(peer) if peer else None,"historical_median_ev_ebitda":median(hist) if hist else None},"market_expectations":{"classification":"SCENARIO_DEPENDENT","implied_growth":implied.get("calculated_value"),"calculation":implied},"scenarios":scenario_rows,"sensitivity":{"variables":["revenue_growth","ebitda_margin"],"grid":grid},"causal_context":{"templates":[{"cause":x,"effect":y,"direction":d,"epistemic_label":"HYPOTHESIS","status":"PROPOSED","counter_effects":[{"description":c}]} for x,y,d,c in ((model.revenue_drivers[0],"revenue","POSITIVE",model.valuation_risks[0]),("revenue","ebitda","POSITIVE",model.cost_drivers[0]),("ebitda","fcf","POSITIVE","reinvestment and working capital"),("fcf","equity_value","POSITIVE","valuation and execution risk"))],"existing_graph":context.get("causal_research",{}),"status":"PROPOSED_NOT_TRUSTED"},"monitoring":list(model.monitoring_variables),"provenance":{k:{q:inputs[k].get(q) for q in ("source_id","available_at","period","unit","currency")} for k in required},"evidence_gaps":[n for n,p in (("peer_valuation",bool(peer)),("historical_valuation",bool(hist)),("trusted_causal_evidence",False)) if not p],"confidence":"MEDIUM" if peer and hist else "LOW","investment_attractiveness":"RESEARCH_ONLY","execution_eligible":False,"certified":False,"investment_certified":False}
