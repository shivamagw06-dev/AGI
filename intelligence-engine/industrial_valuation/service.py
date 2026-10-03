"""Fail-closed Phase 4 industrial valuation evaluator."""
from __future__ import annotations
from datetime import date
from statistics import median
from typing import Any
from financial_engine import calculate
from industrial_valuation.classification import classify_industrial
from industrial_valuation.models import CAUSAL, MODELS

COMMON_REQUIRED=("revenue","ebitda","fcf","market_price","normalized_eps","enterprise_value","capex")
ORDER_FAMILIES={"CAPITAL_GOODS","ENGINEERING_EPC","INFRASTRUCTURE","CONSTRUCTION","DEFENCE_AEROSPACE","RAIL_TRANSPORT_EQUIPMENT","ELECTRICAL_EQUIPMENT","RENEWABLE_EQUIPMENT"}
CAPACITY_FAMILIES={"CAPITAL_GOODS","CEMENT","STEEL","METALS_MINING","CHEMICALS","SPECIALTY_CHEMICALS","AUTO_AUTO_COMPONENTS","RAIL_TRANSPORT_EQUIPMENT","ELECTRICAL_EQUIPMENT","RENEWABLE_EQUIPMENT","PACKAGING","PAPER_PULP"}
COMMODITY_FAMILIES={"CEMENT","STEEL","METALS_MINING","CHEMICALS","PACKAGING","PAPER_PULP"}

def required_inputs(family: str) -> tuple[str,...]:
    values=list(COMMON_REQUIRED)
    if family in ORDER_FAMILIES: values += ["order_inflow","order_book"]
    if family in CAPACITY_FAMILIES: values += ["capacity","production"]
    if family in COMMODITY_FAMILIES: values += ["realization_per_unit","input_cost_per_unit","sales_volume","normalized_spread"]
    return tuple(dict.fromkeys(values))

def _issue(item: Any, as_of: str) -> str | None:
    if not isinstance(item,dict) or not isinstance(item.get("value"),(int,float)) or isinstance(item.get("value"),bool): return "MISSING_OR_INVALID"
    if not item.get("source_id") or not item.get("period") or not item.get("available_at"): return "PROVENANCE_REQUIRED"
    if str(item["available_at"])[:10]>as_of[:10]: return "POINT_IN_TIME_VIOLATION"
    return None

def _calc(calc_id: str, inputs: dict[str,Any], keys: tuple[str,...], as_of: str) -> dict[str,Any] | None:
    if any(_issue(inputs.get(key),as_of) for key in keys): return None
    return calculate(calculation_id=calc_id,inputs={key:inputs[key] for key in keys},as_of=as_of)

def evaluate_industrial_company(*,company:dict[str,Any],inputs:dict[str,Any],as_of:str,peers:list[dict[str,Any]]|None=None,history:list[dict[str,Any]]|None=None,scenarios:dict[str,dict[str,Any]]|None=None)->dict[str,Any]:
    try: date.fromisoformat(str(as_of)[:10])
    except (TypeError,ValueError): return {"status":"DATA_UNAVAILABLE","reason":"valid_as_of_required","execution_eligible":False}
    classification=classify_industrial(company); family=classification.get("model_family")
    if family not in MODELS: return {"status":"CLASSIFICATION_UNAVAILABLE","classification":classification,"execution_eligible":False,"investment_certified":False}
    model=MODELS[family]; required=required_inputs(family)
    issues={key:issue for key in required if (issue:=_issue(inputs.get(key),as_of))}
    specs={"pe":("PRICE_TO_EARNINGS",("market_price","normalized_eps")),"ev_ebitda":("EV_EBITDA",("enterprise_value","ebitda")),"ev_sales":("EV_SALES",("enterprise_value","revenue")),"fcf_margin":("FCF_MARGIN",("fcf","revenue")),"capex_intensity":("INDUSTRIAL_CAPEX_INTENSITY",("capex","revenue"))}
    if family in ORDER_FAMILIES: specs.update({"book_to_bill":("INDUSTRIAL_BOOK_TO_BILL",("order_inflow","revenue")),"order_book_revenue":("INDUSTRIAL_ORDER_BOOK_REVENUE",("order_book","revenue"))})
    if family in CAPACITY_FAMILIES: specs.update({"capacity_utilization":("INDUSTRIAL_CAPACITY_UTILIZATION",("production","capacity")),"ev_per_capacity":("INDUSTRIAL_EV_PER_CAPACITY",("enterprise_value","capacity"))})
    if family in COMMODITY_FAMILIES: specs.update({"commodity_spread":("INDUSTRIAL_COMMODITY_SPREAD",("realization_per_unit","input_cost_per_unit")),"normalized_ebitda":("INDUSTRIAL_NORMALIZED_EBITDA",("sales_volume","normalized_spread"))})
    calculations={}
    for name,(calc_id,keys) in specs.items():
        result=_calc(calc_id,inputs,keys,as_of); calculations[name]=result or {"status":"DATA_UNAVAILABLE","missing":[key for key in keys if _issue(inputs.get(key),as_of)]}
    pe=(calculations.get("pe") or {}).get("calculated_value")
    implied=None
    if pe and not _issue(inputs.get("cost_of_equity"),as_of) and not _issue(inputs.get("payout_ratio"),as_of):
        implied=calculate(calculation_id="IMPLIED_GROWTH_FROM_PE",inputs={"cost_of_equity":inputs["cost_of_equity"],"payout_ratio":inputs["payout_ratio"],"price_to_earnings":{**inputs["market_price"],"value":pe}},as_of=as_of)
    peer_values=[float(row["pe"]) for row in (peers or []) if row.get("subsector")==family and isinstance(row.get("pe"),(int,float))]
    historical=[float(row["pe"]) for row in (history or []) if isinstance(row.get("pe"),(int,float)) and str(row.get("available_at") or "")[:10]<=as_of]
    scenario_pack={name:{"epistemic_label":"SCENARIO","driver_assumptions":(scenarios or {}).get(name) or {},"price_target":None,"auditable":True} for name in ("BEAR","BASE","BULL")}
    available=sum(key not in issues for key in required)
    warnings=list(model.common_analytical_errors)
    if family in COMMODITY_FAMILIES: warnings.append("Use normalized, not spot or peak-cycle, earnings for valuation.")
    if family=="DEFENCE_AEROSPACE": warnings.append("Announced order, signed order, executable backlog, revenue and cash are distinct states.")
    result={"status":"OPERATIONAL_NOT_CERTIFIED" if available else "DATA_UNAVAILABLE","lifecycle_status":"OPERATIONAL","company_id":str(company.get("symbol") or company.get("company_id")),"as_of":as_of,"classification":classification,"model":model.to_dict(),"required_inputs":list(required),"data_coverage":{"available":available,"required":len(required),"coverage_pct":round(100*available/len(required),2),"issues":issues},"calculations":calculations,"cycle_normalization":{"required":family in COMMODITY_FAMILIES,"status":"CALCULATED" if (calculations.get("normalized_ebitda") or {}).get("status")=="SUCCESS" else "DATA_REQUIRED"},"valuation":{"method_selector":[rule.__dict__ for rule in model.valuation_methods],"current_pe":pe,"peer_median_pe":median(peer_values) if peer_values else None,"historical_median_pe":median(historical) if historical else None},"reverse_valuation":{"implied_growth":implied.get("calculated_value") if implied and implied.get("status")=="SUCCESS" else None,"calculation":implied,"expectation_gap":"REQUIRES_AGI_BASE_CASE"},"scenarios":scenario_pack,"causal_context":{"templates":[list(path) for path in CAUSAL[family]],"status":"PROPOSED_NOT_TRUSTED","counter_effect_required":True},"monitoring":list(model.monitoring_variables),"analytical_warnings":warnings,"provenance":{key:{field:inputs[key].get(field) for field in ("source_id","period","available_at","unit","currency")} for key in required if key in inputs},"evidence_gaps":list(issues),"confidence":"MEDIUM" if not issues and peer_values and historical else "LOW","allowed_use":"RESEARCH_ONLY","execution_eligible":False,"certified":False,"research_validated":False,"investment_certified":False}
    from industrial_valuation.scorecard import build_sector_valuation_scorecard
    result["sector_valuation_scorecard"]=build_sector_valuation_scorecard(evaluation=result,inputs=inputs)
    return result
