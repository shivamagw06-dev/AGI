"""Phase 5 company evidence-validation protocol."""
from __future__ import annotations
from typing import Any
from energy_valuation.service import evaluate_energy_company
from energy_valuation.scorecard import build_energy_scorecard
VALIDATION_QUESTIONS=("business_model","earnings_drivers","cyclical_vs_structural","cycle_position","normalized_earning_power","growth_capital_requirement","cash_conversion","market_implied_expectations","bull_case_requirements","thesis_breakers","quarterly_monitoring")
def validate_energy_pack(*,company:dict[str,Any],inputs:dict[str,Any],as_of:str,qualitative_evidence:dict[str,Any]|None=None,peers:list[dict[str,Any]]|None=None,history:list[dict[str,Any]]|None=None,scenarios:dict[str,dict[str,Any]]|None=None)->dict[str,Any]:
 evaluation=evaluate_energy_company(company=company,inputs=inputs,as_of=as_of,peers=peers,history=history,scenarios=scenarios); evidence=qualitative_evidence or {}; card=build_energy_scorecard(evaluation=evaluation,inputs=inputs,qualitative_evidence=evidence); answers={key:{"status":"SUPPORTED" if evidence.get(key) else "DATA_REQUIRED","evidence":evidence.get(key)} for key in VALIDATION_QUESTIONS}; supported=sum(x["status"]=="SUPPORTED" for x in answers.values())
 return {"phase":"5_company_validation","company_id":evaluation.get("company_id"),"evaluation":evaluation,"sector_valuation_scorecard":card,"validation_questions":answers,"question_coverage":{"supported":supported,"required":len(answers)},"validation_status":"EVIDENCE_VALIDATED" if supported==len(answers) and card["conclusion"]=="EVIDENCE_COMPLETE" else "VALIDATION_INCOMPLETE","research_validated":False,"investment_certified":False,"execution_eligible":False}
