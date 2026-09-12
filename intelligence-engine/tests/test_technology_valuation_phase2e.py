from __future__ import annotations
import pytest
from financial_engine import calculate
from technology_valuation.answer import format_technology_answer
from technology_valuation.classification import classify_technology_subsector
from technology_valuation.outcomes import build_outcome_record
from technology_valuation.persistence import persist_semiconductor_certification,seed_semiconductor_model
from technology_valuation.research_context import technology_research_context
from technology_valuation.semiconductor_certification import certify_semiconductors
from technology_valuation.service import evaluate_technology_company
from app.tools.registry import plan_tools
AS_OF="2026-08-15"
def item(v,u="decimal"):return {"value":v,"unit":u,"currency":"INR","period":"FY2026","source_id":"semi-filing","available_at":"2026-07-20"}
def inputs():return {"enterprise_value":item(60000,"INR million"),"revenue":item(10000,"INR million"),"opening_revenue":item(8000,"INR million"),"closing_revenue":item(10000,"INR million"),"ebitda":item(2000,"INR million"),"gross_profit":item(4000,"INR million"),"cogs":item(6000,"INR million"),"opening_inventory":item(1200,"INR million"),"closing_inventory":item(1800,"INR million"),"capacity":item(100,"million units"),"utilization":item(.8),"yield_rate":item(.9),"average_selling_price":item(120,"INR/unit"),"bookings":item(12000,"INR million"),"rnd_expense":item(1200,"INR million"),"capex":item(1800,"INR million"),"fcf":item(500,"INR million"),"terminal_ev_ebitda":item(20,"multiple"),"horizon_years":item(5,"years"),"agi_revenue_growth_expectation":item(.18),"target_ev_ebitda":item(25,"multiple")}
def scenarios():return {"BEAR":{"revenue_growth":.05,"ebitda_margin":.15,"target_ev_ebitda":18},"BASE":{"revenue_growth":.18,"ebitda_margin":.20,"target_ev_ebitda":25},"BULL":{"revenue_growth":.30,"ebitda_margin":.25,"target_ev_ebitda":30}}
def pack():return {"inputs":inputs(),"as_of":AS_OF,"peers":[{"ev_ebitda":25},{"ev_ebitda":35}],"history":[{"ev_ebitda":20,"available_at":"2024-01-01"},{"ev_ebitda":30,"available_at":"2025-01-01"}],"scenarios":scenarios(),"warehouse_receipt_id":"receipt","independent_verification_id":"verify"}
def test_semi_math_route_and_answer():
    x=inputs();r=evaluate_technology_company(company={"symbol":"CHIP","technology_subsector":"SEMICONDUCTOR"},inputs=x,as_of=AS_OF,peers=pack()["peers"],history=pack()["history"],scenarios=scenarios());assert r["status"]=="OPERATIONAL_NOT_CERTIFIED" and r["valuation"]["current_ev_ebitda"]==30;assert r["kpis"]["capacity_revenue"]==pytest.approx(8640);assert "30.00x EBITDA" in format_technology_answer(r)["direct_conclusion"]
def test_semi_fail_closed():
    assert classify_technology_subsector({"canonical_industry":"semiconductor"})["model_family"]=="SEMICONDUCTOR_RELATED";future=inputs();future["revenue"]["available_at"]="2027-01-01";assert evaluate_technology_company(company={"technology_subsector":"SEMICONDUCTOR"},inputs=future,as_of=AS_OF)["status"]=="POINT_IN_TIME_VIOLATION";bad=inputs();bad["yield_rate"]["value"]=1.2;assert evaluate_technology_company(company={"technology_subsector":"SEMICONDUCTOR"},inputs=bad,as_of=AS_OF)["status"]=="VALIDATION_FAILED"
def test_semi_certification_integrations():
    packs={"CHIPA":pack(),"CHIPB":pack()};r=certify_semiconductors(packs);assert r["passed_gates"]==23 and r["investment_certified"] is False;calls=[]
    def transport(method,table,**kwargs):calls.append((method,table,kwargs))
    assert seed_semiconductor_model(transport=transport)["certified"] is False;assert persist_semiconductor_certification(r,transport=transport)["investment_certified"] is False;assert technology_research_context("CHIP",loader=lambda _:{"master":{"technology_subsector":"SEMICONDUCTOR"}})["sector_name"]=="Semiconductor-related Businesses";o=build_outcome_record(company_id="CHIP",metric="yield_rate",predicted_value=.9,actual_value=.85,predicted_at="2026-04-01T00:00:00Z",evaluated_at="2026-07-20T00:00:00Z",source_id="filing");assert o["subsector"]=="SEMICONDUCTOR_RELATED";names={x["name"] for x in plan_tools("Is this semiconductor valuation justified by yield rate?",ticker_hint="CHIP")["tools"]};assert "GET_TECHNOLOGY_VALUATION" in names
