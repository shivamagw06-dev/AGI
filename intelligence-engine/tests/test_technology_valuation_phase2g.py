from app.tools.registry import plan_tools
from technology_valuation.answer import format_technology_answer
from technology_valuation.classification import classify_technology_subsector
from technology_valuation.outcomes import build_outcome_record
from technology_valuation.persistence import seed_tower_model
from technology_valuation.research_context import technology_research_context
from technology_valuation.service import evaluate_technology_company
from technology_valuation.tower_certification import certify_towers

AS_OF="2026-08-15"
def datum(value,unit="INR_million"):
    return {"value":value,"unit":unit,"currency":"INR","period":"FY2026","available_at":AS_OF,"source_id":"filing-1"}
def inputs():
    values={"enterprise_value":300000,"revenue":30000,"rental_revenue":24000,"ebitda":15000,"sites":100000,"tenants":180000,"tenant_additions":5000,"annual_rent_per_tenant":0.1333333333,"energy_costs":6000,"energy_reimbursements":5700,"contract_duration":6,"customer_concentration":.65,"capex":6000,"net_debt":90000,"fcf":6000,"terminal_ev_ebitda":12,"horizon_years":5,"target_ev_ebitda":14,"scenario_tenancy_ratio":1.8,"scenario_ebitda_margin":.5}
    return {k:datum(v,"decimal" if k in {"customer_concentration","scenario_ebitda_margin"} else "years" if k in {"contract_duration","horizon_years"} else "count" if k in {"sites","tenants","tenant_additions"} else "multiple" if k in {"terminal_ev_ebitda","target_ev_ebitda","scenario_tenancy_ratio"} else "INR_million") for k,v in values.items()}
def scenarios():
    return {"BEAR":{"sites":100000,"tenancy_ratio":1.65,"annual_rent_per_tenant":.13,"ebitda_margin":.45,"target_ev_ebitda":11},"BASE":{"sites":100000,"tenancy_ratio":1.8,"annual_rent_per_tenant":.1333333333,"ebitda_margin":.5,"target_ev_ebitda":14},"BULL":{"sites":105000,"tenancy_ratio":1.95,"annual_rent_per_tenant":.14,"ebitda_margin":.55,"target_ev_ebitda":16}}
def pack():return {"inputs":inputs(),"as_of":AS_OF,"peers":[{"ev_ebitda":18}],"history":[{"ev_ebitda":16,"available_at":AS_OF}],"scenarios":scenarios(),"warehouse_receipt_id":"wr-1","independent_verification_id":"iv-1"}

def test_tower_route_and_answer():
    assert classify_technology_subsector({"technology_subsector":"TELECOM_TOWERS"})["model_family"]=="TELECOM_INFRASTRUCTURE_TOWERS"
    result=evaluate_technology_company(company={"symbol":"INDUSTOWER","technology_subsector":"TELECOM_TOWERS"},**{k:pack()[k] for k in ("inputs","as_of","peers","history","scenarios")})
    assert result["status"]=="OPERATIONAL_NOT_CERTIFIED" and result["kpis"]["tenancy_ratio"]==1.8
    assert result["valuation"]["current_ev_ebitda"]==20 and result["valuation"]["ev_per_site"]==3
    assert "20.00x" in format_technology_answer(result)["direct_conclusion"]
def test_tower_fail_closed():
    stale=inputs();stale["enterprise_value"]["available_at"]="2026-08-16"
    assert evaluate_technology_company(company={"technology_subsector":"TELECOM_TOWERS"},inputs=stale,as_of=AS_OF)["status"]=="POINT_IN_TIME_VIOLATION"
    bad=inputs();bad["tenants"]["value"]=99999
    assert evaluate_technology_company(company={"technology_subsector":"TELECOM_TOWERS"},inputs=bad,as_of=AS_OF)["status"]=="VALIDATION_FAILED"
def test_tower_certification_and_persistence():
    result=certify_towers({"INDUSTOWER":pack(),"SUMMIT":pack()})
    assert result["passed_gates"]==23 and result["certification_status"]=="IN_PROGRESS" and result["investment_certified"] is False
    calls=[]
    def transport(method,table,**kwargs):calls.append((method,table,kwargs))
    seed=seed_tower_model(transport=transport)
    assert seed["ok"] is True and seed["certified"] is False and calls
def test_tower_context_outcomes_and_tool_selection():
    context=technology_research_context("INDUSTOWER",loader=lambda _:{"master":{"technology_subsector":"TELECOM_TOWERS"}})
    assert context["sector_id"].endswith("TELECOM_INFRASTRUCTURE_TOWERS")
    outcome=build_outcome_record(company_id="INDUSTOWER",metric="tenancy_ratio",predicted_value=1.8,actual_value=1.82,predicted_at=AS_OF,evaluated_at="2027-08-15",source_id="result-1")
    assert outcome["subsector"]=="TELECOM_INFRASTRUCTURE_TOWERS" and outcome["trusted_update_allowed"] is False
    names={tool["name"] for tool in plan_tools("How does tower tenancy ratio affect EV/site?",ticker_hint="INDUSTOWER")["tools"]}
    assert "GET_TECHNOLOGY_VALUATION" in names
