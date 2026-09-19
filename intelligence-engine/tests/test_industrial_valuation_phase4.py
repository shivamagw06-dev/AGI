from datetime import date
import pytest
from financial_engine import calculate
from industrial_valuation.certification import certify_industrial_models
from industrial_valuation.classification import COHORTS,classify_industrial
from industrial_valuation.models import MODELS
from industrial_valuation.outcomes import build_industrial_outcome
from industrial_valuation.persistence import seed_industrial_models
from industrial_valuation.research_context import industrial_research_context
from industrial_valuation.service import evaluate_industrial_company,required_inputs
from industrial_valuation.scorecard import DIMENSIONS,build_sector_valuation_scorecard
from industrial_valuation.validation import VALIDATION_QUESTIONS,cohort_manifest,validate_company_pack
from app.tools.registry import plan_tools

def obs(value,available_at="2026-08-15",unit="INR million"):
    return {"value":value,"source_id":"filing-1","period":"FY2026","available_at":available_at,"unit":unit,"currency":"INR"}

def inputs(family):
    values={"revenue":1000,"ebitda":180,"fcf":90,"market_price":500,"normalized_eps":25,"enterprise_value":2200,"capex":70,"order_inflow":1200,"order_book":2400,"capacity":100,"production":80,"realization_per_unit":100,"input_cost_per_unit":65,"sales_volume":80,"normalized_spread":30,"cost_of_equity":.12,"payout_ratio":.35}
    return {key:obs(values[key]) for key in set(required_inputs(family))|{"cost_of_equity","payout_ratio"}}

def test_all_16_models_are_complete_and_classifiable():
    assert len(MODELS)==16
    assert set(MODELS)==set(COHORTS)
    for family,symbols in COHORTS.items():
        result=classify_industrial({"symbol":next(iter(symbols))})
        assert result["model_family"]==family
        assert len(MODELS[family].key_kpis)>=10

def test_explicit_and_diversified_classification():
    assert classify_industrial({"symbol":"NEWCO","industrial_subsector":"CEMENT"})["model_family"]=="CEMENT"
    result=classify_industrial({"symbol":"MIXED","segments":[{"industrial_subsector":"STEEL","revenue_share":.6},{"industrial_subsector":"CEMENT","revenue_share":.4}]})
    assert result["status"]=="DIVERSIFIED" and result["requires_sotp"] is True

@pytest.mark.parametrize("calculation_id,values,expected",[
    ("INDUSTRIAL_BOOK_TO_BILL",{"order_inflow":120,"revenue":100},1.2),
    ("INDUSTRIAL_COMMODITY_SPREAD",{"realization_per_unit":100,"input_cost_per_unit":70},30),
    ("INDUSTRIAL_NORMALIZED_EBITDA",{"sales_volume":10,"normalized_spread":30},300),
    ("INDUSTRIAL_CAPACITY_UTILIZATION",{"production":80,"capacity":100},.8),
    ("INDUSTRIAL_CASH_CONVERSION_CYCLE",{"receivable_days":60,"inventory_days":40,"payable_days":35},65),
])
def test_afe_is_calculation_authority(calculation_id,values,expected):
    result=calculate(calculation_id=calculation_id,inputs={key:obs(value) for key,value in values.items()},as_of="2026-08-16")
    assert result["status"]=="SUCCESS" and result["calculated_value"]==expected

def test_commodity_cycle_is_normalized_and_not_certified():
    result=evaluate_industrial_company(company={"symbol":"TATASTEEL"},inputs=inputs("STEEL"),as_of="2026-08-16",peers=[{"subsector":"STEEL","pe":8}],history=[{"pe":7,"available_at":"2026-08-01"}])
    assert result["calculations"]["normalized_ebitda"]["calculated_value"]==2400
    assert result["cycle_normalization"]["status"]=="CALCULATED"
    assert result["allowed_use"]=="RESEARCH_ONLY" and not result["investment_certified"]
    assert any("peak-cycle" in warning for warning in result["analytical_warnings"])

def test_order_company_and_defence_state_warning():
    result=evaluate_industrial_company(company={"symbol":"HAL"},inputs=inputs("DEFENCE_AEROSPACE"),as_of="2026-08-16")
    assert result["calculations"]["book_to_bill"]["calculated_value"]==1.2
    assert any("distinct states" in warning for warning in result["analytical_warnings"])

def test_pit_violation_fails_closed():
    data=inputs("CEMENT"); data["revenue"]=obs(1000,"2026-08-17")
    result=evaluate_industrial_company(company={"symbol":"ULTRACEMCO"},inputs=data,as_of="2026-08-16")
    assert result["data_coverage"]["issues"]["revenue"]=="POINT_IN_TIME_VIOLATION"
    assert result["execution_eligible"] is False

def test_context_tool_certification_persistence_and_outcome():
    context=industrial_research_context("BEL",loader=lambda _:{"master":{"industrial_subsector":"DEFENCE_AEROSPACE"}})
    assert context["status"]=="MODEL_CONTEXT" and context["calculation_authority"]=="AFE_ONLY"
    plan=plan_tools("How should defence order book and valuation be assessed?",ticker_hint="BEL")
    assert "GET_INDUSTRIAL_VALUATION" in [row["name"] for row in plan["tools"]]
    certification=certify_industrial_models(); assert certification["investment_certified"] is False and len(certification["sectors"])==16
    writes=[]
    seeded=seed_industrial_models(transport=lambda *args,**kwargs:writes.append((args,kwargs)) or {"ok":True})
    assert seeded["ok"] and seeded["models"]==16 and len(writes)==32
    outcome=build_industrial_outcome(company_id="BEL",subsector="DEFENCE_AEROSPACE",metric="order_book",predicted_value=100,actual_value=90,predicted_at="2026-01-01T00:00:00Z",evaluated_at="2026-08-16T00:00:00Z",source_id="filing")
    assert outcome["status"]=="PROPOSED" and not outcome["trusted_update_allowed"]

def test_formal_validation_cohort_and_uniform_scorecard():
    manifest=cohort_manifest()
    assert manifest["subsectors"]==16 and manifest["companies"]>=35
    assert len(manifest["questions"])==11
    result=evaluate_industrial_company(company={"symbol":"TATASTEEL"},inputs=inputs("STEEL"),as_of="2026-08-16")
    card=result["sector_valuation_scorecard"]
    assert [line["dimension"] for line in card["dimensions"]]==list(DIMENSIONS)
    assert card["conclusion"]=="RESEARCH_INCOMPLETE"
    assert all(line["score"] is None for line in card["dimensions"])

def test_company_validation_requires_all_eleven_evidence_answers():
    result=validate_company_pack(company={"symbol":"TATASTEEL"},inputs=inputs("STEEL"),as_of="2026-08-16",qualitative_evidence={"business_model":{"finding":"Integrated steel producer","source_id":"annual-report"}})
    assert result["validation_status"]=="VALIDATION_INCOMPLETE"
    assert result["validation_questions"]["business_model"]["status"]=="SUPPORTED"
    assert result["validation_questions"]["cycle_position"]["status"]=="DATA_REQUIRED"
    assert len(result["validation_questions"])==len(VALIDATION_QUESTIONS)
    assert not result["investment_certified"]

@pytest.mark.parametrize("symbol,family",[("GMRAIRPORT","INFRASTRUCTURE"),("KNRCON","CONSTRUCTION"),("DEEPAKNTR","SPECIALTY_CHEMICALS"),("BOSCHLTD","AUTO_AUTO_COMPONENTS"),("SONACOMS","AUTO_AUTO_COMPONENTS")])
def test_validation_cohort_symbols_are_classified(symbol,family):
    assert classify_industrial({"symbol":symbol})["model_family"]==family
