from __future__ import annotations

from app.tools.executor import build_core_read_executor
from app.tools.registry import plan_tools
from causal_research_engine.technology_templates import it_services_templates
from financial_engine import calculate
from technology_valuation.answer import format_technology_answer
from technology_valuation.certification import certify_it_services
from technology_valuation.classification import classify_technology_subsector
from technology_valuation.persistence import persist_it_services_certification, seed_it_services_model
from technology_valuation.outcomes import build_outcome_record
from technology_valuation.research_context import technology_research_context
from technology_valuation.service import REQUIRED_INPUTS, evaluate_technology_company

AS_OF="2026-08-15"


def item(value, unit="decimal"):
    return {"value":value,"unit":unit,"currency":"INR","period":"FY2026","source_id":"filing-1","available_at":"2026-07-20"}


def inputs():
    return {
        "market_price":item(3200,"INR/share"),"normalized_eps":item(128,"INR/share"),
        "enterprise_value":item(12000000,"INR million"),"ebitda":item(500000,"INR million"),
        "revenue":item(2500000,"INR million"),"ebit":item(600000,"INR million"),"fcf":item(500000,"INR million"),
        "opening_headcount":item(600000,"employees"),"closing_headcount":item(610000,"employees"),
        "utilization":item(.84),"billing_rate":item(.55,"INR million/employee-period"),"billable_periods":item(4,"periods"),
        "total_contract_value":item(2800000,"INR million"),"roic":item(.32),"attrition":item(.13),
        "client_concentration":item(.18),"cost_of_equity":item(.12),"payout_ratio":item(.45),
        "agi_growth_expectation":item(.08),"tax_rate":item(.25),"shares_outstanding":item(3600,"million shares"),
        "target_pe":item(24,"multiple"),
    }


def scenarios():
    return {"BEAR":{"revenue_growth":.03,"ebit_margin":.21,"target_pe":19},
            "BASE":{"revenue_growth":.08,"ebit_margin":.24,"target_pe":24},
            "BULL":{"revenue_growth":.13,"ebit_margin":.27,"target_pe":29}}


def pack():
    return {"inputs":inputs(),"as_of":AS_OF,"peers":[{"subsector":"IT_SERVICES","pe":23},{"subsector":"IT_SERVICES","pe":26}],
            "history":[{"pe":20,"available_at":"2024-01-01"},{"pe":28,"available_at":"2025-01-01"}],
            "scenarios":scenarios(),"warehouse_receipt_id":"receipt-1","independent_verification_id":"verify-1"}


def test_phase2a_calculations_are_deterministic_and_label_scenarios():
    revenue_per_employee=calculate(calculation_id="REVENUE_PER_EMPLOYEE",inputs={k:inputs()[k] for k in ("revenue","opening_headcount","closing_headcount")},as_of=AS_OF)
    assert revenue_per_employee["status"]=="SUCCESS"
    assert revenue_per_employee["deterministic"] is True
    result=calculate(calculation_id="IT_SERVICES_SCENARIO_PRICE",inputs={
        "revenue":inputs()["revenue"],"revenue_growth":item(.08),"ebit_margin":item(.24),"tax_rate":inputs()["tax_rate"],
        "shares_outstanding":inputs()["shares_outstanding"],"target_pe":inputs()["target_pe"]},as_of=AS_OF)
    assert result["status"]=="SUCCESS"
    assert "SCENARIO_NOT_FACT" in result["warnings"]


def test_it_services_evaluation_and_client_answer():
    result=evaluate_technology_company(company={"symbol":"TCS"},inputs=inputs(),as_of=AS_OF,peers=pack()["peers"],history=pack()["history"],scenarios=scenarios())
    assert result["status"]=="OPERATIONAL_NOT_CERTIFIED"
    assert result["classification"]["subsector"]=="IT_SERVICES"
    assert result["valuation"]["current_pe"]==25
    assert len(result["sensitivity"]["grid"])==9
    assert all(row["status"]=="SUCCESS" for row in result["scenarios"].values())
    assert result["causal_context"]["status"]=="PROPOSED_NOT_TRUSTED"
    assert result["investment_certified"] is False
    answer=format_technology_answer(result)
    assert answer["status"]=="RESEARCH_ONLY"
    assert answer["execution_eligible"] is False
    assert "25.00x" in answer["direct_conclusion"]


def test_fail_closed_classification_missing_data_pit_and_adversarial():
    assert classify_technology_subsector({"company_name":"Technology Consulting Limited"})["status"]=="CLASSIFICATION_UNAVAILABLE"
    missing=inputs(); missing.pop(REQUIRED_INPUTS[0])
    assert evaluate_technology_company(company={"symbol":"TCS"},inputs=missing,as_of=AS_OF)["status"]=="DATA_UNAVAILABLE"
    future=inputs(); future["market_price"]["available_at"]="2027-01-01"
    assert evaluate_technology_company(company={"symbol":"TCS"},inputs=future,as_of=AS_OF)["status"]=="POINT_IN_TIME_VIOLATION"
    bad=inputs(); bad["utilization"]["value"]=1.2
    assert evaluate_technology_company(company={"symbol":"TCS"},inputs=bad,as_of=AS_OF)["status"]=="VALIDATION_FAILED"


def test_causal_templates_include_counter_effects_and_are_not_trusted():
    rows=it_services_templates("TCS")
    assert len(rows)>=10
    assert all(row.status=="PROPOSED" for row in rows)
    assert any(row.counter_effects for row in rows)
    assert any(row.cause=="ai_productivity" for row in rows)


def test_five_company_certification_never_self_promotes():
    packs={symbol:pack() for symbol in ("TCS","INFY","HCLTECH","WIPRO","TECHM")}
    result=certify_it_services(packs)
    assert result["passed_gates"]==23
    assert result["certification_status"]=="IN_PROGRESS"
    assert result["lifecycle_status"]=="EVIDENCE_VALIDATED"
    assert result["investment_certified"] is False
    approved=certify_it_services(packs,authorized_reviewer="research-committee",reviewer_authorized=True,review_evidence_id="review-1")
    assert approved["certification_status"]=="PASSED"
    assert approved["investment_certified"] is False


def test_ask_context_tool_and_persistence_reuse():
    context=technology_research_context("TCS",loader=lambda _: {"master":{"industry_dna":"it_services"}})
    assert context["status"]=="MODEL_CONTEXT"
    assert context["certified"] is False
    names={row["name"] for row in plan_tools("Is TCS valuation attractive?",ticker_hint="TCS")["tools"]}
    assert "GET_TECHNOLOGY_VALUATION" in names
    assert "GET_TECHNOLOGY_VALUATION" in build_core_read_executor().bound_tools
    calls=[]
    def transport(method,table,**kwargs): calls.append((method,table,kwargs))
    seeded=seed_it_services_model(transport=transport)
    assert seeded["ok"] is True and seeded["certified"] is False
    assert calls[0][2]["body"]["parent_sector"]=="TECHNOLOGY_AND_DIGITAL"
    packs={symbol:pack() for symbol in ("TCS","INFY","HCLTECH","WIPRO","TECHM")}
    certification=certify_it_services(packs,authorized_reviewer="committee",reviewer_authorized=True,review_evidence_id="review-1")
    persisted=persist_it_services_certification(certification,transport=transport)
    assert persisted["ok"] is True and persisted["investment_certified"] is False
    assert calls[-1][2]["body"]["total_gates"]==23


def test_outcome_learning_proposes_but_never_self_teaches():
    row=build_outcome_record(company_id="TCS",metric="ebit_margin",predicted_value=.25,actual_value=.23,
        predicted_at="2026-04-01T00:00:00Z",evaluated_at="2026-07-20T00:00:00Z",source_id="filing-q1",
        failed_assumptions=["pricing offset wage pressure"])
    assert row["status"]=="PROPOSED"
    assert row["trusted_update_allowed"] is False
    assert row["automatic_framework_change"] is False
