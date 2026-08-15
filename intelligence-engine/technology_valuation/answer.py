"""Concise client-safe Phase 2A answer assembly."""
from __future__ import annotations
from typing import Any


def format_technology_answer(result: dict[str, Any]) -> dict[str, Any]:
    if result.get("status")!="OPERATIONAL_NOT_CERTIFIED":
        return {"status":result.get("status") or "DATA_UNAVAILABLE","answer":"AGI cannot form a reliable IT-services valuation view from the available point-in-time evidence.","limitations":result.get("input_issues") or result.get("risk_flags") or ["Evidence gates did not pass."],"execution_eligible":False}
    company=result.get("company_id") or "The company"; valuation=result["valuation"]; expectations=result["market_expectations"]; kpis=result["kpis"]
    expectation_text={"EXPECTATIONS_STRETCHED":"the market requires stronger growth than AGI's base expectation","EXPECTATIONS_FAVORABLE":"the market embeds less growth than AGI's base expectation","EXPECTATIONS_NEUTRAL":"market-implied growth is broadly aligned with AGI's base expectation"}.get(expectations.get("classification"),"market expectations cannot yet be resolved")
    return {"status":"RESEARCH_ONLY","direct_conclusion":f"{company} trades at {valuation['current_pe']:.2f}x normalized earnings and {valuation['ev_ebitda']:.2f}x EBITDA; {expectation_text}.",
        "business_quality":"IT-services value depends on durable client demand, execution, pricing, utilization and cash conversion rather than the headline multiple alone.",
        "growth":f"Book-to-bill is {kpis['book_to_bill']:.2f}x; signed contract value must still convert into reported revenue.",
        "margin_economics":f"EBIT margin is {kpis['ebit_margin']:.1%}. Utilization, billing rates, wages, attrition, delivery mix and AI sharing determine its durability.",
        "cash_flow":f"FCF margin is {kpis['fcf_margin']:.1%}.","valuation":valuation,"market_implied_expectations":expectations,
        "scenarios":result.get("scenarios"),"key_risks":result.get("model",{}).get("valuation_risks") or [],
        "ai_impact":result.get("business_economics",{}).get("ai_analysis"),"what_to_monitor":result.get("monitoring") or [],
        "confidence":result.get("confidence"),"as_of":result.get("as_of"),"sources":sorted({v.get("source_id") for v in (result.get("provenance") or {}).values() if v.get("source_id")}),
        "limitations":"Operational research curriculum, not investment-certified or personalized advice.","execution_eligible":False}
