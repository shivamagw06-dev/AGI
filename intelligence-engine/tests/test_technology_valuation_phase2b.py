from __future__ import annotations
from financial_engine import calculate
from technology_valuation.answer import format_technology_answer
from technology_valuation.classification import classify_technology_subsector
from technology_valuation.outcomes import build_outcome_record
from technology_valuation.persistence import persist_software_saas_certification,seed_software_saas_model
from technology_valuation.research_context import technology_research_context
from technology_valuation.saas_certification import certify_software_saas
from technology_valuation.service import evaluate_technology_company
from app.tools.registry import plan_tools

AS_OF="2026-08-15"
def item(v,unit="decimal"): return {"value":v,"unit":unit,"currency":"INR","period":"FY2026","source_id":"filing-saas","available_at":"2026-07-20"}
def inputs(): return {"enterprise_value":item(120000,"INR million"),"arr":item(10000,"INR million"),"opening_arr":item(8000,"INR million"),"closing_arr":item(10000,"INR million"),
    "churned_arr":item(400,"INR million"),"contraction_arr":item(200,"INR million"),"expansion_arr":item(1600,"INR million"),"gross_profit":item(7200,"INR million"),"revenue":item(12000,"INR million"),
    "customer_acquisition_cost":item(1.2,"INR million/customer"),"monthly_revenue_per_new_customer":item(.1,"INR million/customer-month"),"gross_margin":item(.60),
    "annual_revenue_per_customer":item(1.2,"INR million/customer"),"annual_logo_churn":item(.08),"fcf":item(1200,"INR million"),"terminal_ev_arr":item(7,"multiple"),
    "horizon_years":item(5,"years"),"agi_arr_growth_expectation":item(.20),"target_ev_arr":item(10,"multiple"),"market_price":item(500,"INR/share"),"normalized_eps":item(20,"INR/share")}
def scenarios(): return {"BEAR":{"arr_growth":.10,"target_ev_arr":7},"BASE":{"arr_growth":.20,"target_ev_arr":10},"BULL":{"arr_growth":.30,"target_ev_arr":13}}
def pack(): return {"inputs":inputs(),"as_of":AS_OF,"peers":[{"ev_arr":10},{"ev_arr":14}],"history":[{"ev_arr":8,"available_at":"2024-01-01"},{"ev_arr":13,"available_at":"2025-01-01"}],"scenarios":scenarios(),"warehouse_receipt_id":"receipt","independent_verification_id":"verify"}

def test_saas_afe_unit_economics_and_scenario_labels():
    nrr=calculate(calculation_id="NET_REVENUE_RETENTION",inputs={k:inputs()[k] for k in ("opening_arr","churned_arr","contraction_arr","expansion_arr")},as_of=AS_OF)
    assert nrr["status"]=="SUCCESS" and nrr["calculated_value"]==1.125
    scenario=calculate(calculation_id="SAAS_SCENARIO_EV",inputs={"arr":inputs()["arr"],"arr_growth":item(.2),"target_ev_arr":inputs()["target_ev_arr"]},as_of=AS_OF)
    assert scenario["status"]=="SUCCESS" and "SCENARIO_NOT_FACT" in scenario["warnings"]

def test_saas_route_answer_and_maturity_selector():
    result=evaluate_technology_company(company={"symbol":"SOFT","technology_subsector":"SAAS"},inputs=inputs(),as_of=AS_OF,peers=pack()["peers"],history=pack()["history"],scenarios=scenarios())
    assert result["status"]=="OPERATIONAL_NOT_CERTIFIED" and result["valuation"]["primary_method"]=="EV_ARR"
    assert result["kpis"]["nrr"]==1.125 and len(result["sensitivity"]["grid"])==9
    answer=format_technology_answer(result); assert answer["status"]=="RESEARCH_ONLY" and "12.00x ARR" in answer["direct_conclusion"]
    mature=evaluate_technology_company(company={"symbol":"SOFT","technology_subsector":"ENTERPRISE_SOFTWARE","business_maturity":"MATURE_PROFITABLE"},inputs=inputs(),as_of=AS_OF,scenarios=scenarios())
    assert mature["valuation"]["primary_method"]=="TECH_PRICE_TO_EARNINGS" and mature["valuation"]["primary_value"]==25

def test_saas_fail_closed_and_classification():
    assert classify_technology_subsector({"technology_subsector":"SOFTWARE_PRODUCTS"})["model_family"]=="SOFTWARE_SAAS"
    missing=inputs(); missing.pop("arr"); assert evaluate_technology_company(company={"technology_subsector":"SAAS"},inputs=missing,as_of=AS_OF)["status"]=="DATA_UNAVAILABLE"
    future=inputs(); future["arr"]["available_at"]="2027-01-01"; assert evaluate_technology_company(company={"technology_subsector":"SAAS"},inputs=future,as_of=AS_OF)["status"]=="POINT_IN_TIME_VIOLATION"
    bad=inputs(); bad["churned_arr"]["value"]=9000; assert evaluate_technology_company(company={"technology_subsector":"SAAS"},inputs=bad,as_of=AS_OF)["status"]=="VALIDATION_FAILED"

def test_saas_certification_persistence_context_and_outcomes():
    packs={"SOFTA":pack(),"SOFTB":pack()}; result=certify_software_saas(packs)
    assert result["passed_gates"]==23 and result["certification_status"]=="IN_PROGRESS" and result["investment_certified"] is False
    approved=certify_software_saas(packs,authorized_reviewer="committee",reviewer_authorized=True,review_evidence_id="review")
    calls=[]
    def transport(method,table,**kwargs): calls.append((method,table,kwargs))
    assert seed_software_saas_model(transport=transport)["certified"] is False
    assert persist_software_saas_certification(approved,transport=transport)["investment_certified"] is False
    assert technology_research_context("SOFT",loader=lambda _:{"master":{"technology_subsector":"SAAS"}})["sector_name"]=="Software and SaaS"
    outcome=build_outcome_record(company_id="SOFT",metric="nrr",predicted_value=1.12,actual_value=1.05,predicted_at="2026-04-01T00:00:00Z",evaluated_at="2026-07-20T00:00:00Z",source_id="filing")
    assert outcome["subsector"]=="SOFTWARE_SAAS" and outcome["trusted_update_allowed"] is False
    names={row["name"] for row in plan_tools("Is this SaaS valuation justified by ARR and NRR?",ticker_hint="SOFT")["tools"]}
    assert "GET_TECHNOLOGY_VALUATION" in names and "GET_FINANCIAL_VALUATION" not in names
