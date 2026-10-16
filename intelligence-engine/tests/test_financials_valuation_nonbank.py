from app.tools.executor import build_core_read_executor
from app.tools.registry import plan_tools
from financials_valuation.answer import format_financial_answer
from financials_valuation.facade import evaluate_financial_institution
from financials_valuation.nonbank_certification import certify_subsector
from financials_valuation.nonbank_models import MODELS
from financials_valuation.nonbank_service import PROFILES, evaluate_financial_subsector
from financials_valuation.persistence import seed_financial_models
from financials_valuation.research_context import financial_research_context

AS_OF = "2026-08-15"


def cell(value, key=""):
    unit = "INR million" if key in {"enterprise_value","revenue","gross_profit","tpv","cash_burn","segment_1_value","segment_2_value","segment_3_value","net_debt","aum","net_flows","trading_volume","active_clients","vnb","ape"} else "decimal"
    if key in {"market_price","book_value_per_share","normalized_eps","embedded_value_per_share","fcf_per_share","revenue_per_client"}: unit="INR/share"
    return {"value":value,"period":"FY2026","unit":unit,"currency":"INR","source_id":f"source:{key}","available_at":"2026-06-30"}


VALUES = {
    "market_price":100,"book_value_per_share":50,"normalized_eps":5,"roe":.16,"growth":.06,
    "cost_of_equity":.12,"gnpa":.02,"credit_cost":.01,"capital_adequacy":.18,"leverage":5,
    "ltv":.65,"embedded_value_per_share":60,"vnb":100,"ape":500,"persistency":.85,"solvency":.18,
    "claims_ratio":.65,"expense_ratio":.25,"aum":10000,"net_flows":500,"fee_yield":.01,
    "operating_margin":.35,"retention":.9,"active_clients":1000,"trading_volume":100000,
    "market_share":.2,"revenue_per_client":100,"fcf_per_share":4,"enterprise_value":1000,
    "revenue":200,"gross_profit":100,"tpv":20000,"contribution_profit":20,"cash_burn":10,
    "segment_1_value":500,"segment_2_value":300,"segment_3_value":200,"net_debt":100,"holdco_discount":.1,
    "payout_ratio":.4,"agi_growth_expectation":.08,"terminal_multiple":5,"horizon_years":5,"market_cap":800,
}


def inputs_for(subsector):
    return {key:cell(VALUES[key],key) for key in PROFILES[subsector].required}


def scenarios_for(subsector):
    profile=PROFILES[subsector]; base=inputs_for(subsector)
    return {name:{key:float(base[key]["value"])*factor for key in profile.calculation_inputs}
            for name,factor in (("BEAR",.9),("BASE",1),("BULL",1.1))}


def pack(subsector):
    return {"inputs":inputs_for(subsector),"as_of":AS_OF,
            "peers":[{"subsector":subsector,"primary_multiple":2.0},{"subsector":"WRONG","primary_multiple":99}],
            "history":[{"available_at":"2025-01-01","primary_multiple":1.8},{"available_at":"2027-01-01","primary_multiple":99}],
            "scenarios":scenarios_for(subsector)}


def test_every_nonbank_financial_subsector_has_distinct_operational_model():
    assert set(MODELS)==set(PROFILES)
    assert len(MODELS)==12
    for subsector, model in MODELS.items():
        p=pack(subsector)
        result=evaluate_financial_subsector(company={"symbol":"TEST","financial_subsector":subsector},**p)
        assert result["status"]=="OPERATIONAL_NOT_CERTIFIED", (subsector,result)
        assert result["model"]["sector_id"]==model.sector_id
        assert result["valuation"]["peer_median"]==2.0
        assert result["valuation"]["historical_median"]==1.8
        assert len(result["sensitivity"]["grid"])==9
        assert result["market_expectations"]["classification"]!="DATA_INSUFFICIENT"
        assert all(row["status"]=="SUCCESS" for row in result["scenarios"].values())
        assert result["execution_eligible"] is False and result["certified"] is False


def test_facade_routes_bank_and_nonbank_without_name_inference():
    p=pack("NBFC")
    result=evaluate_financial_institution(company={"symbol":"BAJFINANCE","financial_subsector":"NBFC"},**p)
    assert result["classification"]["subsector"]=="NBFC"
    unknown=evaluate_financial_institution(company={"name":"Looks Financial"},inputs={},as_of=AS_OF)
    assert unknown["status"]=="CLASSIFICATION_UNAVAILABLE"


def test_future_missing_and_impossible_inputs_fail_closed_for_every_subsector():
    for subsector, profile in PROFILES.items():
        base=inputs_for(subsector); base.pop(profile.required[0])
        assert evaluate_financial_subsector(company={"financial_subsector":subsector},inputs=base,as_of=AS_OF)["status"]=="DATA_UNAVAILABLE"
        future=inputs_for(subsector); future[profile.required[0]]["available_at"]="2027-01-01"
        assert evaluate_financial_subsector(company={"financial_subsector":subsector},inputs=future,as_of=AS_OF)["status"]=="POINT_IN_TIME_VIOLATION"
        bad=inputs_for(subsector); bad[profile.positive[0]]["value"]=-1
        assert evaluate_financial_subsector(company={"financial_subsector":subsector},inputs=bad,as_of=AS_OF)["status"]=="VALIDATION_FAILED"


def test_methods_are_sector_specific_and_known_bad_methods_are_blocked():
    assert next(m for m in MODELS["LIFE_INSURANCE"].valuation_methods if m.method=="EV_EBITDA").tier=="INAPPROPRIATE"
    assert next(m for m in MODELS["NBFC"].valuation_methods if m.method=="EV_EBITDA").tier=="INAPPROPRIATE"
    assert MODELS["FINTECH_PAYMENTS"].valuation_methods[0].method=="EV_SALES"
    assert MODELS["DIVERSIFIED_FINANCIALS"].valuation_methods[0].method=="SOTP"


def test_nonbank_answers_are_concise_research_only():
    result=evaluate_financial_subsector(company={"symbol":"AMC","financial_subsector":"ASSET_MANAGEMENT"},**pack("ASSET_MANAGEMENT"))
    answer=format_financial_answer(result)
    assert answer["status"]=="RESEARCH_ONLY"
    assert "not a recommendation" in answer["answer"]
    assert answer["execution_eligible"] is False


def test_certification_harness_never_self_certifies_and_exposes_unfinished_gates():
    for subsector in PROFILES:
        packs={"SAMPLE1":pack(subsector),"SAMPLE2":pack(subsector)}
        result=certify_subsector(subsector,packs,authorized_reviewer="name-only")
        assert result["total_gates"]==20
        assert result["certification_status"]!="PASSED"
        assert result["gates"]["point_in_time"] and result["gates"]["missing_data"] and result["gates"]["adversarial"]
        assert result["automatic_promotion"] is False


def test_all_models_seed_idempotently_without_certifying():
    calls=[]
    def transport(method,table,**kwargs): calls.append((method,table,kwargs)); return []
    first=seed_financial_models(transport=transport); second=seed_financial_models(transport=transport)
    assert first["models"]==second["models"]==13
    assert first["certified_models"]==0 and first["execution_eligible_models"]==0
    assert [r["content_hash"] for r in first["results"]]==[r["content_hash"] for r in second["results"]]


def test_ask_agi_plans_and_binds_financial_subsector_tool():
    names={row["name"] for row in plan_tools("Is this NBFC valuation attractive?",ticker_hint="BAJFINANCE")["tools"]}
    assert "GET_FINANCIAL_VALUATION" in names
    assert "GET_FINANCIAL_VALUATION" in build_core_read_executor().bound_tools


def test_ask_research_context_exposes_curriculum_but_not_calculation():
    context=financial_research_context("AMC",loader=lambda _: {"master":{"financial_subsector":"ASSET_MANAGEMENT"}})
    assert context["status"]=="MODEL_CONTEXT"
    assert context["sector_id"]==MODELS["ASSET_MANAGEMENT"].sector_id
    assert "fee_yield" in context["required_evidence"]
    assert context["calculation_status"]=="REQUIRES_PROVENANCE_COMPLETE_INPUT_PACK"
    assert context["execution_eligible"] is False and context["certified"] is False
    unknown=financial_research_context("X",loader=lambda _: {"master":{"company_name":"Finance Name"}})
    assert unknown["status"]=="CLASSIFICATION_UNAVAILABLE"
