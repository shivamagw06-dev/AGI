"""Twenty-gate commercial-bank certification; no self-certification."""
from __future__ import annotations
from typing import Any
from financials_valuation.banking import BANKING_MODEL, BANK_KPIS
from financials_valuation.answer import format_bank_answer
from financials_valuation.service import evaluate_bank

REQUIRED_COMPANIES = ("HDFCBANK", "ICICIBANK", "AXISBANK", "SBIN")
GATES = ("classification","business_model","kpi","financial_statement","causal_transmission",
 "method_selection","multiple_justification","reverse_valuation","historical_valuation","peer_valuation",
 "scenario","sensitivity","point_in_time","missing_data","contradiction","accounting_quality",
 "regulatory_capital","client_answer","adversarial","provenance")

def certify_banking(company_packs: dict[str, dict[str, Any]], *, authorized_reviewer: str | None = None,
                    reviewer_authorized: bool = False, review_evidence_id: str | None = None) -> dict[str, Any]:
    results = {}
    for symbol in REQUIRED_COMPANIES:
        pack = company_packs.get(symbol)
        if not pack:
            results[symbol] = {"status":"DATA_UNAVAILABLE"}; continue
        results[symbol] = evaluate_bank(company={"symbol":symbol, **(pack.get("company") or {})},
            inputs=pack.get("inputs") or {}, as_of=str(pack.get("as_of") or ""),
            peers=pack.get("peers"), history=pack.get("history"), scenarios=pack.get("scenarios"))
    all_operational = all((results.get(x) or {}).get("status") == "OPERATIONAL_NOT_CERTIFIED" for x in REQUIRED_COMPANIES)
    sample = next((x for x in results.values() if x.get("status") == "OPERATIONAL_NOT_CERTIFIED"), {})
    probe_pack = next((company_packs.get(x) for x in REQUIRED_COMPANIES if company_packs.get(x)), None) or {}
    probe_inputs = dict(probe_pack.get("inputs") or {})
    missing_probe = dict(probe_inputs); missing_probe.pop("roe", None)
    adversarial_probe = {key: dict(value) for key, value in probe_inputs.items() if isinstance(value, dict)}
    if "credit_cost" in adversarial_probe:
        adversarial_probe["credit_cost"]["value"] = -0.01
    pit_probe = {key: dict(value) for key, value in probe_inputs.items() if isinstance(value, dict)}
    if "market_price" in pit_probe:
        pit_probe["market_price"]["available_at"] = "9999-12-31"
    probe_company = {"financial_subsector": "COMMERCIAL_BANK"}
    gates = {
      "classification": all_operational,
      "business_model": bool(BANKING_MODEL.economic_structure),
      "kpi": len(BANK_KPIS) >= 20,
      "financial_statement": all_operational,
      "causal_transmission": any("->" in rel for k in BANK_KPIS for rel in k.causal_relationships),
      "method_selection": BANKING_MODEL.valuation_methods[0].method == "PRICE_TO_BOOK",
      "multiple_justification": all(x.reason_for_use for x in BANKING_MODEL.valuation_methods),
      "reverse_valuation": all((results.get(x) or {}).get("market_expectations",{}).get("implied_roe") is not None for x in REQUIRED_COMPANIES),
      "historical_valuation": all((results.get(x) or {}).get("valuation",{}).get("historical_median_pb") is not None for x in REQUIRED_COMPANIES),
      "peer_valuation": all((results.get(x) or {}).get("valuation",{}).get("peer_median_pb") is not None for x in REQUIRED_COMPANIES),
      "scenario": all(all(v.get("status") == "SUCCESS" for v in (results.get(x) or {}).get("scenarios",{}).values()) for x in REQUIRED_COMPANIES),
      "sensitivity": all(len((results.get(x) or {}).get("sensitivity",{}).get("roe_x_cost_of_equity", [])) == 9 for x in REQUIRED_COMPANIES),
      "point_in_time": bool(pit_probe) and evaluate_bank(company=probe_company, inputs=pit_probe, as_of="2026-08-15").get("status") == "POINT_IN_TIME_VIOLATION",
      "missing_data": bool(missing_probe) and evaluate_bank(company=probe_company, inputs=missing_probe, as_of="2026-08-15").get("status") == "DATA_UNAVAILABLE",
      "contradiction": all(not (results.get(x) or {}).get("risk_flags") for x in REQUIRED_COMPANIES),
      "accounting_quality": all("normalized_eps" in (company_packs.get(x) or {}).get("inputs",{}) for x in REQUIRED_COMPANIES),
      "regulatory_capital": all("cet1" in (company_packs.get(x) or {}).get("inputs",{}) for x in REQUIRED_COMPANIES),
      "client_answer": all(format_bank_answer(results.get(x) or {}).get("execution_eligible") is False for x in REQUIRED_COMPANIES),
      "adversarial": bool(adversarial_probe) and evaluate_bank(company=probe_company, inputs=adversarial_probe, as_of="2026-08-15", scenarios={}).get("status") == "VALIDATION_FAILED",
      "provenance": all(len((results.get(x) or {}).get("provenance",{})) == 9 for x in REQUIRED_COMPANIES),
    }
    passed=sum(gates.values())
    external_approval = bool(authorized_reviewer and reviewer_authorized and review_evidence_id)
    status="PASSED" if passed == len(GATES) and external_approval else "IN_PROGRESS" if passed else "FAILED"
    return {"sector_id":BANKING_MODEL.sector_id,"model_version":BANKING_MODEL.version,
            "certification_status":status,"passed_gates":passed,"total_gates":len(GATES),
            "gates":gates,"companies":results,"authorized_reviewer":authorized_reviewer,
            "reviewer_authorized": reviewer_authorized, "review_evidence_id": review_evidence_id,
            "automatic_promotion":False}
