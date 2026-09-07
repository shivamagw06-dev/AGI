"""Commercial-bank valuation assembly over AFE, policy and CRE."""
from __future__ import annotations
from datetime import date
from statistics import median
from typing import Any
from financial_engine import calculate
from financials_valuation.banking import BANKING_MODEL
from financials_valuation.classification import classify_financial_subsector
from causal_research_engine.service import ask_context

CRITICAL = ("market_price", "book_value_per_share", "roe", "growth", "cost_of_equity", "normalized_eps",
            "gnpa", "credit_cost", "cet1")

def _cell_issue(inputs: dict[str, Any], key: str, as_of: str) -> str | None:
    item = inputs.get(key)
    if isinstance(item, (int, float)) and not isinstance(item, bool):
        return "PROVENANCE_REQUIRED"
    if not isinstance(item, dict) or not isinstance(item.get("value"), (int, float)): return "MISSING_OR_INVALID"
    available = str(item.get("available_at") or "")
    if not available: return "AVAILABLE_AT_REQUIRED"
    if available[:10] > as_of[:10]: return "POINT_IN_TIME_VIOLATION"
    if not item.get("source_id") or not item.get("period"): return "PROVENANCE_REQUIRED"
    return None

def _calc(cid: str, values: dict[str, Any], as_of: str, assumptions=()) -> dict[str, Any]:
    return calculate(calculation_id=cid, inputs=values, as_of=as_of,
                     assumptions=[{"text": x} for x in assumptions])

def _percentile(value: float, series: list[float]) -> float | None:
    if not series: return None
    return round(100 * sum(x <= value for x in series) / len(series), 2)

def evaluate_bank(*, company: dict[str, Any], inputs: dict[str, Any], as_of: str,
                  peers: list[dict[str, Any]] | None = None, history: list[dict[str, Any]] | None = None,
                  scenarios: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    try:
        date.fromisoformat(str(as_of)[:10])
    except (TypeError, ValueError):
        return {"status": "DATA_UNAVAILABLE", "reason": "A valid ISO as-of date is required.",
                "execution_eligible": False, "certified": False}
    classification = classify_financial_subsector(company)
    if classification.get("subsector") != "COMMERCIAL_BANK":
        return {"status": "CLASSIFICATION_UNAVAILABLE", "classification": classification,
                "execution_eligible": False, "certified": False}
    issues = {key: issue for key in CRITICAL if (issue := _cell_issue(inputs, key, as_of))}
    if issues:
        status = "POINT_IN_TIME_VIOLATION" if "POINT_IN_TIME_VIOLATION" in issues.values() else "DATA_UNAVAILABLE"
        return {"status": status, "input_issues": issues, "missing_inputs": list(issues), "as_of": as_of,
                "classification": classification, "execution_eligible": False, "certified": False}
    domain_issues = []
    for key in ("market_price", "book_value_per_share", "normalized_eps"):
        if float(inputs[key]["value"]) <= 0:
            domain_issues.append(f"{key.upper()}_MUST_BE_POSITIVE")
    for key in ("gnpa", "credit_cost", "cet1"):
        if not 0 <= float(inputs[key]["value"]) <= 1:
            domain_issues.append(f"{key.upper()}_OUT_OF_DECIMAL_RANGE")
    if domain_issues:
        return {"status": "VALIDATION_FAILED", "risk_flags": domain_issues, "as_of": as_of,
                "classification": classification, "execution_eligible": False, "certified": False}
    price = inputs["market_price"]; bvps = inputs["book_value_per_share"]
    roe = inputs["roe"]; growth = inputs["growth"]; coe = inputs["cost_of_equity"]
    eps = inputs["normalized_eps"]
    current_pb = _calc("BANK_PRICE_TO_BOOK", {"market_price": price, "book_value_per_share": bvps}, as_of)
    justified_pb = _calc("JUSTIFIED_PB", {"roe": roe, "growth": growth, "cost_of_equity": coe}, as_of,
                         ("ROE, growth and cost of equity are explicit inputs",))
    residual = _calc("BANK_RESIDUAL_INCOME", {"book_value": bvps, "roe": roe, "growth": growth, "cost_of_equity": coe}, as_of)
    current_pe = _calc("BANK_PRICE_TO_EARNINGS", {"market_price": price, "normalized_eps": eps}, as_of)
    calcs = {"current_pb": current_pb, "current_pe": current_pe,
             "justified_pb": justified_pb, "residual_income": residual}
    failed = [key for key, row in calcs.items() if row.get("status") != "SUCCESS"]
    if failed:
        return {"status": "VALUATION_UNAVAILABLE", "failed_calculations": failed, "calculations": calcs,
                "as_of": as_of, "execution_eligible": False, "certified": False}
    implied_roe = _calc("BANK_IMPLIED_ROE", {"price_to_book": {**price, "value": current_pb["calculated_value"]},
        "cost_of_equity": coe, "growth": growth}, as_of)
    implied_growth = _calc("BANK_IMPLIED_GROWTH", {"roe": roe,
        "price_to_book": {**price, "value": current_pb["calculated_value"]}, "cost_of_equity": coe}, as_of)
    peer_pb = [float(x["pb"]) for x in (peers or []) if isinstance(x.get("pb"), (int,float)) and x.get("subsector") == "COMMERCIAL_BANK"]
    history_pb = [float(x["pb"]) for x in (history or []) if isinstance(x.get("pb"), (int,float)) and str(x.get("available_at") or "")[:10] <= as_of[:10]]
    scenario_rows = _scenarios(inputs, as_of, scenarios or {})
    sensitivity = _sensitivity(inputs, as_of)
    market_pb = float(current_pb["calculated_value"]); fair_pb = float(justified_pb["calculated_value"])
    expectations = "EXPECTATIONS_STRETCHED" if market_pb > fair_pb * 1.15 else "EXPECTATIONS_FAVORABLE" if market_pb < fair_pb * .85 else "EXPECTATIONS_NEUTRAL"
    risk_flags = []
    status = "OPERATIONAL_NOT_CERTIFIED"
    company_id = company.get("symbol") or company.get("company_id")
    causal = ask_context(entity=str(company_id), question="What drives sustainable bank value?",
                         industry="commercial banking", analysis_as_of=as_of)
    return {"status": status, "company_id": company_id, "as_of": as_of,
        "classification": classification, "model": BANKING_MODEL.to_dict(),
        "business_quality": "REQUIRES_SEPARATE_ASSESSMENT", "financial_quality": "REQUIRES_NORMALIZATION",
        "valuation": {"current_pb": market_pb, "current_pe": current_pe["display_value"],
                      "justified_pb": fair_pb, "residual_income_value_per_share": residual["calculated_value"],
                      "peer_median_pb": median(peer_pb) if peer_pb else None,
                      "historical_median_pb": median(history_pb) if history_pb else None,
                      "historical_percentile": _percentile(market_pb, history_pb)},
        "market_expectations": {"classification": expectations,
            "implied_roe": implied_roe.get("calculated_value") if implied_roe.get("status") == "SUCCESS" else None,
            "implied_growth": implied_growth.get("calculated_value") if implied_growth.get("status") == "SUCCESS" else None},
        "scenarios": scenario_rows, "sensitivity": sensitivity, "risk_flags": risk_flags,
        "causal_context": causal.get("causal_research", {}),
        "monitoring": ["deposit_growth","casa","nim","slippage","credit_cost","roa","roe","cet1"],
        "calculations": {**calcs, "implied_roe": implied_roe, "implied_growth": implied_growth},
        "provenance": {key: {k: inputs[key].get(k) for k in ("source_id","available_at","period","unit","currency")} for key in CRITICAL},
        "confidence": "LOW" if not peer_pb or not history_pb else "MEDIUM",
        "evidence_gaps": [x for x, present in (("peer_valuation",bool(peer_pb)),("historical_valuation",bool(history_pb))) if not present],
        "investment_attractiveness": "RESEARCH_ONLY", "execution_eligible": False, "certified": False}

def _scenario_value(base: dict[str, Any], as_of: str, assumptions: dict[str, Any]) -> dict[str, Any]:
    needed = ("roe","growth","cost_of_equity")
    if any(key not in assumptions for key in needed): return {"status":"DATA_UNAVAILABLE", "missing":[k for k in needed if k not in assumptions]}
    wrapped = {key: {**base[key], "value": float(assumptions[key])} for key in needed}
    result = _calc("JUSTIFIED_PB", wrapped, as_of, ("Scenario, not reported fact",))
    return {"status": result.get("status"), "epistemic_label":"SCENARIO", "assumptions": assumptions,
            "justified_pb": result.get("calculated_value"), "probability": None}

def _scenarios(inputs, as_of, supplied):
    return {name: _scenario_value(inputs, as_of, supplied.get(name) or {}) for name in ("BEAR","BASE","BULL")}

def _sensitivity(inputs, as_of):
    roe=float(inputs["roe"]["value"]); coe=float(inputs["cost_of_equity"]["value"]); growth=float(inputs["growth"]["value"])
    rows=[]
    for r in (roe-.02, roe, roe+.02):
        for c in (coe-.01, coe, coe+.01):
            wrapped={"roe":{**inputs["roe"],"value":r},"growth":inputs["growth"],"cost_of_equity":{**inputs["cost_of_equity"],"value":c}}
            result=_calc("JUSTIFIED_PB",wrapped,as_of,("Sensitivity, not forecast",))
            rows.append({"roe":r,"cost_of_equity":c,"growth":growth,"justified_pb":result.get("calculated_value"),"status":result.get("status")})
    return {"dominant_variables":["ROE","cost_of_equity","growth"],"roe_x_cost_of_equity":rows}
