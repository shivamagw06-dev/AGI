"""Twenty-three-gate Phase 2A certification without self-promotion."""
from __future__ import annotations
from typing import Any
from technology_valuation.answer import format_technology_answer
from technology_valuation.model import IT_SERVICES_MODEL
from technology_valuation.service import REQUIRED_INPUTS, evaluate_technology_company

GATES=("classification","business_model","kpi","revenue_driver","margin_driver","cash_flow","capital_intensity",
       "competitive_advantage","method_selection","historical_valuation","reverse_valuation","peer_comparison",
       "scenario","sensitivity","macro_transmission","ai_impact","point_in_time","accounting_quality","missing_data",
       "contradiction","provenance","client_answer","adversarial")


def certify_it_services(company_packs: dict[str,dict[str,Any]], *, authorized_reviewer: str | None=None,
                        reviewer_authorized: bool=False, review_evidence_id: str | None=None) -> dict[str,Any]:
    results={symbol:evaluate_technology_company(company={"symbol":symbol},inputs=pack.get("inputs") or {},as_of=str(pack.get("as_of") or ""),peers=pack.get("peers"),history=pack.get("history"),scenarios=pack.get("scenarios")) for symbol,pack in company_packs.items()}
    cohort={"TCS","INFY","HCLTECH","WIPRO","TECHM"}
    operational=set(results)==cohort and all(row.get("status")=="OPERATIONAL_NOT_CERTIFIED" for row in results.values())
    sample=next(iter(company_packs.values()),{}); inputs=sample.get("inputs") or {}; as_of=str(sample.get("as_of") or "2026-08-15")
    missing=dict(inputs); missing.pop(REQUIRED_INPUTS[0],None)
    future={k:dict(v) for k,v in inputs.items() if isinstance(v,dict)}
    if REQUIRED_INPUTS[0] in future: future[REQUIRED_INPUTS[0]]["available_at"]="9999-12-31"
    bad={k:dict(v) for k,v in inputs.items() if isinstance(v,dict)}
    if "utilization" in bad: bad["utilization"]["value"]=1.5
    gates={
        "classification":operational,"business_model":bool(IT_SERVICES_MODEL.economic_structure),"kpi":len(IT_SERVICES_MODEL.key_kpis)>=12,
        "revenue_driver":len(IT_SERVICES_MODEL.revenue_drivers)>=6,"margin_driver":len(IT_SERVICES_MODEL.cost_drivers)>=5,
        "cash_flow":any(k.key=="fcf_margin" for k in IT_SERVICES_MODEL.key_kpis),"capital_intensity":bool(IT_SERVICES_MODEL.capital_structure),
        "competitive_advantage":operational and all((r.get("business_economics") or {}).get("competitive_advantage",{}).get("moat_claim_allowed") is False for r in results.values()),
        "method_selection":len(IT_SERVICES_MODEL.valuation_methods)>=4,
        "historical_valuation":operational and all((r.get("valuation") or {}).get("historical_median_pe") is not None for r in results.values()),
        "reverse_valuation":operational and all((r.get("market_expectations") or {}).get("classification")!="DATA_INSUFFICIENT" for r in results.values()),
        "peer_comparison":operational and all((r.get("valuation") or {}).get("peer_median_pe") is not None for r in results.values()),
        "scenario":operational and all(all(v.get("status")=="SUCCESS" for v in (r.get("scenarios") or {}).values()) for r in results.values()),
        "sensitivity":operational and all(len((r.get("sensitivity") or {}).get("grid") or [])==9 for r in results.values()),
        "macro_transmission":operational and all((r.get("causal_context") or {}).get("templates") for r in results.values()),
        "ai_impact":operational and all((r.get("business_economics") or {}).get("ai_analysis",{}).get("net_impact")=="EVIDENCE_REQUIRED" for r in results.values()),
        "point_in_time":bool(future) and evaluate_technology_company(company={"symbol":"TCS"},inputs=future,as_of=as_of).get("status")=="POINT_IN_TIME_VIOLATION",
        "accounting_quality":operational,"missing_data":bool(missing) and evaluate_technology_company(company={"symbol":"TCS"},inputs=missing,as_of=as_of).get("status")=="DATA_UNAVAILABLE",
        "contradiction":operational and all(any(t.get("counter_effects") for t in (r.get("causal_context") or {}).get("templates") or []) for r in results.values()),
        "provenance":operational and all(len(r.get("provenance") or {})==len(REQUIRED_INPUTS) and bool(company_packs[s].get("warehouse_receipt_id")) and bool(company_packs[s].get("independent_verification_id")) for s,r in results.items()),
        "client_answer":operational and all(format_technology_answer(r).get("execution_eligible") is False for r in results.values()),
        "adversarial":bool(bad) and evaluate_technology_company(company={"symbol":"TCS"},inputs=bad,as_of=as_of).get("status")=="VALIDATION_FAILED",
    }
    passed=sum(gates.values()); external=bool(authorized_reviewer and reviewer_authorized and review_evidence_id)
    lifecycle="EVIDENCE_VALIDATED" if passed==23 else "OPERATIONAL" if operational else "ENGINEERED"
    status="PASSED" if passed==23 and external else "IN_PROGRESS" if passed else "FAILED"
    return {"sector_id":IT_SERVICES_MODEL.sector_id,"subsector":"IT_SERVICES","model_version":IT_SERVICES_MODEL.version,
        "certification_status":status,"lifecycle_status":lifecycle,"passed_gates":passed,"total_gates":23,"gates":gates,
        "companies":results,"authorized_reviewer":authorized_reviewer,"reviewer_authorized":reviewer_authorized,
        "review_evidence_id":review_evidence_id,"investment_certified":False,"automatic_promotion":False}
