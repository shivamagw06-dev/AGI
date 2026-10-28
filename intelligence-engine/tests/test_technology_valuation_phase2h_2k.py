from __future__ import annotations
import pytest
from app.tools.registry import plan_tools
from technology_valuation.answer import format_technology_answer
from technology_valuation.classification import classify_technology_subsector
from technology_valuation.outcomes import build_outcome_record
from technology_valuation.persistence import seed_specialized_models
from technology_valuation.research_context import technology_research_context
from technology_valuation.service import evaluate_technology_company
from technology_valuation.specialized_certification import certify_specialized
from technology_valuation.specialized_service import REQUIRED_SPECIALIZED

AS_OF="2026-08-15"
def item(value,unit="INR_million"):return {"value":value,"unit":unit,"currency":"INR","period":"FY2026","available_at":AS_OF,"source_id":"official-filing"}
BASE={"enterprise_value":1000,"revenue":200,"ebitda":40,"gross_profit":100,"fcf":20,"capex":10,"net_debt":100,"terminal_ev_ebitda":12,"horizon_years":5,"target_ev_ebitda":14,"scenario_revenue_growth":.12,"scenario_ebitda_margin":.2}
EXTRA={
"ERD_TECHNOLOGY_SERVICES":{"opening_revenue":180,"closing_revenue":200,"order_intake":240,"opening_engineers":900,"closing_engineers":1100,"utilization":.8,"embedded_revenue":80,"client_concentration":.35},
"HARDWARE_ELECTRONICS":{"opening_units":90,"closing_units":100,"inventory":40,"cogs":100,"local_value_add":60,"order_book":300},
"DATA_CENTRES":{"operational_mw":100,"contracted_mw":80,"pipeline_mw":60,"preleased_mw":30,"facility_power":140,"it_power":100,"added_mw":20},
"FINTECH_PAYMENTS":{"opening_tpv":9000,"closing_tpv":11000,"tpv":11000,"transactions":1000,"active_merchants":100,"contribution_profit":30,"fraud_losses":1},
"CYBERSECURITY_CLOUD":{"opening_arr":120,"closing_arr":150,"retained_expanded_arr":132,"segment_arr":120,"customer_concentration":.2,"rpo":225,"rnd":30},
}
ALIASES={"ERD_TECHNOLOGY_SERVICES":"ERD_SERVICES","HARDWARE_ELECTRONICS":"ELECTRONICS_MANUFACTURING","DATA_CENTRES":"DATA_CENTRES","FINTECH_PAYMENTS":"PAYMENTS_TECHNOLOGY","CYBERSECURITY_CLOUD":"CYBERSECURITY"}
def inputs(family):return {k:item(v,"decimal" if k in {"scenario_revenue_growth","scenario_ebitda_margin","utilization","client_concentration","customer_concentration"} else "count") for k,v in (BASE|EXTRA[family]).items()}
def scenarios():return {"BEAR":{"revenue_growth":.02,"ebitda_margin":.15,"target_ev_ebitda":10},"BASE":{"revenue_growth":.12,"ebitda_margin":.2,"target_ev_ebitda":14},"BULL":{"revenue_growth":.2,"ebitda_margin":.25,"target_ev_ebitda":17}}
def pack(family):return {"inputs":inputs(family),"as_of":AS_OF,"peers":[{"ev_ebitda":18}],"history":[{"ev_ebitda":16,"available_at":AS_OF}],"scenarios":scenarios(),"warehouse_receipt_id":"wr","independent_verification_id":"iv"}

@pytest.mark.parametrize("family",list(EXTRA))
def test_specialized_routes_math_answers_and_gates(family):
    classification=classify_technology_subsector({"technology_subsector":ALIASES[family]});assert classification["model_family"]==family
    result=evaluate_technology_company(company={"symbol":"TEST","technology_subsector":ALIASES[family]},**{k:pack(family)[k] for k in ("inputs","as_of","peers","history","scenarios")})
    assert result["status"]=="OPERATIONAL_NOT_CERTIFIED" and result["valuation"]["current_ev_ebitda"]==25
    assert format_technology_answer(result)["execution_eligible"] is False
    certified=certify_specialized(family,{"TEST":pack(family)})
    assert certified["passed_gates"]==23 and certified["certification_status"]=="IN_PROGRESS" and certified["investment_certified"] is False

@pytest.mark.parametrize("family",list(EXTRA))
def test_specialized_fails_closed_and_exposes_context(family):
    future=inputs(family);future["enterprise_value"]["available_at"]="2026-08-16"
    assert evaluate_technology_company(company={"technology_subsector":ALIASES[family]},inputs=future,as_of=AS_OF)["status"]=="POINT_IN_TIME_VIOLATION"
    missing=inputs(family);missing.pop(REQUIRED_SPECIALIZED[family][0])
    assert evaluate_technology_company(company={"technology_subsector":ALIASES[family]},inputs=missing,as_of=AS_OF)["status"]=="DATA_UNAVAILABLE"
    context=technology_research_context("TEST",loader=lambda _:{"master":{"technology_subsector":ALIASES[family]}})
    assert context["sector_id"].endswith(family) and context["investment_certified"] is False

def test_specialized_persistence_outcomes_and_tool_route():
    calls=[]
    def transport(method,table,**kwargs):calls.append((method,table,kwargs))
    seeded=seed_specialized_models(transport=transport);assert seeded["ok"] is True and seeded["models"]==5 and seeded["certified_models"]==0
    for metric,family in (("revenue_per_engineer","ERD_TECHNOLOGY_SERVICES"),("unit_growth","HARDWARE_ELECTRONICS"),("occupancy","DATA_CENTRES"),("tpv_growth","FINTECH_PAYMENTS"),("rpo_coverage","CYBERSECURITY_CLOUD")):
        outcome=build_outcome_record(company_id="TEST",metric=metric,predicted_value=1,actual_value=1.1,predicted_at=AS_OF,evaluated_at="2027-08-15",source_id="result")
        assert outcome["subsector"]==family and outcome["trusted_update_allowed"] is False
    names={x["name"] for x in plan_tools("How does data centre PUE affect valuation?",ticker_hint="TEST")["tools"]}
    assert "GET_TECHNOLOGY_VALUATION" in names
