"""Uniform evidence-gated sector valuation scorecard."""
from __future__ import annotations
from typing import Any

DIMENSIONS=("business_quality","industry_structure","growth_quality","operating_economics","cycle_position","capital_intensity","cash_conversion","balance_sheet","normalized_earnings","valuation","market_implied_expectations","catalysts","risks","thesis","monitoring")
REQUIREMENTS={"business_quality":("revenue","ebitda"),"industry_structure":(),"growth_quality":("revenue",),"operating_economics":("ebitda",),"cycle_position":("normalized_spread",),"capital_intensity":("capex","revenue"),"cash_conversion":("fcf","ebitda"),"balance_sheet":("net_debt",),"normalized_earnings":("normalized_eps",),"valuation":("market_price","normalized_eps","enterprise_value","ebitda"),"market_implied_expectations":("cost_of_equity","payout_ratio"),"catalysts":(),"risks":(),"thesis":(),"monitoring":()}

def build_sector_valuation_scorecard(*,evaluation:dict[str,Any],inputs:dict[str,Any],qualitative_evidence:dict[str,Any]|None=None)->dict[str,Any]:
    qualitative_evidence=qualitative_evidence or {}; as_of=str(evaluation.get("as_of") or ""); lines=[]
    for dimension in DIMENSIONS:
        required=REQUIREMENTS[dimension]; missing=[]; sources=[]
        for key in required:
            item=inputs.get(key)
            if not isinstance(item,dict) or not isinstance(item.get("value"),(int,float)) or not item.get("source_id") or str(item.get("available_at") or "")[:10]>as_of[:10]: missing.append(key)
            else: sources.append(item["source_id"])
        narrative=qualitative_evidence.get(dimension)
        if not required and not narrative: missing.append(f"{dimension}_evidence")
        if isinstance(narrative,dict) and narrative.get("source_id"): sources.append(narrative["source_id"])
        status="SUPPORTED" if not missing else ("PARTIAL" if sources else "DATA_REQUIRED")
        lines.append({"dimension":dimension,"status":status,"source_ids":sorted(set(sources)),"missing":missing,"finding":narrative.get("finding") if isinstance(narrative,dict) else None,"score":None})
    supported=sum(line["status"]=="SUPPORTED" for line in lines); partial=sum(line["status"]=="PARTIAL" for line in lines)
    return {"version":"sector-valuation-scorecard-v1","company_id":evaluation.get("company_id"),"subsector":(evaluation.get("classification") or {}).get("subsector"),"as_of":as_of,"dimensions":lines,"coverage":{"supported":supported,"partial":partial,"required":len(lines),"coverage_pct":round(100*(supported+.5*partial)/len(lines),2)},"conclusion":"EVIDENCE_COMPLETE" if supported==len(lines) else "RESEARCH_INCOMPLETE","allowed_use":"RESEARCH_ONLY","execution_eligible":False,"investment_certified":False}
