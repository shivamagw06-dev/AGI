"""Read-only Consumer curriculum context for Ask AGI."""
from __future__ import annotations
from typing import Any, Callable
from consumer_valuation.classification import classify_consumer
from consumer_valuation.models import CAUSAL_TEMPLATES, MODELS
from consumer_valuation.service import COMMON_REQUIRED, SPECIAL_REQUIRED


def consumer_research_context(company_id: str, *, loader: Callable[[str],dict[str,Any]] | None=None) -> dict[str,Any]:
    ticker=str(company_id or "").upper().strip()
    if not ticker: return {"status":"DATA_UNAVAILABLE","reason":"company_id_required","execution_eligible":False}
    if loader is None:
        try:
            from institutional_warehouse.production import read_company
            record=read_company(ticker) or {}
        except Exception: record={}
    else: record=loader(ticker) or {}
    master=record.get("master") if isinstance(record.get("master"),dict) else record
    classification=classify_consumer({**(master or {}),"symbol":ticker})
    family=classification.get("model_family")
    if family not in MODELS:
        return {"status":"CLASSIFICATION_UNAVAILABLE","company_id":ticker,"classification":classification,"execution_eligible":False}
    model=MODELS[family]
    return {"status":"MODEL_CONTEXT","company_id":ticker,"classification":classification,"model_version":model.version,
        "sector_id":model.sector_id,"sector_name":model.sector_name,"business_model":model.economic_structure,
        "key_kpis":[item.__dict__ for item in model.key_kpis],"valuation_methods":[item.__dict__ for item in model.valuation_methods],
        "causal_templates":[list(path) for path in CAUSAL_TEMPLATES[family]],"valuation_drivers":list(model.valuation_drivers),
        "risks":list(model.valuation_risks),"monitoring":list(model.monitoring_variables),
        "required_evidence":list(COMMON_REQUIRED+SPECIAL_REQUIRED[family]),"calculation_authority":"AFE_ONLY",
        "allowed_use":"research_planning_and_reasoning","execution_eligible":False,"investment_certified":False}
