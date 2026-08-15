from copy import deepcopy

from app.tools.executor import build_core_read_executor
from app.tools.registry import plan_tools
from financial_engine import calculate
from financials_valuation.answer import format_bank_answer
from financials_valuation.banking import BANKING_MODEL, BANK_KPIS
from financials_valuation.certification import GATES, certify_banking
from financials_valuation.classification import classify_financial_subsector
from financials_valuation.service import evaluate_bank


AS_OF = "2026-08-15"


def cell(value, *, period="FY2026", unit="decimal", source="annual-report", available="2026-06-30"):
    return {"value": value, "period": period, "unit": unit, "currency": "INR",
            "source_id": source, "available_at": available}


def bank_inputs():
    return {
        "market_price": cell(1800, period="2026-08-15", unit="INR/share", source="market-feed", available=AS_OF),
        "book_value_per_share": cell(600, unit="INR/share"),
        "roe": cell(.17), "growth": cell(.07), "cost_of_equity": cell(.12),
        "normalized_eps": cell(90, unit="INR/share"), "gnpa": cell(.015),
        "credit_cost": cell(.006), "cet1": cell(.17),
    }


def scenarios():
    return {
        "BEAR": {"roe": .13, "growth": .05, "cost_of_equity": .13},
        "BASE": {"roe": .17, "growth": .07, "cost_of_equity": .12},
        "BULL": {"roe": .20, "growth": .08, "cost_of_equity": .115},
    }


def pack(symbol="HDFCBANK"):
    return {
        "company": {"symbol": symbol, "financial_subsector": "COMMERCIAL_BANK"},
        "inputs": bank_inputs(), "as_of": AS_OF,
        "peers": [{"symbol": "ICICIBANK", "subsector": "COMMERCIAL_BANK", "pb": 2.8},
                  {"symbol": "NBFC", "subsector": "NBFC", "pb": 7.0}],
        "history": [{"available_at": "2025-06-01", "pb": 2.5},
                    {"available_at": "2027-01-01", "pb": 9.0}],
        "scenarios": scenarios(),
    }


def evaluate(symbol="HDFCBANK"):
    p = pack(symbol)
    return evaluate_bank(company=p["company"], inputs=p["inputs"], as_of=p["as_of"],
                         peers=p["peers"], history=p["history"], scenarios=p["scenarios"])


def test_classification_is_authoritative_and_fails_closed():
    assert classify_financial_subsector({"financial_subsector": "COMMERCIAL_BANK"})["subsector"] == "COMMERCIAL_BANK"
    assert classify_financial_subsector({"canonical_industry": "banks"})["subsector"] == "COMMERCIAL_BANK"
    assert classify_financial_subsector({"name": "Definitely A Bank"})["status"] == "CLASSIFICATION_UNAVAILABLE"


def test_bank_curriculum_has_complete_kpis_and_rejects_ev_ebitda():
    assert len(BANK_KPIS) >= 20
    assert all(k.definition and k.formula and k.preferred_sources and k.limitations for k in BANK_KPIS)
    methods = {m.method: m for m in BANKING_MODEL.valuation_methods}
    assert methods["EV_EBITDA"].tier == "INAPPROPRIATE"
    assert methods["PRICE_TO_BOOK"].tier == "PRIMARY"


def test_bank_afe_math_is_deterministic_and_terminal_growth_fails_closed():
    result = calculate(calculation_id="BANK_PRICE_TO_BOOK", inputs={
        "market_price": bank_inputs()["market_price"],
        "book_value_per_share": bank_inputs()["book_value_per_share"],
    }, as_of=AS_OF)
    assert result["status"] == "SUCCESS" and result["calculated_value"] == 3
    assert result["deterministic"] and not result["model_generated_formula"]
    invalid = calculate(calculation_id="JUSTIFIED_PB", inputs={"roe": .15, "growth": .13, "cost_of_equity": .12})
    assert invalid["status"] == "INVALID_TERMINAL_GROWTH"


def test_full_bank_evaluation_is_research_only_with_pit_peers_and_scenarios():
    result = evaluate()
    assert result["status"] == "OPERATIONAL_NOT_CERTIFIED"
    assert result["valuation"]["current_pb"] == 3
    assert result["valuation"]["current_pe"] == 20
    assert result["valuation"]["peer_median_pb"] == 2.8
    assert result["valuation"]["historical_median_pb"] == 2.5
    assert all(row["epistemic_label"] == "SCENARIO" and row["probability"] is None for row in result["scenarios"].values())
    assert len(result["sensitivity"]["roe_x_cost_of_equity"]) == 9
    assert result["causal_context"]["execution_eligible"] is False
    assert result["execution_eligible"] is False and result["certified"] is False


def test_missing_provenance_future_evidence_and_wrong_classification_are_blocked():
    raw = bank_inputs(); raw["roe"] = .17
    assert evaluate_bank(company={"financial_subsector":"COMMERCIAL_BANK"}, inputs=raw, as_of=AS_OF)["status"] == "DATA_UNAVAILABLE"
    future = bank_inputs(); future["roe"]["available_at"] = "2026-09-01"
    assert evaluate_bank(company={"financial_subsector":"COMMERCIAL_BANK"}, inputs=future, as_of=AS_OF)["status"] == "POINT_IN_TIME_VIOLATION"
    assert evaluate_bank(company={"financial_subsector":"NBFC"}, inputs=bank_inputs(), as_of=AS_OF)["status"] == "CLASSIFICATION_UNAVAILABLE"


def test_adversarial_inputs_fail_validation_and_high_roe_never_recommends():
    bad = bank_inputs(); bad["credit_cost"]["value"] = -.01
    result = evaluate_bank(company={"symbol":"X", "financial_subsector":"COMMERCIAL_BANK"},
                           inputs=bad, as_of=AS_OF, scenarios=scenarios())
    assert result["status"] == "VALIDATION_FAILED"
    rich = bank_inputs(); rich["roe"]["value"] = .30
    result = evaluate_bank(company={"symbol":"X", "financial_subsector":"COMMERCIAL_BANK"},
                           inputs=rich, as_of=AS_OF, scenarios=scenarios())
    assert result["investment_attractiveness"] == "RESEARCH_ONLY"
    assert result["execution_eligible"] is False
    impossible = bank_inputs(); impossible["cet1"]["value"] = 17
    assert evaluate_bank(company={"financial_subsector":"COMMERCIAL_BANK"}, inputs=impossible,
                         as_of=AS_OF)["status"] == "VALIDATION_FAILED"
    assert evaluate_bank(company={"financial_subsector":"COMMERCIAL_BANK"}, inputs=bank_inputs(),
                         as_of="not-a-date")["status"] == "DATA_UNAVAILABLE"


def test_afe_rejects_non_finite_inputs():
    result = calculate(calculation_id="PRICE_TO_BOOK", inputs={"market_price": float("nan"), "book_value_per_share": 10})
    assert result["status"] == "INVALID_INPUT"


def test_client_answer_is_concise_and_discloses_status():
    answer = format_bank_answer(evaluate())
    assert answer["status"] == "RESEARCH_ONLY"
    assert "3.00x book" in answer["answer"]
    assert "not investment-certified" in answer["limitations"]
    assert answer["execution_eligible"] is False


def test_twenty_gate_certification_requires_all_four_banks_and_human_reviewer():
    packs = {symbol: pack(symbol) for symbol in ("HDFCBANK", "ICICIBANK", "AXISBANK", "SBIN")}
    pending = certify_banking(packs)
    assert pending["total_gates"] == len(GATES) == 20
    assert pending["passed_gates"] == 20
    assert pending["certification_status"] == "IN_PROGRESS"
    still_pending = certify_banking(packs, authorized_reviewer="unverified-name")
    assert still_pending["certification_status"] == "IN_PROGRESS"
    passed = certify_banking(packs, authorized_reviewer="investment-methodology-committee",
                             reviewer_authorized=True, review_evidence_id="review-2026-08-15-001")
    assert passed["certification_status"] == "PASSED"
    assert passed["automatic_promotion"] is False
    incomplete = deepcopy(packs); incomplete.pop("SBIN")
    assert certify_banking(incomplete, authorized_reviewer="reviewer", reviewer_authorized=True,
                           review_evidence_id="review-incomplete")["certification_status"] != "PASSED"


def test_ask_agi_plans_and_binds_governed_bank_tool():
    names = {tool["name"] for tool in plan_tools("Should I invest in HDFC Bank?", ticker_hint="HDFCBANK")["tools"]}
    assert "GET_BANK_VALUATION" in names
    assert "GET_BANK_VALUATION" in build_core_read_executor().bound_tools
