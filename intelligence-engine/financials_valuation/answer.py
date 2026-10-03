"""Client-safe bank research answer assembly from governed valuation output."""
from __future__ import annotations
from typing import Any


def format_bank_answer(result: dict[str, Any]) -> dict[str, Any]:
    status = result.get("status")
    if status != "OPERATIONAL_NOT_CERTIFIED":
        return {
            "status": status or "DATA_UNAVAILABLE",
            "answer": "AGI cannot form a reliable bank valuation view from the available point-in-time evidence.",
            "limitations": result.get("input_issues") or result.get("risk_flags") or ["Evidence gates did not pass."],
            "execution_eligible": False,
        }
    valuation = result["valuation"]
    expectations = result["market_expectations"]
    symbol = result.get("company_id") or "The bank"
    direction = {
        "EXPECTATIONS_STRETCHED": "the market price appears to require stronger delivery than the base assumptions",
        "EXPECTATIONS_FAVORABLE": "the market price embeds less demanding assumptions than the base case",
        "EXPECTATIONS_NEUTRAL": "the market price is broadly aligned with the base assumptions",
    }.get(expectations.get("classification"), "the market-implied expectations remain uncertain")
    return {
        "status": "RESEARCH_ONLY",
        "answer": (
            f"{symbol} trades at {valuation['current_pb']:.2f}x book and "
            f"{valuation['current_pe']:.2f}x normalized earnings. Against AGI's explicit ROE, growth and "
            f"cost-of-equity assumptions, justified P/B is {valuation['justified_pb']:.2f}x; {direction}."
        ),
        "why_it_matters": (
            "For a bank, sustainable ROE, funding quality, credit costs and regulatory capital determine "
            "whether book value compounds and deserves a premium. A low multiple alone is not evidence of value."
        ),
        "what_to_monitor": result.get("monitoring", []),
        "risks": result.get("risk_flags", []),
        "evidence_gaps": result.get("evidence_gaps", []),
        "confidence": result.get("confidence", "LOW"),
        "as_of": result.get("as_of"),
        "limitations": "Research context, not personalized advice. The model is operational but not investment-certified.",
        "execution_eligible": False,
    }


def format_financial_answer(result: dict[str, Any]) -> dict[str, Any]:
    if (result.get("classification") or {}).get("subsector") == "COMMERCIAL_BANK":
        return format_bank_answer(result)
    if result.get("status") != "OPERATIONAL_NOT_CERTIFIED":
        return {"status":result.get("status") or "DATA_UNAVAILABLE",
                "answer":"AGI cannot form a reliable sector-specific valuation view from the available point-in-time evidence.",
                "limitations":result.get("input_issues") or result.get("risk_flags") or ["Evidence gates did not pass."],
                "execution_eligible":False}
    valuation = result["valuation"]
    model = result.get("model") or {}
    company = result.get("company_id") or "The company"
    return {"status":"RESEARCH_ONLY",
        "answer":f"{company} is evaluated as {model.get('sector_name')} using {valuation['primary_method']}; the current primary valuation output is {valuation['primary_value']:.2f}. This is a sector-specific research measure, not a recommendation.",
        "why_it_matters":model.get("economic_structure"), "what_to_monitor":result.get("monitoring") or [],
        "risks":result.get("risk_flags") or [], "evidence_gaps":result.get("evidence_gaps") or [],
        "confidence":result.get("confidence") or "LOW", "as_of":result.get("as_of"),
        "limitations":"Operational research model; not investment-certified and not personalized advice.",
        "execution_eligible":False}
