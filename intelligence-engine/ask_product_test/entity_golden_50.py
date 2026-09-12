"""Entity Golden 50 — permanent regression. Never regress Air India → BHARTIARTL."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ask_product_test.entity_intelligence_acceptance_v1 import evaluate_ei_case

ENTITY_GOLDEN_50: List[Dict[str, Any]] = []


def _g(
    prompt: str,
    *,
    expect_state: str,
    expect_ticker: Optional[str] = None,
    expect_name_any: Optional[List[str]] = None,
    forbid_tickers: Optional[List[str]] = None,
    forbid_names: Optional[List[str]] = None,
    allow_planner: Optional[bool] = None,
    category: str = "golden",
):
    ENTITY_GOLDEN_50.append(
        {
            "id": f"EG50-{len(ENTITY_GOLDEN_50)+1:02d}",
            "category": category,
            "prompt": prompt,
            "expect_state": expect_state,
            "expect_ticker": expect_ticker,
            "expect_name_any": expect_name_any or [],
            "forbid_tickers": [t.upper() for t in (forbid_tickers or [])],
            "forbid_names": [n.lower() for n in (forbid_names or [])],
            "allow_planner": allow_planner,
        }
    )


_g("Air India", expect_state="verified_entity", expect_name_any=["air india"], forbid_tickers=["BHARTIARTL", "BSE517514"], forbid_names=["bharti airtel"], allow_planner=False)
_g("Explain Air India", expect_state="verified_entity", expect_name_any=["air india"], forbid_tickers=["BHARTIARTL"], allow_planner=False)
_g("What is the investment thesis for Air India?", expect_state="verified_entity", expect_name_any=["air india"], forbid_tickers=["BHARTIARTL"], allow_planner=False)
_g("IndiGo", expect_state="verified_entity", expect_ticker="INDIGO", expect_name_any=["indigo"], allow_planner=True)
_g("Indigo", expect_state="verified_entity", expect_ticker="INDIGO", allow_planner=True)
_g("Reliance", expect_state="verified_entity", expect_ticker="RELIANCE", allow_planner=True)
_g("RIL", expect_state="verified_entity", expect_ticker="RELIANCE", allow_planner=True)
_g("TCS", expect_state="verified_entity", expect_ticker="TCS", allow_planner=True)
_g("Infosys", expect_state="verified_entity", expect_ticker="INFY", allow_planner=True)
_g("HDFC Bank", expect_state="verified_entity", expect_ticker="HDFCBANK", allow_planner=True)
_g("HDFC", expect_state="clarification_required", allow_planner=False)
_g("HDFC Life", expect_state="verified_entity", expect_ticker="HDFCLIFE", forbid_tickers=["HDFCBANK"], allow_planner=True)
_g("HDFC AMC", expect_state="verified_entity", expect_ticker="HDFCAMC", forbid_tickers=["HDFCBANK"], allow_planner=True)
_g("JSW Energy", expect_state="verified_entity", expect_ticker="JSWENERGY", forbid_tickers=["JSWSTEEL"], allow_planner=True)
_g("JSW Steel", expect_state="verified_entity", expect_ticker="JSWSTEEL", forbid_tickers=["JSWENERGY"], allow_planner=True)
_g("Titan Company", expect_state="verified_entity", expect_ticker="TITAN", forbid_tickers=["TITANBIO"], allow_planner=True)
_g("Titan Biotech", expect_state="verified_entity", expect_ticker="TITANBIO", forbid_tickers=["TITAN"], allow_planner=True)
_g("Reliance Infrastructure", expect_state="verified_entity", expect_ticker="RELINFRA", forbid_tickers=["RELIANCE"], allow_planner=True)
_g("Reliance Industrial Infrastructure", expect_state="verified_entity", expect_ticker="RIIL", forbid_tickers=["RELIANCE"], allow_planner=True)
_g("Visa", expect_state="unsupported_entity", allow_planner=False)
_g("Costco", expect_state="unsupported_entity", allow_planner=False)
_g("Ferrari", expect_state="unsupported_entity", allow_planner=False)
_g("Tesla", expect_state="unsupported_entity", allow_planner=False)
_g("OpenAI", expect_state="unsupported_entity", allow_planner=False)
_g("XYZ Quantum Robotics", expect_state="unsupported_entity", allow_planner=False)
_g("ABC Pharma Holdings", expect_state="unsupported_entity", allow_planner=False)
_g("Asian Paints", expect_state="verified_entity", expect_ticker="ASIANPAINT", allow_planner=True)
_g("DMart", expect_state="verified_entity", expect_ticker="DMART", allow_planner=True)
_g("Bharti Airtel", expect_state="verified_entity", expect_ticker="BHARTIARTL", allow_planner=True)
_g("Airtel", expect_state="verified_entity", expect_ticker="BHARTIARTL", allow_planner=True)
_g("Flipkart", expect_state="verified_entity", expect_name_any=["flipkart"], allow_planner=False)
_g("BYJU'S", expect_state="verified_entity", expect_name_any=["byju"], allow_planner=False)
_g("Zomato Hyperpure", expect_state="verified_entity", expect_name_any=["hyperpure"], allow_planner=False)
_g("Explain ROIC", expect_state="verified_concept", allow_planner=True)
_g("Explain airline industry economics", expect_state="verified_industry", allow_planner=True)
_g("What is inflation?", expect_state="verified_macro", allow_planner=True)
_g("Tata", expect_state="clarification_required", allow_planner=False)
_g("JSW", expect_state="clarification_required", allow_planner=False)
_g("Titan", expect_state="clarification_required", allow_planner=False)
_g("INFY", expect_state="verified_entity", expect_ticker="INFY", allow_planner=True)
_g("APNT", expect_state="verified_entity", expect_ticker="ASIANPAINT", allow_planner=True)
_g("Air India investment committee", expect_state="verified_entity", expect_name_any=["air india"], forbid_tickers=["BHARTIARTL"], allow_planner=False)
_g("Committee vote Neutral Air India", expect_state="verified_entity", expect_name_any=["air india"], forbid_tickers=["BHARTIARTL"], allow_planner=False)
_g("Reliance Industries Limited", expect_state="verified_entity", expect_ticker="RELIANCE", allow_planner=True)
_g("InterGlobe Aviation", expect_state="verified_entity", expect_ticker="INDIGO", allow_planner=True)
_g("Avenue Supermarts", expect_state="verified_entity", expect_ticker="DMART", allow_planner=True)
_g("Quorvex Analytics Private Limited", expect_state="unsupported_entity", allow_planner=False)
_g("Air India vs Bharti Airtel", expect_state="verified_entity", expect_name_any=["air india"], forbid_tickers=["BHARTIARTL"], allow_planner=False)
_g("Should I analyse Air India as BHARTIARTL?", expect_state="verified_entity", expect_name_any=["air india"], forbid_tickers=["BHARTIARTL"], allow_planner=False)
_g("HDFC Bank Limited", expect_state="verified_entity", expect_ticker="HDFCBANK", allow_planner=True)

assert len(ENTITY_GOLDEN_50) == 50, len(ENTITY_GOLDEN_50)


def evaluate_golden_case(case: Dict[str, Any], contract: Dict[str, Any]) -> Dict[str, Any]:
    return evaluate_ei_case(case, contract)
