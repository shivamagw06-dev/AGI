from __future__ import annotations
from financial_engine import calculate
from technology_valuation.answer import format_technology_answer
from technology_valuation.classification import classify_technology_subsector
from technology_valuation.outcomes import build_outcome_record
from technology_valuation.persistence import persist_platform_certification,seed_platform_model
from technology_valuation.platform_certification import certify_platform_marketplaces
from technology_valuation.research_context import technology_research_context
from technology_valuation.service import evaluate_technology_company
from app.tools.registry import plan_tools

AS_OF="2026-08-15"
def item(v,unit="decimal"): return {"value":v,"unit":unit,"currency":"INR","period":"FY2026","source_id":"filing-platform","available_at":"2026-07-20"}
def inputs(): return {"enterprise_value":item(60000,"INR million"),"gmv":item(100000,"INR million"),"opening_gmv":item(80000,"INR million"),"closing_gmv":item(100000,"INR million"),"revenue":item(12000,"INR million"),"gross_profit":item(8000,"INR million"),"orders":item(50,"million orders"),"active_buyers":item(10,"million buyers"),"active_sellers":item(.5,"million sellers"),"contribution_profit":item(1800,"INR million"),"sales_marketing_spend":item(2000,"INR million"),"new_customers":item(2,"million customers"),"repeat_rate":item(.65),"seller_concentration":item(.12),"refund_cancellation_rate":item(.05),"fcf":item(900,"INR million"),"terminal_ev_revenue":item(3,"multiple"),"horizon_years":item(5,"years"),"agi_gmv_growth_expectation":item(.20),"target_ev_revenue":item(4,"multiple")}
def scenarios(): return {"BEAR":{"gmv_growth":.10,"take_rate":.10,"target_ev_revenue":3},"BASE":{"gmv_growth":.20,"take_rate":.12,"target_ev_revenue":4},"BULL":{"gmv_growth":.30,"take_rate":.13,"target_ev_revenue":5}}
def pack(): return {"inputs":inputs(),"as_of":AS_OF,"peers":[{"ev_sales":4},{"ev_sales":6}],"history":[{"ev_sales":3,"available_at":"2024-01-01"},{"ev_sales":5,"available_at":"2025-01-01"}],"scenarios":scenarios(),"warehouse_receipt_id":"receipt","independent_verification_id":"verify"}

def test_platform_formulas_and_scenario_label():
    take=calculate(calculation_id="PLATFORM_TAKE_RATE",inputs={k:inputs()[k] for k in ("revenue","gmv")},as_of=AS_OF)
    assert take["status"]=="SUCCESS" and take["calculated_value"]==.12
    s=calculate(calculation_id="PLATFORM_SCENARIO_EV",inputs={"gmv":inputs()["gmv"],"gmv_growth":item(.2),"take_rate":item(.12),"target_ev_revenue":item(4)},as_of=AS_OF)
    assert s["status"]=="SUCCESS" and s["calculated_value"]==57600 and "SCENARIO_NOT_FACT" in s["warnings"]

def test_platform_route_answer_and_network_effect_guard():
    r=evaluate_technology_company(company={"symbol":"PLAT","technology_subsector":"MARKETPLACE"},inputs=inputs(),as_of=AS_OF,peers=pack()["peers"],history=pack()["history"],scenarios=scenarios())
    assert r["status"]=="OPERATIONAL_NOT_CERTIFIED" and r["valuation"]["primary_method"]=="EV_SALES"
    assert r["kpis"]["take_rate"]==.12 and r["business_economics"]["network_effect"]["user_growth_is_not_proof"] is True
    a=format_technology_answer(r); assert a["status"]=="RESEARCH_ONLY" and "5.00x revenue" in a["direct_conclusion"]

def test_platform_fail_closed():
    assert classify_technology_subsector({"canonical_industry":"marketplace"})["model_family"]=="INTERNET_PLATFORMS_MARKETPLACES"
    missing=inputs(); missing.pop("gmv"); assert evaluate_technology_company(company={"technology_subsector":"MARKETPLACE"},inputs=missing,as_of=AS_OF)["status"]=="DATA_UNAVAILABLE"
    future=inputs(); future["gmv"]["available_at"]="2027-01-01"; assert evaluate_technology_company(company={"technology_subsector":"MARKETPLACE"},inputs=future,as_of=AS_OF)["status"]=="POINT_IN_TIME_VIOLATION"
    bad=inputs(); bad["revenue"]["value"]=120000; assert evaluate_technology_company(company={"technology_subsector":"MARKETPLACE"},inputs=bad,as_of=AS_OF)["status"]=="VALIDATION_FAILED"

def test_platform_certification_persistence_context_outcome_and_tool():
    packs={"PLATA":pack(),"PLATB":pack()}; result=certify_platform_marketplaces(packs)
    assert result["passed_gates"]==23 and result["certification_status"]=="IN_PROGRESS" and result["investment_certified"] is False
    approved=certify_platform_marketplaces(packs,authorized_reviewer="committee",reviewer_authorized=True,review_evidence_id="review")
    calls=[]
    def transport(method,table,**kwargs): calls.append((method,table,kwargs))
    assert seed_platform_model(transport=transport)["certified"] is False
    assert persist_platform_certification(approved,transport=transport)["investment_certified"] is False
    assert technology_research_context("PLAT",loader=lambda _:{"master":{"technology_subsector":"MARKETPLACE"}})["sector_name"]=="Internet Platforms and Marketplaces"
    o=build_outcome_record(company_id="PLAT",metric="take_rate",predicted_value=.12,actual_value=.11,predicted_at="2026-04-01T00:00:00Z",evaluated_at="2026-07-20T00:00:00Z",source_id="filing")
    assert o["subsector"]=="INTERNET_PLATFORMS_MARKETPLACES" and o["trusted_update_allowed"] is False
    names={x["name"] for x in plan_tools("Is this marketplace valuation justified by GMV and take rate?",ticker_hint="PLAT")["tools"]}
    assert "GET_TECHNOLOGY_VALUATION" in names and "GET_FINANCIAL_VALUATION" not in names
