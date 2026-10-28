"""Representative-company Phase 4 validation protocol."""
from __future__ import annotations
from typing import Any
from industrial_valuation.service import evaluate_industrial_company
from industrial_valuation.scorecard import build_sector_valuation_scorecard

VALIDATION_COHORTS={"CAPITAL_GOODS":("SIEMENS","ABB","CUMMINSIND"),"ENGINEERING_EPC":("LT","KEC"),"INFRASTRUCTURE":("IRB","GMRAIRPORT"),"CONSTRUCTION":("NCC","KNRCON"),"CEMENT":("ULTRACEMCO","SHREECEM"),"STEEL":("TATASTEEL","JSWSTEEL"),"METALS_MINING":("HINDALCO","VEDL"),"CHEMICALS":("TATACHEM","GNFC"),"SPECIALTY_CHEMICALS":("PIIND","SRF","DEEPAKNTR","NAVINFLUOR"),"AUTO_AUTO_COMPONENTS":("MARUTI","M&M","BOSCHLTD","SONACOMS"),"DEFENCE_AEROSPACE":("HAL","BEL"),"RAIL_TRANSPORT_EQUIPMENT":("TITAGARH","RVNL"),"ELECTRICAL_EQUIPMENT":("POLYCAB","CGPOWER"),"RENEWABLE_EQUIPMENT":("WAAREEENER","SUZLON"),"PACKAGING":("UFLEX",),"PAPER_PULP":("JKPAPER",)}
VALIDATION_QUESTIONS=("business_model","earnings_drivers","cyclical_vs_structural","cycle_position","normalized_earning_power","growth_capital_requirement","cash_conversion","market_implied_expectations","bull_case_requirements","thesis_breakers","quarterly_monitoring")

def validate_company_pack(*,company:dict[str,Any],inputs:dict[str,Any],as_of:str,qualitative_evidence:dict[str,Any]|None=None,peers:list[dict[str,Any]]|None=None,history:list[dict[str,Any]]|None=None,scenarios:dict[str,dict[str,Any]]|None=None)->dict[str,Any]:
    evaluation=evaluate_industrial_company(company=company,inputs=inputs,as_of=as_of,peers=peers,history=history,scenarios=scenarios)
    scorecard=build_sector_valuation_scorecard(evaluation=evaluation,inputs=inputs,qualitative_evidence=qualitative_evidence)
    evidence=qualitative_evidence or {}; answers={key:{"status":"SUPPORTED" if evidence.get(key) else "DATA_REQUIRED","evidence":evidence.get(key)} for key in VALIDATION_QUESTIONS}; supported=sum(row["status"]=="SUPPORTED" for row in answers.values())
    return {"phase":"4_company_validation","company_id":evaluation.get("company_id"),"evaluation":evaluation,"sector_valuation_scorecard":scorecard,"validation_questions":answers,"question_coverage":{"supported":supported,"required":len(answers)},"validation_status":"EVIDENCE_VALIDATED" if supported==len(answers) and scorecard["conclusion"]=="EVIDENCE_COMPLETE" else "VALIDATION_INCOMPLETE","research_validated":False,"investment_certified":False,"execution_eligible":False}

def cohort_manifest()->dict[str,Any]:
    return {"subsectors":len(VALIDATION_COHORTS),"companies":sum(len(rows) for rows in VALIDATION_COHORTS.values()),"cohorts":VALIDATION_COHORTS,"questions":VALIDATION_QUESTIONS,"status":"READY_FOR_EVIDENCE_PACKS"}
