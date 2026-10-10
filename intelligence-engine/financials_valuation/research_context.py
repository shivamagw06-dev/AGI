"""Read-only subsector curriculum context for Ask AGI."""
from __future__ import annotations
from typing import Any, Callable

from financials_valuation.banking import BANKING_MODEL
from financials_valuation.classification import classify_financial_subsector
from financials_valuation.nonbank_models import MODELS
from financials_valuation.nonbank_service import PROFILES


def financial_research_context(company_id: str, *, loader: Callable[[str], dict[str, Any]] | None = None) -> dict[str, Any]:
    ticker = str(company_id or "").strip().upper()
    if not ticker:
        return {"status":"DATA_UNAVAILABLE","reason":"company_id_required","execution_eligible":False}
    if loader is None:
        try:
            from institutional_warehouse.production import read_company
            record = read_company(ticker) or {}
        except Exception:
            record = {}
    else:
        record = loader(ticker) or {}
    master = record.get("master") if isinstance(record.get("master"),dict) else record
    classification = classify_financial_subsector(master or {})
    subsector = classification.get("subsector")
    model = BANKING_MODEL if subsector == "COMMERCIAL_BANK" else MODELS.get(str(subsector))
    if model is None:
        return {"status":"CLASSIFICATION_UNAVAILABLE","company_id":ticker,"classification":classification,
                "reason":"No authoritative financial-subsector curriculum can be selected.","execution_eligible":False}
    required = ("market_price","book_value_per_share","roe","growth","cost_of_equity","normalized_eps","gnpa","credit_cost","cet1") if subsector=="COMMERCIAL_BANK" else PROFILES[str(subsector)].required
    return {"status":"MODEL_CONTEXT","company_id":ticker,"classification":classification,
            "model_version":model.version,"sector_id":model.sector_id,"sector_name":model.sector_name,
            "economic_structure":model.economic_structure,"key_kpis":[k.__dict__ for k in model.key_kpis],
            "valuation_methods":[m.__dict__ for m in model.valuation_methods],
            "valuation_drivers":list(model.valuation_drivers),"valuation_risks":list(model.valuation_risks),
            "monitoring":list(model.monitoring_variables),"common_errors":list(model.common_analytical_errors),
            "required_evidence":list(required),"calculation_status":"REQUIRES_PROVENANCE_COMPLETE_INPUT_PACK",
            "allowed_use":"research_planning_and_reasoning","execution_eligible":False,"certified":False}
