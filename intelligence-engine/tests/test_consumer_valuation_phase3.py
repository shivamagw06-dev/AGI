from __future__ import annotations
import pytest

from app.tools.executor import build_core_read_executor
from app.tools.registry import plan_tools
from consumer_valuation.certification import certify_consumer_models
from consumer_valuation.classification import COHORTS, classify_consumer
from consumer_valuation.models import MODELS
from consumer_valuation.outcomes import build_consumer_outcome
from consumer_valuation.persistence import seed_consumer_models
from consumer_valuation.research_context import consumer_research_context
from consumer_valuation.service import evaluate_consumer_company
from financial_engine import calculate

AS_OF="2026-08-16"


def item(value, unit="decimal", available="2026-08-15"):
    return {"value":value,"unit":unit,"period":"FY26","available_at":available,"source_id":"official-filing"}


def base_inputs():
    return {"revenue":item(1000,"INR million"),"ebitda":item(180,"INR million"),"fcf":item(100,"INR million"),
        "market_price":item(500,"INR/share"),"normalized_eps":item(20,"INR/share"),"enterprise_value":item(5000,"INR million"),
        "gross_profit":item(400,"INR million"),"cogs":item(600,"INR million"),"opening_inventory":item(90,"INR million"),"closing_inventory":item(110,"INR million")}


def test_all_eight_consumer_subsectors_have_reviewed_models_and_cohorts():
    assert set(MODELS)==set(COHORTS)
    assert len(MODELS)==8
    for family,model in MODELS.items():
        symbol=next(iter(COHORTS[family]))
        assert classify_consumer({"symbol":symbol})["subsector"]==family
        assert len(model.key_kpis)>=10 and len(model.valuation_methods)>=3
        assert model.validation_status=="IMPLEMENTED_NOT_RESEARCH_VALIDATED"


def test_diversified_company_is_not_forced_into_one_subsector():
    result=classify_consumer({"symbol":"MIXED","segments":[
        {"consumer_subsector":"FMCG","revenue_share":.55},{"consumer_subsector":"RETAIL","revenue_share":.45}]})
    assert result["status"]=="DIVERSIFIED" and result["requires_sotp"] is True


def test_afe_consumer_decompositions_are_deterministic():
    pvm=calculate(calculation_id="CONSUMER_PRICE_VOLUME_MIX_GROWTH",inputs={"volume_growth":item(.08),"price_mix_growth":item(.05)},as_of=AS_OF)
    revpar=calculate(calculation_id="CONSUMER_REVPAR",inputs={"adr":item(10000,"INR"),"occupancy":item(.75)},as_of=AS_OF)
    room=calculate(calculation_id="CONSUMER_ROOM_REVENUE",inputs={"rooms":item(100,"rooms"),"available_days":item(365,"days"),"occupancy":item(.75),"adr":item(10000,"INR")},as_of=AS_OF)
    assert pvm["calculated_value"]==pytest.approx(.134)
    assert revpar["calculated_value"]==7500
    assert room["calculated_value"]==273_750_000


def test_hotel_evaluation_decomposes_occupancy_and_adr_and_remains_blocked():
    inputs={**base_inputs(),"rooms":item(100,"rooms"),"occupancy":item(.75),"adr":item(10000,"INR"),"available_days":item(365,"days")}
    result=evaluate_consumer_company(company={"symbol":"INDHOTEL"},inputs=inputs,as_of=AS_OF)
    assert result["status"]=="OPERATIONAL_NOT_CERTIFIED"
    assert result["calculations"]["revpar"]["calculated_value"]==7500
    assert result["execution_eligible"] is False and result["investment_certified"] is False


def test_missing_and_future_dated_data_fail_closed_without_fabrication():
    inputs={**base_inputs(),"volume_growth":item(.08),"price_mix_growth":item(.05,available="2026-08-17")}
    result=evaluate_consumer_company(company={"symbol":"HINDUNILVR"},inputs=inputs,as_of=AS_OF)
    assert result["data_coverage"]["issues"]["price_mix_growth"]=="POINT_IN_TIME_VIOLATION"
    assert result["calculations"]["price_volume_mix_growth"]["status"]=="DATA_UNAVAILABLE"
    assert result["reverse_valuation"]["expectation_gap"]=="REQUIRES_AGI_BASE_CASE"


def test_context_certification_and_ask_tool_integration():
    context=consumer_research_context("TITAN",loader=lambda _:{"master":{"consumer_subsector":"JEWELLERY"}})
    assert context["sector_name"]=="Jewellery" and context["calculation_authority"]=="AFE_ONLY"
    certification=certify_consumer_models()
    assert certification["investment_certified"] is False
    assert all(row["total"]==23 and row["investment_certified"] is False for row in certification["sectors"].values())
    tools={row["name"] for row in plan_tools("How do gold prices affect jewellery volume and valuation?",ticker_hint="TITAN")["tools"]}
    assert "GET_CONSUMER_VALUATION" in tools and "GET_FINANCIAL_VALUATION" not in tools
    assert "GET_CONSUMER_VALUATION" in build_core_read_executor().bound_tools


def test_existing_registry_persistence_and_outcome_learning_are_fail_closed():
    calls=[]
    def transport(*args,**kwargs): calls.append((args,kwargs))
    seeded=seed_consumer_models(transport=transport)
    assert seeded["models"]==8 and seeded["investment_certified_models"]==0
    outcome=build_consumer_outcome(company_id="TITAN",subsector="JEWELLERY",metric="sssg",predicted_value=.12,
        actual_value=.08,predicted_at="2026-04-01T00:00:00Z",evaluated_at="2026-08-01T00:00:00Z",source_id="results")
    assert outcome["status"]=="PROPOSED" and outcome["trusted_update_allowed"] is False
