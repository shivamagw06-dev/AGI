"""Twenty-gate certification harness for non-bank financial curricula."""
from __future__ import annotations
from typing import Any

from financials_valuation.answer import format_financial_answer
from financials_valuation.nonbank_models import MODELS
from financials_valuation.nonbank_service import PROFILES, evaluate_financial_subsector

GATES = ("classification","business_model","kpi","financial_statement","causal_transmission",
 "method_selection","multiple_justification","reverse_valuation","historical_valuation","peer_valuation",
 "scenario","sensitivity","point_in_time","missing_data","contradiction","accounting_quality",
 "regulatory_capital","client_answer","adversarial","provenance")


def certify_subsector(subsector: str, company_packs: dict[str, dict[str, Any]], *,
                      authorized_reviewer: str | None = None, reviewer_authorized: bool = False,
                      review_evidence_id: str | None = None) -> dict[str, Any]:
    model = MODELS.get(subsector); profile = PROFILES.get(subsector)
    if model is None or profile is None:
        return {"certification_status":"FAILED", "reason":"unsupported_subsector", "automatic_promotion":False}
    results = {}
    for symbol, pack in company_packs.items():
        results[symbol] = evaluate_financial_subsector(company={"symbol":symbol, "financial_subsector":subsector},
            inputs=pack.get("inputs") or {}, as_of=str(pack.get("as_of") or ""), peers=pack.get("peers"),
            history=pack.get("history"), scenarios=pack.get("scenarios"))
    operational = len(results) >= 2 and all(row.get("status") == "OPERATIONAL_NOT_CERTIFIED" for row in results.values())
    sample_pack = next(iter(company_packs.values()), {}); sample_inputs = sample_pack.get("inputs") or {}
    sample_as_of = str(sample_pack.get("as_of") or "2026-08-15")
    missing = dict(sample_inputs); missing.pop(profile.required[0], None)
    future = {key:dict(value) for key,value in sample_inputs.items() if isinstance(value,dict)}
    if profile.required and profile.required[0] in future: future[profile.required[0]]["available_at"] = "9999-12-31"
    adversarial = {key:dict(value) for key,value in sample_inputs.items() if isinstance(value,dict)}
    if profile.positive and profile.positive[0] in adversarial: adversarial[profile.positive[0]]["value"] = -1
    gates = {
        "classification":operational, "business_model":bool(model.economic_structure), "kpi":len(model.key_kpis)>=4,
        "financial_statement":operational, "causal_transmission":all(k.causal_relationships for k in model.key_kpis),
        "method_selection":bool(model.valuation_methods), "multiple_justification":all(m.reason_for_use for m in model.valuation_methods),
        "reverse_valuation":operational and all((r.get("market_expectations") or {}).get("classification") != "DATA_INSUFFICIENT" for r in results.values()),
        "historical_valuation":operational and all((r.get("valuation") or {}).get("historical_median") is not None for r in results.values()),
        "peer_valuation":operational and all((r.get("valuation") or {}).get("peer_median") is not None for r in results.values()),
        "scenario":operational and all(all(v.get("status")=="SUCCESS" for v in (r.get("scenarios") or {}).values()) for r in results.values()),
        "sensitivity":operational and all(len((r.get("sensitivity") or {}).get("grid") or [])==9 for r in results.values()),
        "point_in_time":bool(future) and evaluate_financial_subsector(company={"financial_subsector":subsector},inputs=future,as_of=sample_as_of).get("status")=="POINT_IN_TIME_VIOLATION",
        "missing_data":bool(missing) and evaluate_financial_subsector(company={"financial_subsector":subsector},inputs=missing,as_of=sample_as_of).get("status")=="DATA_UNAVAILABLE",
        "contradiction":operational and all(not r.get("risk_flags") for r in results.values()),
        "accounting_quality":operational, "regulatory_capital":bool(model.regulatory_characteristics),
        "client_answer":operational and all(format_financial_answer(r).get("execution_eligible") is False for r in results.values()),
        "adversarial":bool(adversarial) and evaluate_financial_subsector(company={"financial_subsector":subsector},inputs=adversarial,as_of=sample_as_of).get("status")=="VALIDATION_FAILED",
        "provenance":operational and all(
            len(r.get("provenance") or {})==len(profile.required)
            and bool((company_packs.get(symbol) or {}).get("warehouse_receipt_id"))
            and bool((company_packs.get(symbol) or {}).get("independent_verification_id"))
            for symbol,r in results.items()),
    }
    passed=sum(gates.values()); external=bool(authorized_reviewer and reviewer_authorized and review_evidence_id)
    status="PASSED" if passed==20 and external else "IN_PROGRESS" if passed else "FAILED"
    return {"sector_id":model.sector_id,"subsector":subsector,"model_version":model.version,
            "certification_status":status,"passed_gates":passed,"total_gates":20,"gates":gates,
            "companies":results,"authorized_reviewer":authorized_reviewer,"reviewer_authorized":reviewer_authorized,
            "review_evidence_id":review_evidence_id,"automatic_promotion":False}
