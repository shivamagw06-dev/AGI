from __future__ import annotations
import pytest
from financial_engine import calculate
from technology_valuation.answer import format_technology_answer
from technology_valuation.classification import classify_technology_subsector
from technology_valuation.consumer_certification import certify_consumer_digital
from technology_valuation.outcomes import build_outcome_record
from technology_valuation.persistence import persist_consumer_certification,seed_consumer_model
from technology_valuation.research_context import technology_research_context
from technology_valuation.service import evaluate_technology_company
from app.tools.registry import plan_tools

AS_OF="2026-08-15"
def item(v,unit="decimal"): return {"value":v,"unit":unit,"currency":"INR","period":"FY2026","source_id":"filing-digital","available_at":"2026-07-20"}
def inputs(): return {"enterprise_value":item(60000,"INR million"),"net_revenue":item(12000,"INR million"),"opening_net_revenue":item(10000,"INR million"),"closing_net_revenue":item(12000,"INR million"),"net_sales":item(12000,"INR million"),"gross_profit":item(4800,"INR million"),"cogs":item(7200,"INR million"),"opening_inventory":item(1600,"INR million"),"closing_inventory":item(2000,"INR million"),"net_orders":item(40,"million orders"),"gross_orders":item(44,"million orders"),"returned_orders":item(4,"million orders"),"active_customers":item(10,"million customers"),"new_customers":item(2,"million customers"),"repeat_rate":item(.62),"contribution_profit":item(1200,"INR million"),"sales_marketing_spend":item(1800,"INR million"),"advertising_revenue":item(1200,"INR million"),"monetizable_users":item(20,"million users"),"fcf":item(600,"INR million"),"terminal_ev_revenue":item(3,"multiple"),"horizon_years":item(5,"years"),"agi_revenue_growth_expectation":item(.18),"target_ev_revenue":item(4,"multiple")}
def scenarios(): return {"BEAR":{"revenue_growth":.08,"target_ev_revenue":3},"BASE":{"revenue_growth":.18,"target_ev_revenue":4},"BULL":{"revenue_growth":.28,"target_ev_revenue":5}}
def pack(): return {"inputs":inputs(),"as_of":AS_OF,"peers":[{"ev_sales":4},{"ev_sales":6}],"history":[{"ev_sales":3,"available_at":"2024-01-01"},{"ev_sales":5,"available_at":"2025-01-01"}],"scenarios":scenarios(),"warehouse_receipt_id":"receipt","independent_verification_id":"verify"}

def test_digital_formulas_and_scenario():
    x=inputs(); growth=calculate(calculation_id="DIGITAL_NET_REVENUE_GROWTH",inputs={k:x[k] for k in ("opening_net_revenue","closing_net_revenue")},as_of=AS_OF)
    assert growth["status"]=="SUCCESS" and growth["calculated_value"]==pytest.approx(.2)
    s=calculate(calculation_id="DIGITAL_SCENARIO_EV",inputs={"net_revenue":x["net_revenue"],"revenue_growth":item(.2),"target_ev_revenue":item(4)},as_of=AS_OF)
    assert s["status"]=="SUCCESS" and s["calculated_value"]==57600 and "SCENARIO_NOT_FACT" in s["warnings"]

def test_digital_route_and_client_answer():
    r=evaluate_technology_company(company={"symbol":"SHOP","technology_subsector":"DIGITAL_COMMERCE"},inputs=inputs(),as_of=AS_OF,peers=pack()["peers"],history=pack()["history"],scenarios=scenarios())
    assert r["status"]=="OPERATIONAL_NOT_CERTIFIED" and r["valuation"]["primary_method"]=="EV_SALES"
    assert r["kpis"]["gross_margin"]==.4 and r["kpis"]["return_rate"]==4/44
    assert r["business_economics"]["accounting_model"]["gmv_is_not_revenue"] is True
    a=format_technology_answer(r); assert a["status"]=="RESEARCH_ONLY" and "5.00x net revenue" in a["direct_conclusion"]

def test_digital_fail_closed_and_classification():
    assert classify_technology_subsector({"canonical_industry":"ecommerce"})["model_family"]=="CONSUMER_INTERNET_DIGITAL_COMMERCE"
    missing=inputs(); missing.pop("net_revenue"); assert evaluate_technology_company(company={"technology_subsector":"DIGITAL_COMMERCE"},inputs=missing,as_of=AS_OF)["status"]=="DATA_UNAVAILABLE"
    future=inputs(); future["net_revenue"]["available_at"]="2027-01-01"; assert evaluate_technology_company(company={"technology_subsector":"DIGITAL_COMMERCE"},inputs=future,as_of=AS_OF)["status"]=="POINT_IN_TIME_VIOLATION"
    bad=inputs(); bad["gross_profit"]["value"]=13000; assert evaluate_technology_company(company={"technology_subsector":"DIGITAL_COMMERCE"},inputs=bad,as_of=AS_OF)["status"]=="VALIDATION_FAILED"

def test_digital_certification_persistence_context_outcome_and_tool():
    packs={"SHOPA":pack(),"SHOPB":pack()}; result=certify_consumer_digital(packs)
    assert result["passed_gates"]==23 and result["certification_status"]=="IN_PROGRESS" and result["investment_certified"] is False
    approved=certify_consumer_digital(packs,authorized_reviewer="committee",reviewer_authorized=True,review_evidence_id="review")
    calls=[]
    def transport(method,table,**kwargs): calls.append((method,table,kwargs))
    assert seed_consumer_model(transport=transport)["certified"] is False
    assert persist_consumer_certification(approved,transport=transport)["investment_certified"] is False
    assert technology_research_context("SHOP",loader=lambda _:{"master":{"technology_subsector":"DIGITAL_COMMERCE"}})["sector_name"]=="Consumer Internet and Digital Commerce"
    o=build_outcome_record(company_id="SHOP",metric="return_rate",predicted_value=.1,actual_value=.12,predicted_at="2026-04-01T00:00:00Z",evaluated_at="2026-07-20T00:00:00Z",source_id="filing")
    assert o["subsector"]=="CONSUMER_INTERNET_DIGITAL_COMMERCE" and o["trusted_update_allowed"] is False
    names={x["name"] for x in plan_tools("Is this ecommerce valuation justified by repeat rate and inventory turns?",ticker_hint="SHOP")["tools"]}
    assert "GET_TECHNOLOGY_VALUATION" in names and "GET_FINANCIAL_VALUATION" not in names
