import pytest
from financial_engine import calculate
from energy_valuation.answer import build_energy_answer
from energy_valuation.certification import GATES,certify_energy_models
from energy_valuation.classification import COHORTS,classify_energy
from energy_valuation.models import MODELS
from energy_valuation.outcomes import build_energy_outcome
from energy_valuation.persistence import seed_energy_models
from energy_valuation.research_context import energy_research_context
from energy_valuation.service import evaluate_energy_company,required_inputs
from energy_valuation.validation import VALIDATION_QUESTIONS,validate_energy_pack
from app.tools.registry import plan_tools

def obs(value,available_at="2026-08-15",unit="unit"):
 return {"value":value,"source_id":"filing-1","period":"FY2026","available_at":available_at,"unit":unit,"currency":"INR"}
VALUES={"revenue":1000,"ebitda":300,"fcf":100,"enterprise_value":4000,"market_price":500,"normalized_eps":25,"capex":150,"net_debt":900,"installed_capacity_mw":100,"generation":600,"available_hours":10,"production_volume":80,"realization_per_unit":100,"cash_cost_per_unit":60,"normalized_spread":30,"reserves":1000,"annual_production":100,"regulated_asset_base":2000,"allowed_return":.15,"initial_capex":1000,"annual_fcf":150,"discount_rate":.1,"operating_life":20,"cost_of_equity":.12,"payout_ratio":.35}
def inputs(family,extras=()):return {key:obs(VALUES[key]) for key in set(required_inputs(family))|set(extras)}

def test_twenty_authoritative_models_and_classification():
 assert len(MODELS)==20 and set(MODELS)==set(COHORTS)
 for family,symbols in COHORTS.items():
  result=classify_energy({"symbol":next(iter(symbols))})
  assert result.get("model_family")==family or result["status"]=="DIVERSIFIED"
  assert len(MODELS[family].key_kpis)>=10

@pytest.mark.parametrize("calc_id,values,expected",[
 ("ENERGY_PLANT_LOAD_FACTOR",{"generation":600,"installed_capacity_mw":100,"available_hours":10},.6),
 ("ENERGY_UNIT_SPREAD",{"realization_per_unit":100,"cash_cost_per_unit":60},40),
 ("ENERGY_NORMALIZED_EBITDA",{"production_volume":80,"normalized_spread":30},2400),
 ("ENERGY_RESERVE_LIFE",{"reserves":1000,"annual_production":100},10),
 ("ENERGY_REGULATED_RETURN",{"regulated_asset_base":2000,"allowed_return":.15},300),
])
def test_afe_energy_calculations(calc_id,values,expected):
 result=calculate(calculation_id=calc_id,inputs={k:obs(v) for k,v in values.items()},as_of="2026-08-16")
 assert result["status"]=="SUCCESS" and result["calculated_value"]==pytest.approx(expected)

def test_upstream_normalizes_commodity_and_reserves():
 data=inputs("OIL_GAS_UPSTREAM",("cost_of_equity","payout_ratio")); result=evaluate_energy_company(company={"symbol":"ONGC"},inputs=data,as_of="2026-08-16",peers=[{"subsector":"OIL_GAS_UPSTREAM","pe":8}],history=[{"pe":7,"available_at":"2026-08-01"}])
 assert result["calculations"]["reserve_life"]["calculated_value"]==10
 assert result["calculations"]["normalized_ebitda"]["calculated_value"]==2400
 assert result["commodity_normalization"]["historical_percentile"]=="DATA_REQUIRED"
 assert not result["investment_certified"] and not result["execution_eligible"]
 assert len(result["observation_matrix"])==len(result["required_inputs"])
 assert {"company","segment","metric","publication_date","effective_date","source","pit_valid","status"} <= set(result["observation_matrix"][0])

def test_power_keeps_capacity_generation_and_plf_distinct():
 data=inputs("POWER_GENERATION",("initial_capex","annual_fcf","discount_rate","operating_life")); result=evaluate_energy_company(company={"symbol":"NTPC"},inputs=data,as_of="2026-08-16")
 assert result["calculations"]["plf"]["calculated_value"]==.6
 assert result["calculations"]["project_npv"]["status"]=="SUCCESS"
 assert any("distinct states" in x for x in result["analytical_warnings"])

def test_regulated_return_is_distinct_and_pit_is_fail_closed():
 data=inputs("POWER_TRANSMISSION"); data["revenue"]=obs(1000,"2026-08-17")
 result=evaluate_energy_company(company={"symbol":"POWERGRID"},inputs=data,as_of="2026-08-16")
 assert result["calculations"]["regulated_return"]["calculated_value"]==300
 assert result["data_coverage"]["issues"]["revenue"]=="POINT_IN_TIME_VIOLATION"
 assert result["sector_valuation_scorecard"]["conclusion"]=="RESEARCH_INCOMPLETE"

def test_diversified_requires_sotp():
 assert classify_energy({"symbol":"LT"})["model_family"]=="NUCLEAR_SUPPLY_CHAIN"
 result=classify_energy({"symbol":"MIXED","segments":[{"energy_subsector":"OIL_GAS_UPSTREAM","revenue_share":.5},{"energy_subsector":"OIL_GAS_REFINING","revenue_share":.5}]})
 assert result["status"]=="DIVERSIFIED" and result["requires_sotp"]

def test_ask_context_tools_answer_validation_learning_and_persistence():
 context=energy_research_context("NTPC",loader=lambda _:{"master":{"energy_subsector":"POWER_GENERATION"}})
 assert context["status"]=="MODEL_CONTEXT" and context["calculation_authority"]=="AFE_ONLY"
 plan=plan_tools("What PLF and tariff does NTPC valuation imply?",ticker_hint="NTPC"); names=[x["name"] for x in plan["tools"]]
 assert "GET_ENERGY_VALUATION" in names and "GET_ENERGY_RESEARCH_CONTEXT" in names
 result=evaluate_energy_company(company={"symbol":"NTPC"},inputs=inputs("POWER_GENERATION"),as_of="2026-08-16"); answer=build_energy_answer(result)
 assert answer["status"]=="RESEARCH_ONLY" and "DATA_REQUIRED" in answer["direct_conclusion"]
 validation=validate_energy_pack(company={"symbol":"NTPC"},inputs=inputs("POWER_GENERATION"),as_of="2026-08-16",qualitative_evidence={"business_model":{"finding":"Generator","source_id":"annual-report"}})
 assert validation["validation_status"]=="VALIDATION_INCOMPLETE" and len(validation["validation_questions"])==len(VALIDATION_QUESTIONS)
 certification=certify_energy_models(); assert len(certification["sectors"])==20 and len(GATES)==23 and not certification["investment_certified"]
 assert all(row["passed"]==23 for row in certification["sectors"].values())
 writes=[]; seeded=seed_energy_models(transport=lambda *a,**kw:writes.append((a,kw)) or {"ok":True}); assert seeded["models"]==20 and len(writes)==40
 outcome=build_energy_outcome(company_id="NTPC",subsector="POWER_GENERATION",metric="generation",predicted_value=100,actual_value=95,predicted_at="2026-01-01T00:00:00Z",evaluated_at="2026-08-16T00:00:00Z",source_id="filing")
 assert outcome["status"]=="PROPOSED" and not outcome["trusted_update_allowed"]

@pytest.mark.parametrize("family",["OIL_GAS_UPSTREAM","OIL_GAS_REFINING","POWER_GENERATION","POWER_DISTRIBUTION","RENEWABLE_POWER","COAL","CITY_GAS_DISTRIBUTION","OILFIELD_SERVICES","WATER_UTILITIES","ENERGY_STORAGE_BATTERIES"])
def test_missing_kpis_never_fabricate_or_certify(family):
 symbol=next(iter(COHORTS[family])); result=evaluate_energy_company(company={"symbol":symbol,"energy_subsector":family},inputs={},as_of="2026-08-16")
 assert result["status"]=="DATA_UNAVAILABLE" and result["evidence_gaps"]
 assert result["cycle"]["state"]=="DATA_REQUIRED" and not result["investment_certified"]
