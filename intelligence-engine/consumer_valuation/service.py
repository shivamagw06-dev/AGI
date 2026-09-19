"""Fail-closed Consumer valuation and unit-economics evaluator."""
from __future__ import annotations
from datetime import date
from statistics import median
from typing import Any

from financial_engine import calculate
from consumer_valuation.classification import classify_consumer
from consumer_valuation.models import CAUSAL_TEMPLATES, MODELS

COMMON_REQUIRED=("revenue","ebitda","fcf","market_price","normalized_eps","enterprise_value","gross_profit","cogs","opening_inventory","closing_inventory")
SPECIAL_REQUIRED={
    "FMCG":("volume_growth","price_mix_growth"), "CONSUMER_DURABLES":("volume_growth","asp"),
    "RETAIL":("opening_stores","closing_stores","sssg","lease_liabilities","net_debt"),
    "QSR":("opening_stores","closing_stores","sssg","average_order_value"),
    "HOTELS_HOSPITALITY":("rooms","occupancy","adr","available_days"),
    "TEXTILES_APPAREL":("volume_growth","capacity_utilization","export_share"),
    "FOOTWEAR":("pairs_sold","asp","opening_stores","closing_stores"),
    "JEWELLERY":("jewellery_volume_growth","gold_price_growth","sssg"),
}


def _issue(item: Any, as_of: str) -> str | None:
    if not isinstance(item,dict) or not isinstance(item.get("value"),(int,float)) or isinstance(item.get("value"),bool): return "MISSING_OR_INVALID"
    if not item.get("source_id") or not item.get("period") or not item.get("available_at"): return "PROVENANCE_REQUIRED"
    if str(item["available_at"])[:10]>as_of[:10]: return "POINT_IN_TIME_VIOLATION"
    return None


def _calc(calc_id: str, inputs: dict[str,Any], keys: tuple[str,...], as_of: str) -> dict[str,Any] | None:
    if any(_issue(inputs.get(key),as_of) for key in keys): return None
    return calculate(calculation_id=calc_id,inputs={key:inputs[key] for key in keys},as_of=as_of)


def evaluate_consumer_company(*, company: dict[str,Any], inputs: dict[str,Any], as_of: str,
                              peers: list[dict[str,Any]] | None=None, history: list[dict[str,Any]] | None=None,
                              scenarios: dict[str,dict[str,Any]] | None=None) -> dict[str,Any]:
    try: date.fromisoformat(str(as_of)[:10])
    except (TypeError,ValueError): return {"status":"DATA_UNAVAILABLE","reason":"valid_as_of_required","execution_eligible":False}
    classification=classify_consumer(company)
    family=classification.get("model_family")
    if family not in MODELS:
        return {"status":"CLASSIFICATION_UNAVAILABLE","classification":classification,"execution_eligible":False,"investment_certified":False}
    model=MODELS[family]
    required=COMMON_REQUIRED+SPECIAL_REQUIRED[family]
    issues={key:issue for key in required if (issue:=_issue(inputs.get(key),as_of))}
    calculations={}
    specs={
        "pe":("PRICE_TO_EARNINGS",("market_price","normalized_eps")),
        "ev_ebitda":("EV_EBITDA",("enterprise_value","ebitda")),
        "ev_sales":("EV_SALES",("enterprise_value","revenue")),
        "gross_margin":("GROSS_MARGIN",("gross_profit","revenue")),
        "fcf_margin":("FCF_MARGIN",("fcf","revenue")),
        "inventory_turns":("CONSUMER_INVENTORY_TURNS",("cogs","opening_inventory","closing_inventory")),
    }
    if family in {"RETAIL","QSR","FOOTWEAR"}: specs["sales_per_store"]=("CONSUMER_SALES_PER_STORE",("revenue","opening_stores","closing_stores"))
    if family=="FMCG": specs["price_volume_mix_growth"]=("CONSUMER_PRICE_VOLUME_MIX_GROWTH",("volume_growth","price_mix_growth"))
    if family=="HOTELS_HOSPITALITY":
        specs.update({"revpar":("CONSUMER_REVPAR",("adr","occupancy")),"room_revenue_bridge":("CONSUMER_ROOM_REVENUE",("rooms","available_days","occupancy","adr")),"ev_per_key":("CONSUMER_EV_PER_KEY",("enterprise_value","rooms"))})
    if family=="FOOTWEAR": specs["revenue_per_pair"]=("CONSUMER_REVENUE_PER_PAIR",("revenue","pairs_sold"))
    if family=="RETAIL": specs["lease_adjusted_leverage"]=("CONSUMER_LEASE_ADJUSTED_LEVERAGE",("net_debt","lease_liabilities","ebitda"))
    for name,(calc_id,keys) in specs.items():
        result=_calc(calc_id,inputs,keys,as_of)
        calculations[name]=result if result else {"status":"DATA_UNAVAILABLE","missing":[key for key in keys if _issue(inputs.get(key),as_of)]}
    pe=(calculations.get("pe") or {}).get("calculated_value")
    implied=None
    if pe and not _issue(inputs.get("cost_of_equity"),as_of) and not _issue(inputs.get("payout_ratio"),as_of):
        implied=calculate(calculation_id="IMPLIED_GROWTH_FROM_PE",inputs={"cost_of_equity":inputs["cost_of_equity"],"payout_ratio":inputs["payout_ratio"],"price_to_earnings":{**inputs["market_price"],"value":pe}},as_of=as_of)
    peer_values=[float(row["pe"]) for row in (peers or []) if row.get("subsector")==family and isinstance(row.get("pe"),(int,float))]
    historical=[float(row["pe"]) for row in (history or []) if isinstance(row.get("pe"),(int,float)) and str(row.get("available_at") or "")[:10]<=as_of]
    scenario_pack={name:{"epistemic_label":"SCENARIO","driver_assumptions":(scenarios or {}).get(name) or {},"price_target":None,"auditable":True} for name in ("BEAR","BASE","BULL")}
    available=sum(1 for key in required if key not in issues)
    status="OPERATIONAL_NOT_CERTIFIED" if available else "DATA_UNAVAILABLE"
    return {"status":status,"lifecycle_status":"OPERATIONAL","company_id":str(company.get("symbol") or company.get("company_id")),"as_of":as_of,
        "classification":classification,"model":model.to_dict(),"required_inputs":list(required),"data_coverage":{"available":available,"required":len(required),"coverage_pct":round(100*available/len(required),2),"issues":issues},
        "calculations":calculations,"valuation":{"method_selector":[rule.__dict__ for rule in model.valuation_methods],"current_pe":pe,"peer_median_pe":median(peer_values) if peer_values else None,"historical_median_pe":median(historical) if historical else None},
        "reverse_valuation":{"implied_growth":implied.get("calculated_value") if implied and implied.get("status")=="SUCCESS" else None,"calculation":implied,"expectation_gap":"REQUIRES_AGI_BASE_CASE"},
        "scenarios":scenario_pack,"causal_context":{"templates":[list(path) for path in CAUSAL_TEMPLATES[family]],"status":"PROPOSED_NOT_TRUSTED","counter_effect_required":True},
        "monitoring":list(model.monitoring_variables),"analytical_warnings":list(model.common_analytical_errors),
        "provenance":{key:{field:inputs[key].get(field) for field in ("source_id","period","available_at","unit","currency")} for key in required if key in inputs},
        "evidence_gaps":list(issues),"confidence":"MEDIUM" if not issues and peer_values and historical else "LOW",
        "allowed_use":"RESEARCH_ONLY","execution_eligible":False,"certified":False,"research_validated":False,"investment_certified":False}
