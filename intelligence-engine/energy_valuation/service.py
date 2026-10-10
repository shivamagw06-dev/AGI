"""Fail-closed Phase 5 Energy valuation evaluator."""
from __future__ import annotations
from datetime import date
from statistics import median
from typing import Any
from financial_engine import calculate
from energy_valuation.classification import classify_energy
from energy_valuation.models import CAUSAL,MODELS

COMMON=("revenue","ebitda","fcf","enterprise_value","market_price","normalized_eps","capex","net_debt")
POWER={"POWER_GENERATION","POWER_TRANSMISSION","POWER_DISTRIBUTION","RENEWABLE_POWER","SOLAR","WIND","HYDRO_POWER","NUCLEAR_SUPPLY_CHAIN"}
COMMODITY={"OIL_GAS_UPSTREAM","OIL_GAS_REFINING","OIL_GAS_MARKETING","OIL_GAS_INTEGRATED","COAL","GAS_UTILITIES","CITY_GAS_DISTRIBUTION","OILFIELD_SERVICES","MINING_SERVICES","ENERGY_STORAGE_BATTERIES"}
RESOURCE={"OIL_GAS_UPSTREAM","OIL_GAS_INTEGRATED","COAL"}
REGULATED={"POWER_TRANSMISSION","POWER_DISTRIBUTION","GAS_UTILITIES","WATER_UTILITIES"}
PROJECT=POWER|{"WATER_UTILITIES","WASTE_MANAGEMENT","ENERGY_STORAGE_BATTERIES"}
def required_inputs(family:str)->tuple[str,...]:
 keys=list(COMMON)
 if family in POWER:keys += ["installed_capacity_mw","generation","available_hours"]
 if family in COMMODITY:keys += ["production_volume","realization_per_unit","cash_cost_per_unit","normalized_spread"]
 if family in RESOURCE:keys += ["reserves","annual_production"]
 if family in REGULATED:keys += ["regulated_asset_base","allowed_return"]
 return tuple(dict.fromkeys(keys))
def _issue(item:Any,as_of:str)->str|None:
 if not isinstance(item,dict) or not isinstance(item.get("value"),(int,float)) or isinstance(item.get("value"),bool):return "MISSING_OR_INVALID"
 if not item.get("source_id") or not item.get("period") or not item.get("available_at"):return "PROVENANCE_REQUIRED"
 if str(item["available_at"])[:10]>as_of[:10]:return "POINT_IN_TIME_VIOLATION"
 return None
def _calc(calc_id:str,inputs:dict[str,Any],keys:tuple[str,...],as_of:str)->dict[str,Any]|None:
 if any(_issue(inputs.get(key),as_of) for key in keys):return None
 return calculate(calculation_id=calc_id,inputs={key:inputs[key] for key in keys},as_of=as_of)
def _observation_matrix(company_id:str,family:str,required:tuple[str,...],inputs:dict[str,Any],as_of:str)->list[dict[str,Any]]:
 rows=[]
 for metric in required:
  item=inputs.get(metric) if isinstance(inputs.get(metric),dict) else {}; issue=_issue(item,as_of)
  metadata_complete=all(item.get(key) is not None for key in ("source_id","period","available_at"))
  status="PIT_INVALID" if issue=="POINT_IN_TIME_VIOLATION" else ("SUPPORTED" if issue is None and metadata_complete else "DATA_REQUIRED")
  rows.append({"company":company_id,"segment":item.get("segment"),"subsector":family,"metric":metric,"required":True,"available":issue is None,"value":item.get("value"),"unit":item.get("unit"),"period":item.get("period"),"publication_date":item.get("publication_date") or item.get("available_at"),"effective_date":item.get("effective_date"),"as_of_date":as_of,"source":item.get("source_id"),"source_priority":item.get("source_priority"),"evidence":item.get("evidence"),"pit_valid":issue is None,"confidence":item.get("confidence"),"validation_status":item.get("validation_status"),"quality":item.get("quality"),"status":status})
 return rows
def evaluate_energy_company(*,company:dict[str,Any],inputs:dict[str,Any],as_of:str,peers:list[dict[str,Any]]|None=None,history:list[dict[str,Any]]|None=None,scenarios:dict[str,dict[str,Any]]|None=None)->dict[str,Any]:
 try:date.fromisoformat(str(as_of)[:10])
 except (TypeError,ValueError):return {"status":"DATA_UNAVAILABLE","reason":"valid_as_of_required","execution_eligible":False}
 classification=classify_energy(company); family=classification.get("model_family")
 if family not in MODELS:return {"status":"CLASSIFICATION_UNAVAILABLE","classification":classification,"execution_eligible":False,"investment_certified":False}
 model=MODELS[family]; required=required_inputs(family); issues={key:issue for key in required if (issue:=_issue(inputs.get(key),as_of))}
 specs={"pe":("PRICE_TO_EARNINGS",("market_price","normalized_eps")),"ev_ebitda":("EV_EBITDA",("enterprise_value","ebitda")),"ev_sales":("EV_SALES",("enterprise_value","revenue")),"fcf_margin":("FCF_MARGIN",("fcf","revenue"))}
 if family in POWER:specs.update({"plf":("ENERGY_PLANT_LOAD_FACTOR",("generation","installed_capacity_mw","available_hours")),"generation_per_mw":("ENERGY_GENERATION_PER_MW",("generation","installed_capacity_mw")),"revenue_per_mw":("ENERGY_REVENUE_PER_MW",("revenue","installed_capacity_mw")),"ebitda_per_mw":("ENERGY_EBITDA_PER_MW",("ebitda","installed_capacity_mw")),"debt_per_mw":("ENERGY_DEBT_PER_MW",("net_debt","installed_capacity_mw")),"fcf_per_mw":("ENERGY_FCF_PER_MW",("fcf","installed_capacity_mw")),"ev_per_mw":("ENERGY_EV_PER_MW",("enterprise_value","installed_capacity_mw"))})
 if family in COMMODITY:specs.update({"unit_spread":("ENERGY_UNIT_SPREAD",("realization_per_unit","cash_cost_per_unit")),"ebitda_per_unit":("ENERGY_EBITDA_PER_UNIT",("ebitda","production_volume")),"normalized_ebitda":("ENERGY_NORMALIZED_EBITDA",("production_volume","normalized_spread"))})
 if family in RESOURCE:specs.update({"reserve_life":("ENERGY_RESERVE_LIFE",("reserves","annual_production")),"ev_per_reserve":("ENERGY_EV_PER_RESERVE",("enterprise_value","reserves"))})
 if family in REGULATED:specs["regulated_return"]=("ENERGY_REGULATED_RETURN",("regulated_asset_base","allowed_return"))
 if family in PROJECT:specs["project_npv"]=("ENERGY_PROJECT_NPV",("initial_capex","annual_fcf","discount_rate","operating_life"))
 calculations={}
 for name,(calc_id,keys) in specs.items():
  result=_calc(calc_id,inputs,keys,as_of); calculations[name]=result or {"status":"DATA_UNAVAILABLE","missing":[key for key in keys if _issue(inputs.get(key),as_of)]}
 pe=(calculations.get("pe") or {}).get("calculated_value"); implied=None
 if pe and not _issue(inputs.get("cost_of_equity"),as_of) and not _issue(inputs.get("payout_ratio"),as_of):implied=calculate(calculation_id="IMPLIED_GROWTH_FROM_PE",inputs={"cost_of_equity":inputs["cost_of_equity"],"payout_ratio":inputs["payout_ratio"],"price_to_earnings":{**inputs["market_price"],"value":pe}},as_of=as_of)
 peer_values=[float(x["pe"]) for x in (peers or []) if x.get("subsector")==family and isinstance(x.get("pe"),(int,float))]; historical=[float(x["pe"]) for x in (history or []) if isinstance(x.get("pe"),(int,float)) and str(x.get("available_at") or "")[:10]<=as_of]
 scenario_pack={name:{"epistemic_label":"SCENARIO","operating_assumptions":(scenarios or {}).get(name) or {},"price_target":None,"auditable":True} for name in ("BEAR","BASE","BULL")}; available=sum(key not in issues for key in required)
 warnings=list(model.common_analytical_errors)
 if family in COMMODITY:warnings.append("Normalize commodity price/spread; do not capitalize peak earnings.")
 if family in POWER:warnings.append("Installed MW, available MW, generation and realized PLF are distinct states.")
 company_id=str(company.get("symbol") or company.get("company_id"))
 result={"status":"OPERATIONAL_NOT_CERTIFIED" if available else "DATA_UNAVAILABLE","lifecycle_status":"OPERATIONAL","company_id":company_id,"as_of":as_of,"classification":classification,"model":model.to_dict(),"required_inputs":list(required),"data_coverage":{"available":available,"required":len(required),"coverage_pct":round(100*available/len(required),2),"issues":issues},"observation_matrix":_observation_matrix(company_id,family,required,inputs,as_of),"calculations":calculations,"cycle":{"state":"DATA_REQUIRED","allowed_states":["EARLY_RECOVERY","RECOVERY","MID_CYCLE","PEAK","DOWNTURN","TROUGH"],"share_price_not_used":True},"commodity_normalization":{"required":family in COMMODITY,"status":"CALCULATED" if (calculations.get("normalized_ebitda") or {}).get("status")=="SUCCESS" else "DATA_REQUIRED","historical_percentile":"DATA_REQUIRED"},"valuation":{"method_selector":[rule.__dict__ for rule in model.valuation_methods],"current_pe":pe,"peer_median_pe":median(peer_values) if peer_values else None,"historical_median_pe":median(historical) if historical else None},"reverse_valuation":{"implied_growth":implied.get("calculated_value") if implied and implied.get("status")=="SUCCESS" else None,"commodity_price":"REQUIRES_ASSET_MODEL","tariff_or_utilization":"REQUIRES_PROJECT_MODEL","expectation_gap":"REQUIRES_AGI_BASE_CASE"},"scenarios":scenario_pack,"causal_context":{"templates":[list(path) for path in CAUSAL[family]],"edge_contract":{"direction":True,"conditions":True,"time_lag":True,"counter_effect":True,"evidence":True,"source":True,"confidence":True,"effective_date":True},"status":"PROPOSED_NOT_TRUSTED"},"monitoring":list(model.monitoring_variables),"analytical_warnings":warnings,"accounting_quality_status":"AREA_REQUIRING_INVESTIGATION" if issues else "NO_UNSUPPORTED_LABEL","provenance":{key:{field:inputs[key].get(field) for field in ("source_id","period","available_at","unit","currency")} for key in required if key in inputs},"evidence_gaps":list(issues),"confidence":"MEDIUM" if not issues and peer_values and historical else "LOW","allowed_use":"RESEARCH_ONLY","execution_eligible":False,"data_validated":False,"research_validated":False,"investment_certified":False}
 from energy_valuation.scorecard import build_energy_scorecard
 result["sector_valuation_scorecard"]=build_energy_scorecard(evaluation=result,inputs=inputs)
 return result
