"""Fail-closed Phase 2C Internet Platform and Marketplace evaluator."""
from __future__ import annotations
from datetime import date
from statistics import median
from typing import Any
from causal_research_engine.service import ask_context
from causal_research_engine.technology_templates import platform_marketplace_templates
from financial_engine import calculate
from technology_valuation.platform_model import PLATFORM_MODEL

REQUIRED_PLATFORM_INPUTS=("enterprise_value","gmv","opening_gmv","closing_gmv","revenue","gross_profit","orders","active_buyers","active_sellers","contribution_profit","sales_marketing_spend","new_customers","repeat_rate","seller_concentration","refund_cancellation_rate","fcf","terminal_ev_revenue","horizon_years","agi_gmv_growth_expectation","target_ev_revenue")

def _issue(item:Any,as_of:str)->str|None:
    if not isinstance(item,dict) or not isinstance(item.get("value"),(int,float)) or isinstance(item.get("value"),bool): return "MISSING_OR_INVALID"
    if not item.get("source_id") or not item.get("period") or not item.get("available_at"): return "PROVENANCE_REQUIRED"
    if str(item["available_at"])[:10]>as_of[:10]: return "POINT_IN_TIME_VIOLATION"
    return None

def _calc(cid,inputs,keys,as_of): return calculate(calculation_id=cid,inputs={k:inputs[k] for k in keys},as_of=as_of)

def _scenario(inputs,as_of,a):
    missing=[k for k in ("gmv_growth","take_rate","target_ev_revenue") if k not in a]
    if missing: return {"status":"DATA_UNAVAILABLE","missing":missing,"epistemic_label":"SCENARIO","probability":None}
    wrapped={"gmv":inputs["gmv"],"gmv_growth":{**inputs["gmv"],"value":float(a["gmv_growth"])},"take_rate":{**inputs["revenue"],"value":float(a["take_rate"])},"target_ev_revenue":{**inputs["target_ev_revenue"],"value":float(a["target_ev_revenue"])}}
    r=calculate(calculation_id="PLATFORM_SCENARIO_EV",inputs=wrapped,as_of=as_of,assumptions=[{"text":"Scenario, not reported fact"}])
    return {"status":r.get("status"),"epistemic_label":"SCENARIO","assumptions":a,"enterprise_value":r.get("calculated_value"),"probability":None,"calculation":r}

def evaluate_platform_marketplace(*,company:dict[str,Any],inputs:dict[str,Any],as_of:str,peers:list[dict[str,Any]]|None=None,history:list[dict[str,Any]]|None=None,scenarios:dict[str,dict[str,Any]]|None=None)->dict[str,Any]:
    try: date.fromisoformat(str(as_of)[:10])
    except (TypeError,ValueError): return {"status":"DATA_UNAVAILABLE","reason":"A valid ISO as-of date is required.","execution_eligible":False,"certified":False}
    issues={k:v for k in REQUIRED_PLATFORM_INPUTS if (v:=_issue(inputs.get(k),as_of))}
    if issues: return {"status":"POINT_IN_TIME_VIOLATION" if "POINT_IN_TIME_VIOLATION" in issues.values() else "DATA_UNAVAILABLE","input_issues":issues,"execution_eligible":False,"certified":False}
    positive=("enterprise_value","gmv","opening_gmv","closing_gmv","revenue","gross_profit","orders","active_buyers","active_sellers","new_customers","terminal_ev_revenue","horizon_years","target_ev_revenue")
    risks=[f"{k.upper()}_MUST_BE_POSITIVE" for k in positive if float(inputs[k]["value"])<=0]
    for k in ("repeat_rate","seller_concentration","refund_cancellation_rate"):
        if not 0<=float(inputs[k]["value"])<=1: risks.append(f"{k.upper()}_OUT_OF_RANGE")
    if float(inputs["revenue"]["value"])>float(inputs["gmv"]["value"]): risks.append("REVENUE_EXCEEDS_GMV_SCOPE_REVIEW_REQUIRED")
    if risks: return {"status":"VALIDATION_FAILED","risk_flags":risks,"execution_eligible":False,"certified":False}
    specs=(("ev_sales","EV_SALES",("enterprise_value","revenue")),("ev_gmv","EV_GMV",("enterprise_value","gmv")),("ev_gross_profit","EV_GROSS_PROFIT",("enterprise_value","gross_profit")),("gmv_growth","PLATFORM_GMV_GROWTH",("opening_gmv","closing_gmv")),("take_rate","PLATFORM_TAKE_RATE",("revenue","gmv")),("order_frequency","PLATFORM_ORDER_FREQUENCY",("orders","active_buyers")),("contribution_margin","PLATFORM_CONTRIBUTION_MARGIN",("contribution_profit","revenue")),("cac","PLATFORM_CUSTOMER_ACQUISITION_COST",("sales_marketing_spend","new_customers")),("fcf_margin","FCF_MARGIN",("fcf","revenue")))
    calculations={}
    for name,cid,keys in specs: calculations[name]=_calc(cid,inputs,keys,as_of)
    if any(r.get("status")!="SUCCESS" for r in calculations.values()): return {"status":"VALUATION_UNAVAILABLE","calculations":calculations,"execution_eligible":False,"certified":False}
    current=float(calculations["ev_sales"]["calculated_value"]); implied=calculate(calculation_id="IMPLIED_GROWTH_FROM_MULTIPLE",inputs={"current_multiple":{**inputs["enterprise_value"],"value":current},"terminal_multiple":inputs["terminal_ev_revenue"],"horizon_years":inputs["horizon_years"]},as_of=as_of)
    ig=implied.get("calculated_value") if implied.get("status")=="SUCCESS" else None; expected=float(inputs["agi_gmv_growth_expectation"]["value"])
    label="DATA_INSUFFICIENT" if ig is None or expected==0 else "EXPECTATIONS_STRETCHED" if ig/expected>1.10 else "EXPECTATIONS_FAVORABLE" if ig/expected<.90 else "EXPECTATIONS_NEUTRAL"
    peer=[float(x["ev_sales"]) for x in (peers or []) if isinstance(x.get("ev_sales"),(int,float))]; hist=[float(x["ev_sales"]) for x in (history or []) if isinstance(x.get("ev_sales"),(int,float)) and str(x.get("available_at") or "")[:10]<=as_of[:10]]
    scenario_rows={n:_scenario(inputs,as_of,(scenarios or {}).get(n) or {}) for n in ("BEAR","BASE","BULL")}
    g=float(inputs["agi_gmv_growth_expectation"]["value"]); tr=float(calculations["take_rate"]["calculated_value"]); m=float(inputs["target_ev_revenue"]["value"])
    grid=[{"gmv_growth":x,"take_rate":y,"target_ev_revenue":m,"enterprise_value":_scenario(inputs,as_of,{"gmv_growth":x,"take_rate":y,"target_ev_revenue":m}).get("enterprise_value")} for x in (g-.05,g,g+.05) for y in (max(0,tr-.01),tr,min(1,tr+.01))]
    symbol=str(company.get("symbol") or company.get("company_id") or "PLATFORM"); graph=ask_context(entity=symbol,question=f"What drives sustainable platform value for {symbol}?",industry="Internet Platforms and Marketplaces",analysis_as_of=as_of)
    return {"status":"OPERATIONAL_NOT_CERTIFIED","lifecycle_status":"OPERATIONAL","company_id":symbol,"as_of":as_of,"model":PLATFORM_MODEL.to_dict(),"business_economics":{"revenue_model":"buyers x frequency x order value -> GMV x take rate -> revenue -> contribution profit -> FCF","network_effect":{"status":"EVIDENCE_REQUIRED","user_growth_is_not_proof":True,"liquidity_and_retention_required":True},"competitive_advantage":{"status":"EVIDENCE_REQUIRED","moat_claim_allowed":False},"ai_analysis":{"benefit":"matching, discovery, trust and support productivity","risk":"lower discovery differentiation, fraud and incumbent replication","net_impact":"EVIDENCE_REQUIRED"}},"kpis":{n:r["calculated_value"] for n,r in calculations.items()}|{"active_sellers":inputs["active_sellers"]["value"],"repeat_rate":inputs["repeat_rate"]["value"],"seller_concentration":inputs["seller_concentration"]["value"],"refund_cancellation_rate":inputs["refund_cancellation_rate"]["value"]},"valuation":{"primary_method":"EV_SALES","current_ev_sales":current,"ev_gmv":calculations["ev_gmv"]["calculated_value"],"ev_gross_profit":calculations["ev_gross_profit"]["calculated_value"],"peer_median_ev_sales":median(peer) if peer else None,"historical_median_ev_sales":median(hist) if hist else None},"market_expectations":{"classification":label,"implied_growth":ig,"agi_gmv_growth_expectation":expected,"calculation":implied},"scenarios":scenario_rows,"sensitivity":{"variables":["gmv_growth","take_rate"],"grid":grid},"causal_context":{"templates":[r.to_dict() for r in platform_marketplace_templates(symbol)],"existing_graph":graph.get("causal_research",{}),"status":"PROPOSED_NOT_TRUSTED"},"monitoring":list(PLATFORM_MODEL.monitoring_variables),"risk_flags":[],"provenance":{k:{q:inputs[k].get(q) for q in ("source_id","available_at","period","unit","currency")} for k in REQUIRED_PLATFORM_INPUTS},"evidence_gaps":[n for n,p in (("peer_valuation",bool(peer)),("historical_valuation",bool(hist)),("trusted_network_effect_evidence",False)) if not p],"confidence":"MEDIUM" if peer and hist else "LOW","investment_attractiveness":"RESEARCH_ONLY","execution_eligible":False,"certified":False,"investment_certified":False}
