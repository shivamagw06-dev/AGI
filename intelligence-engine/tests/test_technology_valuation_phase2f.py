from __future__ import annotations
import pytest
from technology_valuation.answer import format_technology_answer
from technology_valuation.classification import classify_technology_subsector
from technology_valuation.outcomes import build_outcome_record
from technology_valuation.persistence import persist_telecom_certification,seed_telecom_model
from technology_valuation.research_context import technology_research_context
from technology_valuation.service import evaluate_technology_company
from technology_valuation.telecom_certification import certify_telecom
from app.tools.registry import plan_tools
AS_OF="2026-08-15"
def item(v,u="decimal"):return {"value":v,"unit":u,"currency":"INR","period":"FY2026","source_id":"telecom-filing","available_at":"2026-07-20"}
def inputs():return {"enterprise_value":item(900000,"INR million"),"revenue":item(180000,"INR million"),"ebitda":item(90000,"INR million"),"opening_subscribers":item(350,"million subscribers"),"closing_subscribers":item(364,"million subscribers"),"monthly_arpu":item(220,"INR/subscriber/month"),"churn":item(.025),"market_share":item(.36),"data_usage":item(25,"GB/subscriber/month"),"capex":item(36000,"INR million"),"net_debt":item(240000,"INR million"),"spectrum_liabilities":item(60000,"INR million"),"interest_expense":item(30000,"INR million"),"enterprise_revenue":item(36000,"INR million"),"fcf":item(18000,"INR million"),"terminal_ev_ebitda":item(8,"multiple"),"horizon_years":item(5,"years"),"agi_ebitda_growth_expectation":item(.12),"target_ev_ebitda":item(10,"multiple"),"tariff_change":item(.10),"realization":item(.75),"incremental_margin":item(.70)}
def scenarios():return {"BEAR":{"tariff_change":.05,"realization":.5,"incremental_margin":.6,"target_ev_ebitda":8},"BASE":{"tariff_change":.1,"realization":.75,"incremental_margin":.7,"target_ev_ebitda":10},"BULL":{"tariff_change":.15,"realization":.9,"incremental_margin":.75,"target_ev_ebitda":11}}
def pack():return {"inputs":inputs(),"as_of":AS_OF,"peers":[{"ev_ebitda":8},{"ev_ebitda":12}],"history":[{"ev_ebitda":7,"available_at":"2024-01-01"},{"ev_ebitda":11,"available_at":"2025-01-01"}],"scenarios":scenarios(),"warehouse_receipt_id":"receipt","independent_verification_id":"verify"}
def test_telecom_route_math_answer():
    r=evaluate_technology_company(company={"symbol":"BHARTIARTL","technology_subsector":"WIRELESS_TELECOM"},inputs=inputs(),as_of=AS_OF,peers=pack()["peers"],history=pack()["history"],scenarios=scenarios());assert r["status"]=="OPERATIONAL_NOT_CERTIFIED" and r["valuation"]["current_ev_ebitda"]==10;assert r["kpis"]["subscriber_growth"]==pytest.approx(.04);assert r["kpis"]["net_debt_ebitda"]==pytest.approx(3.3333333333);assert "10.00x EBITDA" in format_technology_answer(r)["direct_conclusion"]
def test_telecom_fail_closed():
    assert classify_technology_subsector({"canonical_industry":"telecom"})["model_family"]=="TELECOM";future=inputs();future["monthly_arpu"]["available_at"]="2027-01-01";assert evaluate_technology_company(company={"technology_subsector":"TELECOM"},inputs=future,as_of=AS_OF)["status"]=="POINT_IN_TIME_VIOLATION";bad=inputs();bad["realization"]["value"]=1.2;assert evaluate_technology_company(company={"technology_subsector":"TELECOM"},inputs=bad,as_of=AS_OF)["status"]=="VALIDATION_FAILED"
def test_telecom_certification_cohort_and_integrations():
    packs={s:pack() for s in ("BHARTIARTL","IDEA","TATACOMM")};r=certify_telecom(packs);assert r["passed_gates"]==23 and r["investment_certified"] is False;calls=[]
    def transport(method,table,**kwargs):calls.append((method,table,kwargs))
    assert seed_telecom_model(transport=transport)["certified"] is False;assert persist_telecom_certification(r,transport=transport)["investment_certified"] is False;assert technology_research_context("BHARTIARTL",loader=lambda _:{"master":{"technology_subsector":"TELECOM"}})["sector_name"]=="Telecom";o=build_outcome_record(company_id="BHARTIARTL",metric="arpu",predicted_value=220,actual_value=225,predicted_at="2026-04-01T00:00:00Z",evaluated_at="2026-07-20T00:00:00Z",source_id="filing");assert o["subsector"]=="TELECOM";names={x["name"] for x in plan_tools("How does a telecom tariff increase affect ARPU and equity value?",ticker_hint="BHARTIARTL")["tools"]};assert "GET_TECHNOLOGY_VALUATION" in names
