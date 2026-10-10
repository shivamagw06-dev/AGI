"""Fail-closed Phase 2D Consumer Internet/Digital Commerce evaluator."""
from __future__ import annotations
from datetime import date
from statistics import median
from typing import Any
from causal_research_engine.service import ask_context
from causal_research_engine.technology_templates import consumer_digital_templates
from financial_engine import calculate
from technology_valuation.consumer_model import CONSUMER_MODEL

REQUIRED_CONSUMER_INPUTS=("enterprise_value","net_revenue","opening_net_revenue","closing_net_revenue","net_sales","gross_profit","cogs","opening_inventory","closing_inventory","net_orders","gross_orders","returned_orders","active_customers","new_customers","repeat_rate","contribution_profit","sales_marketing_spend","advertising_revenue","monetizable_users","fcf","terminal_ev_revenue","horizon_years","agi_revenue_growth_expectation","target_ev_revenue")
def _issue(x,as_of):
    if not isinstance(x,dict) or not isinstance(x.get("value"),(int,float)) or isinstance(x.get("value"),bool): return "MISSING_OR_INVALID"
    if not x.get("source_id") or not x.get("period") or not x.get("available_at"): return "PROVENANCE_REQUIRED"
    if str(x["available_at"])[:10]>as_of[:10]: return "POINT_IN_TIME_VIOLATION"
    return None
def _calc(cid,i,keys,as_of): return calculate(calculation_id=cid,inputs={k:i[k] for k in keys},as_of=as_of)
def _scenario(i,as_of,a):
    missing=[k for k in ("revenue_growth","target_ev_revenue") if k not in a]
    if missing:return {"status":"DATA_UNAVAILABLE","missing":missing,"epistemic_label":"SCENARIO","probability":None}
    r=calculate(calculation_id="DIGITAL_SCENARIO_EV",inputs={"net_revenue":i["net_revenue"],"revenue_growth":{**i["net_revenue"],"value":float(a["revenue_growth"])},"target_ev_revenue":{**i["target_ev_revenue"],"value":float(a["target_ev_revenue"])}},as_of=as_of,assumptions=[{"text":"Scenario, not reported fact"}])
    return {"status":r.get("status"),"epistemic_label":"SCENARIO","assumptions":a,"enterprise_value":r.get("calculated_value"),"probability":None,"calculation":r}
def evaluate_consumer_digital(*,company:dict[str,Any],inputs:dict[str,Any],as_of:str,peers:list[dict[str,Any]]|None=None,history:list[dict[str,Any]]|None=None,scenarios:dict[str,dict[str,Any]]|None=None)->dict[str,Any]:
    try: date.fromisoformat(str(as_of)[:10])
    except (TypeError,ValueError): return {"status":"DATA_UNAVAILABLE","reason":"A valid ISO as-of date is required.","execution_eligible":False,"certified":False}
    issues={k:v for k in REQUIRED_CONSUMER_INPUTS if (v:=_issue(inputs.get(k),as_of))}
    if issues:return {"status":"POINT_IN_TIME_VIOLATION" if "POINT_IN_TIME_VIOLATION" in issues.values() else "DATA_UNAVAILABLE","input_issues":issues,"execution_eligible":False,"certified":False}
    positive=("enterprise_value","net_revenue","opening_net_revenue","closing_net_revenue","net_sales","gross_profit","cogs","opening_inventory","closing_inventory","net_orders","gross_orders","active_customers","new_customers","monetizable_users","terminal_ev_revenue","horizon_years","target_ev_revenue")
    risks=[f"{k.upper()}_MUST_BE_POSITIVE" for k in positive if float(inputs[k]["value"])<=0]
    if not 0<=float(inputs["repeat_rate"]["value"])<=1: risks.append("REPEAT_RATE_OUT_OF_RANGE")
    if not 0<=float(inputs["returned_orders"]["value"])<=float(inputs["gross_orders"]["value"]): risks.append("RETURNED_ORDERS_OUT_OF_RANGE")
    if float(inputs["net_orders"]["value"])>float(inputs["gross_orders"]["value"]): risks.append("NET_ORDERS_EXCEED_GROSS_ORDERS")
    if float(inputs["gross_profit"]["value"])>float(inputs["net_revenue"]["value"]): risks.append("GROSS_PROFIT_EXCEEDS_NET_REVENUE")
    if risks:return {"status":"VALIDATION_FAILED","risk_flags":risks,"execution_eligible":False,"certified":False}
    specs=(("ev_sales","EV_SALES",("enterprise_value","net_revenue")),("ev_gross_profit","EV_GROSS_PROFIT",("enterprise_value","gross_profit")),("revenue_growth","DIGITAL_NET_REVENUE_GROWTH",("opening_net_revenue","closing_net_revenue")),("aov","DIGITAL_AVERAGE_ORDER_VALUE",("net_sales","net_orders")),("gross_margin","DIGITAL_GROSS_MARGIN",("gross_profit","net_revenue")),("inventory_turns","DIGITAL_INVENTORY_TURNS",("cogs","opening_inventory","closing_inventory")),("return_rate","DIGITAL_RETURN_RATE",("returned_orders","gross_orders")),("order_frequency","PLATFORM_ORDER_FREQUENCY",("net_orders","active_customers")),("contribution_margin","PLATFORM_CONTRIBUTION_MARGIN",("contribution_profit","net_revenue")),("cac","PLATFORM_CUSTOMER_ACQUISITION_COST",("sales_marketing_spend","new_customers")),("ad_arpu","DIGITAL_AD_ARPU",("advertising_revenue","monetizable_users")),("fcf_margin","FCF_MARGIN",("fcf","net_revenue")))
    calculations={}
    for name,cid,keys in specs:
        wrapped={k:inputs[k] for k in keys}
        if cid in {"EV_SALES","PLATFORM_CONTRIBUTION_MARGIN","FCF_MARGIN"}: wrapped["revenue"]=wrapped.pop("net_revenue")
        if cid=="PLATFORM_ORDER_FREQUENCY": wrapped={"orders":inputs["net_orders"],"active_buyers":inputs["active_customers"]}
        calculations[name]=calculate(calculation_id=cid,inputs=wrapped,as_of=as_of)
    if any(r.get("status")!="SUCCESS" for r in calculations.values()):return {"status":"VALUATION_UNAVAILABLE","calculations":calculations,"execution_eligible":False,"certified":False}
    current=float(calculations["ev_sales"]["calculated_value"]); implied=calculate(calculation_id="IMPLIED_GROWTH_FROM_MULTIPLE",inputs={"current_multiple":{**inputs["enterprise_value"],"value":current},"terminal_multiple":inputs["terminal_ev_revenue"],"horizon_years":inputs["horizon_years"]},as_of=as_of); ig=implied.get("calculated_value") if implied.get("status")=="SUCCESS" else None; expected=float(inputs["agi_revenue_growth_expectation"]["value"]); label="DATA_INSUFFICIENT" if ig is None or expected==0 else "EXPECTATIONS_STRETCHED" if ig/expected>1.1 else "EXPECTATIONS_FAVORABLE" if ig/expected<.9 else "EXPECTATIONS_NEUTRAL"
    peer=[float(x["ev_sales"]) for x in (peers or []) if isinstance(x.get("ev_sales"),(int,float))]; hist=[float(x["ev_sales"]) for x in (history or []) if isinstance(x.get("ev_sales"),(int,float)) and str(x.get("available_at") or "")[:10]<=as_of[:10]]; scenario_rows={n:_scenario(inputs,as_of,(scenarios or {}).get(n) or {}) for n in ("BEAR","BASE","BULL")}; growth=float(inputs["agi_revenue_growth_expectation"]["value"]); multiple=float(inputs["target_ev_revenue"]["value"]); grid=[{"revenue_growth":g,"target_ev_revenue":m,"enterprise_value":_scenario(inputs,as_of,{"revenue_growth":g,"target_ev_revenue":m}).get("enterprise_value")} for g in (growth-.05,growth,growth+.05) for m in (multiple*.8,multiple,multiple*1.2)]
    symbol=str(company.get("symbol") or company.get("company_id") or "DIGITAL"); graph=ask_context(entity=symbol,question=f"What drives sustainable consumer digital value for {symbol}?",industry="Consumer Internet and Digital Commerce",analysis_as_of=as_of)
    return {"status":"OPERATIONAL_NOT_CERTIFIED","lifecycle_status":"OPERATIONAL","company_id":symbol,"as_of":as_of,"model":CONSUMER_MODEL.to_dict(),"business_economics":{"revenue_model":"active customers x frequency x AOV - returns -> net revenue -> gross profit -> contribution -> FCF","accounting_model":{"gmv_is_not_revenue":True,"first_party_and_marketplace_must_be_separated":True},"cohort_quality":{"status":"EVIDENCE_REQUIRED","downloads_are_not_active_customers":True},"competitive_advantage":{"status":"EVIDENCE_REQUIRED","moat_claim_allowed":False},"ai_analysis":{"benefit":"personalization, pricing, demand forecasting and service productivity","risk":"privacy, compute cost, commoditization and trust","net_impact":"EVIDENCE_REQUIRED"}},"kpis":{n:r["calculated_value"] for n,r in calculations.items()}|{"repeat_rate":inputs["repeat_rate"]["value"]},"valuation":{"primary_method":"EV_SALES","current_ev_sales":current,"ev_gross_profit":calculations["ev_gross_profit"]["calculated_value"],"peer_median_ev_sales":median(peer) if peer else None,"historical_median_ev_sales":median(hist) if hist else None},"market_expectations":{"classification":label,"implied_growth":ig,"agi_revenue_growth_expectation":expected,"calculation":implied},"scenarios":scenario_rows,"sensitivity":{"variables":["revenue_growth","target_ev_revenue"],"grid":grid},"causal_context":{"templates":[r.to_dict() for r in consumer_digital_templates(symbol)],"existing_graph":graph.get("causal_research",{}),"status":"PROPOSED_NOT_TRUSTED"},"monitoring":list(CONSUMER_MODEL.monitoring_variables),"risk_flags":[],"provenance":{k:{q:inputs[k].get(q) for q in ("source_id","available_at","period","unit","currency")} for k in REQUIRED_CONSUMER_INPUTS},"evidence_gaps":[n for n,p in (("peer_valuation",bool(peer)),("historical_valuation",bool(hist)),("cohort_evidence",False)) if not p],"confidence":"MEDIUM" if peer and hist else "LOW","investment_attractiveness":"RESEARCH_ONLY","execution_eligible":False,"certified":False,"investment_certified":False}
