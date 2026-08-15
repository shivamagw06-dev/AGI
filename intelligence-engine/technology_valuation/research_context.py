"""Read-only Phase 2A curriculum context for Ask AGI."""
from __future__ import annotations
from typing import Any, Callable
from technology_valuation.classification import classify_technology_subsector
from technology_valuation.model import IT_SERVICES_MODEL
from technology_valuation.service import REQUIRED_INPUTS
from technology_valuation.saas_model import SOFTWARE_SAAS_MODEL
from technology_valuation.saas_service import REQUIRED_SAAS_INPUTS
from technology_valuation.platform_model import PLATFORM_MODEL
from technology_valuation.platform_service import REQUIRED_PLATFORM_INPUTS


def technology_research_context(company_id: str, *, loader: Callable[[str],dict[str,Any]] | None=None) -> dict[str,Any]:
    ticker=str(company_id or "").strip().upper()
    if not ticker: return {"status":"DATA_UNAVAILABLE","reason":"company_id_required","execution_eligible":False}
    if loader is None:
        try:
            from institutional_warehouse.production import read_company
            record=read_company(ticker) or {}
        except Exception: record={}
    else: record=loader(ticker) or {}
    master=record.get("master") if isinstance(record.get("master"),dict) else record
    classification=classify_technology_subsector({**(master or {}),"symbol":ticker})
    if classification.get("model_family")=="SOFTWARE_SAAS":
        model=SOFTWARE_SAAS_MODEL; required=REQUIRED_SAAS_INPUTS
    elif classification.get("model_family")=="INTERNET_PLATFORMS_MARKETPLACES":
        model=PLATFORM_MODEL; required=REQUIRED_PLATFORM_INPUTS
    elif classification.get("subsector")=="IT_SERVICES":
        model=IT_SERVICES_MODEL; required=REQUIRED_INPUTS
    else:
        return {"status":"CLASSIFICATION_UNAVAILABLE","company_id":ticker,"classification":classification,"execution_eligible":False}
    return {"status":"MODEL_CONTEXT","company_id":ticker,"classification":classification,"model_version":model.version,
        "sector_id":model.sector_id,"sector_name":model.sector_name,"economic_structure":model.economic_structure,
        "key_kpis":[k.__dict__ for k in model.key_kpis],"valuation_methods":[m.__dict__ for m in model.valuation_methods],
        "valuation_drivers":list(model.valuation_drivers),"valuation_risks":list(model.valuation_risks),
        "monitoring":list(model.monitoring_variables),"required_evidence":list(required),
        "calculation_status":"REQUIRES_PROVENANCE_COMPLETE_INPUT_PACK","causal_status":"PROPOSED_NOT_TRUSTED",
        "allowed_use":"research_planning_and_reasoning","execution_eligible":False,"certified":False,"investment_certified":False}
