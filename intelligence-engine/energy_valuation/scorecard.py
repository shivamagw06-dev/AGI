"""Phase 5 implementation of the shared 15-dimension evidence scorecard."""
from __future__ import annotations
from typing import Any
from industrial_valuation.scorecard import DIMENSIONS
REQ={"business_quality":("revenue","ebitda"),"industry_structure":(),"growth_quality":("production_volume",),"operating_economics":("ebitda",),"cycle_position":(),"capital_intensity":("capex","revenue"),"cash_conversion":("fcf","ebitda"),"balance_sheet":("net_debt",),"normalized_earnings":("normalized_eps",),"valuation":("enterprise_value","ebitda"),"market_implied_expectations":(),"catalysts":(),"risks":(),"thesis":(),"monitoring":()}
def build_energy_scorecard(*,evaluation:dict[str,Any],inputs:dict[str,Any],qualitative_evidence:dict[str,Any]|None=None)->dict[str,Any]:
 evidence=qualitative_evidence or {}; as_of=str(evaluation.get("as_of") or ""); lines=[]
 for dimension in DIMENSIONS:
  missing=[]; sources=[]
  for key in REQ[dimension]:
   item=inputs.get(key)
   if not isinstance(item,dict) or not isinstance(item.get("value"),(int,float)) or not item.get("source_id") or str(item.get("available_at") or "")[:10]>as_of[:10]:missing.append(key)
   else:sources.append(item["source_id"])
  narrative=evidence.get(dimension)
  if not REQ[dimension] and not narrative:missing.append(f"{dimension}_evidence")
  if isinstance(narrative,dict) and narrative.get("source_id"):sources.append(narrative["source_id"])
  lines.append({"dimension":dimension,"status":"SUPPORTED" if not missing else ("PARTIAL" if sources else "DATA_REQUIRED"),"source_ids":sorted(set(sources)),"missing":missing,"finding":narrative.get("finding") if isinstance(narrative,dict) else None,"score":None})
 supported=sum(x["status"]=="SUPPORTED" for x in lines); partial=sum(x["status"]=="PARTIAL" for x in lines)
 return {"version":"sector-valuation-scorecard-v1","company_id":evaluation.get("company_id"),"subsector":(evaluation.get("classification") or {}).get("subsector"),"as_of":as_of,"dimensions":lines,"coverage":{"supported":supported,"partial":partial,"required":len(lines),"coverage_pct":round(100*(supported+.5*partial)/len(lines),2)},"conclusion":"EVIDENCE_COMPLETE" if supported==len(lines) else "RESEARCH_INCOMPLETE","allowed_use":"RESEARCH_ONLY","execution_eligible":False,"investment_certified":False}
