"""AGIB v3.4 Track A — Intent Resolution acceptance + CIO routing benchmark."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from ask_pipeline.intent_resolution import resolve_intent
from ask_pipeline.intent_resolution.schema import INTENTS_V2, IRL_VERSION
from ask_pipeline.intent_resolution.temporal import detect_temporal
from ask_pipeline.pipeline import run_complete_ask
from ask_pipeline.policy import execution_policy

ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# CIO exam routing gold labels (Track A — routing only, not answer quality)
# Accept any of the listed intents as correct.
# ---------------------------------------------------------------------------
CIO_ROUTING_GOLD: list[dict] = [
    {"id": "Q1", "q": "Why is HDFC Bank primarily valued using Price-to-Book and Residual Income, while Infosys is commonly valued using EV/EBITDA and DCF? Explain the economic and accounting reasons, not just the formulas.", "intents": {"Explain", "Compare", "Accounting"}, "concept_mode": False, "not_question_type": {"valuation"}},
    {"id": "Q2", "q": "Compare Infosys, TCS, and Wipro. If all three trade at similar P/E multiples, which additional evidence would you retrieve before concluding whether one is undervalued?", "intents": {"Compare", "Analyse"}, "concept_mode": False, "not_question_type": set()},
    {"id": "Q3", "q": "If Titan reports 25% revenue growth but operating cash flow falls sharply, what evidence would you investigate before determining whether growth quality has deteriorated?", "intents": {"Analyse", "Accounting"}, "concept_mode": False},
    {"id": "Q4", "q": "How would you assess whether Asian Paints has maintained its competitive moat over the last decade? Which evidence domains should AGIB retrieve?", "intents": {"Analyse", "Explain"}, "concept_mode": False},
    {"id": "Q5", "q": "Explain why EV/EBITDA is generally inappropriate for banks and insurance companies.", "intents": {"Explain", "Education"}, "concept_mode": True, "not_question_type": {"valuation"}},
    {"id": "Q6", "q": "Why do cement companies often experience valuation expansion before earnings actually improve?", "intents": {"Industry", "Explain"}, "concept_mode": True, "not_question_type": {"valuation"}},
    {"id": "Q7", "q": "Why do software companies typically receive higher valuation multiples than steel producers?", "intents": {"Industry", "Explain", "Compare"}, "concept_mode": True, "not_question_type": {"valuation"}},
    {"id": "Q8", "q": "Compare the business economics of FMCG, IT Services, and PSU Banks. Which KPIs matter most for each and why?", "intents": {"Compare", "Industry"}, "concept_mode": True},
    {"id": "Q9", "q": "If crude oil prices fall by 25%, which Indian industries benefit first, and which benefit only after a lag?", "intents": {"Industry", "Macro", "CrossDomain"}, "concept_mode": True},
    {"id": "Q10", "q": "Explain why hospitals often require a different valuation framework than pharmaceutical manufacturers.", "intents": {"Explain", "Industry"}, "concept_mode": True, "not_question_type": {"valuation"}},
    {"id": "Q11", "q": "The RBI unexpectedly cuts the repo rate by 75 basis points. Trace the complete transmission mechanism through Banks, NBFCs, Real Estate, Auto, IT, and FMCG.", "intents": {"Macro", "Government", "CrossDomain"}, "concept_mode": True},
    {"id": "Q12", "q": "The Government doubles import duties on steel. Which sectors are likely to benefit, and which are likely to suffer?", "intents": {"Government", "Industry", "CrossDomain"}, "concept_mode": True},
    {"id": "Q13", "q": "GST collections hit a record high for six consecutive months. What conclusions can—and cannot—be drawn from this?", "intents": {"Government", "Macro", "Analyse"}, "concept_mode": True},
    {"id": "Q14", "q": "How would a weakening Indian Rupee affect Infosys, Indigo, Maruti, and Oil Marketing Companies?", "intents": {"Macro", "CrossDomain", "Analyse"}, "concept_mode": False},
    {"id": "Q15", "q": "Inflation rises while GDP growth slows. Which sectors historically outperform in such an environment?", "intents": {"Macro", "Industry"}, "concept_mode": True},
    {"id": "Q16", "q": "Suppose all of the following occur simultaneously: RBI cuts rates; Crude oil falls 20%; UPI transactions reach record highs; GST collections rise; The Government announces a new PLI scheme. Identify the Indian sectors most likely to benefit over the next 12–24 months.", "intents": {"CrossDomain", "Macro"}, "concept_mode": True},
    {"id": "Q17", "q": "A company reports excellent quarterly earnings, but its stock falls 8% the next day. List at least ten institutional reasons why this can happen.", "intents": {"Analyse", "Explain"}, "concept_mode": True, "not_question_type": {"valuation"}},
    {"id": "Q18", "q": "Two companies have identical revenue growth and EPS growth, but one trades at twice the valuation multiple. Explain all plausible institutional reasons.", "intents": {"Explain", "Compare"}, "concept_mode": True, "not_question_type": {"valuation"}},
    {"id": "Q19", "q": "How should AGIB determine whether a company deserves a premium valuation rather than simply identifying that it has one?", "intents": {"Explain", "Analyse"}, "concept_mode": True, "not_question_type": {"valuation"}},
    {"id": "Q20", "q": "What evidence should AGIB gather before recommending that an analyst initiate research coverage on a newly listed Indian company?", "intents": {"Analyse", "Documents", "Explain"}, "concept_mode": True},
    {"id": "Q21", "q": "Using only institutional documents, explain how you would evaluate whether management's capital allocation policy has improved over the last five years.", "intents": {"Documents", "Explain", "Analyse"}, "concept_mode": True},
    {"id": "Q22", "q": "Which sections of an annual report are most useful for identifying emerging risks before they appear in the financial statements?", "intents": {"Documents", "Explain"}, "concept_mode": True},
    {"id": "Q23", "q": "How would you detect inconsistencies between an investor presentation and the audited annual report?", "intents": {"Documents", "Explain", "Analyse"}, "concept_mode": True},
    {"id": "Q24", "q": "Replay Infosys as of 31 March 2020. Describe only the evidence that would have been available on that date. Explain how AGIB prevents future information leakage.", "intents": {"HistoricalReplay"}, "concept_mode": False, "as_of": "2020-03-31"},
    {"id": "Q25", "q": "Imagine you are presenting Reliance Industries to an Investment Committee. Construct the institutional evidence package you would prepare before anyone begins valuation. Do not value the company.", "intents": {"CrossDomain", "Analyse"}, "concept_mode": False, "not_question_type": {"valuation"}},
]


def test_irl_version_and_taxonomy() -> None:
    assert IRL_VERSION.startswith("intent-resolution")
    assert "Explain" in INTENTS_V2
    assert "HistoricalReplay" in INTENTS_V2
    assert "CrossDomain" in INTENTS_V2


def test_temporal_as_of_and_fy() -> None:
    t = detect_temporal("Replay Infosys as of 31 March 2020")
    assert t["as_of"] == "2020-03-31"
    assert t["is_historical"] is True
    fy = detect_temporal("Show the books for FY19")
    assert fy["as_of"] == "2019-03-31"
    covid = detect_temporal("What did the market look like before COVID?")
    assert covid["as_of"] == "2020-03-01"


def test_concept_mode_no_infosys_pollution() -> None:
    irl = resolve_intent(
        "Explain why EV/EBITDA is generally inappropriate for banks and insurance companies.",
        ticker_hint="INFY",
    )
    assert irl["concept_mode"] is True
    assert irl["primary"] is None
    assert irl["entities"] == []
    assert irl["entity_pollution_blocked"] is True
    assert irl["ignored_ticker_hint"] == "INFY"
    assert irl["question_type"] == "education"
    assert irl["intent"] in {"Explain", "Education"}


def test_why_not_forced_to_valuation() -> None:
    irl = resolve_intent(
        "Why do cement companies often experience valuation expansion before earnings actually improve?"
    )
    assert irl["intent"] != "Valuation"
    assert irl["question_type"] != "valuation"


def test_historical_replay_routing() -> None:
    irl = resolve_intent(
        "Replay Infosys as of 31 March 2020. Describe only the evidence available on that date."
    )
    assert irl["intent"] == "HistoricalReplay"
    assert irl["as_of"] == "2020-03-31"
    assert irl["question_type"] == "education"


def test_compare_binds_entities() -> None:
    irl = resolve_intent("Compare Infosys, TCS, and Wipro on cash conversion and ROIC.")
    assert irl["intent"] == "Compare"
    assert irl["concept_mode"] is False
    ids = {e["id"] for e in irl["entities"]}
    assert "INFY" in ids and "TCS" in ids and "WIPRO" in ids


def test_policy_education_skips_live_ie() -> None:
    pol = execution_policy(
        intent="Explain",
        has_entity=False,
        question_type="education",
        concept_mode=True,
    )
    assert pol["education"] is True
    assert pol["build_institutional_evidence"] is False
    assert pol["concept_mode"] is True


def test_pipeline_soft_wire_concept_path() -> None:
    out = run_complete_ask(
        "Explain why EV/EBITDA is generally inappropriate for banks and insurance companies.",
        ticker_hint="INFY",
    )
    irl = out.get("intent_resolution") or {}
    assert irl.get("concept_mode") is True
    assert out.get("concept_mode") is True
    assert (out.get("entities") or {}).get("primary") is None
    gov = out.get("governance") or {}
    assert gov.get("path") == "education"
    assert gov.get("question_type") == "education"
    # Must not bind Infosys into governance entity
    assert not (gov.get("entity") or {}).get("entity_id")


def test_pipeline_historical_inherits_as_of() -> None:
    out = run_complete_ask(
        "Replay Infosys as of 31 March 2020. Describe only the evidence that would have been available on that date.",
    )
    assert out.get("as_of") == "2020-03-31"
    assert (out.get("intent_resolution") or {}).get("intent") == "HistoricalReplay"
    assert (out.get("knowledge") or {}).get("as_of") == "2020-03-31"
    gov = out.get("governance") or {}
    assert gov.get("path") == "education"


def test_cio_routing_benchmark() -> None:
    """Exit gate: intent routing accuracy >98%, historical 100%, pollution <1%."""
    hits = 0
    historical_ok = 0
    historical_n = 0
    pollution = 0
    pollution_n = 0
    failures: list[str] = []

    for row in CIO_ROUTING_GOLD:
        irl = resolve_intent(row["q"])
        ok = irl["intent"] in row["intents"]
        if ok:
            hits += 1
        else:
            failures.append(f"{row['id']}: got {irl['intent']} expected {row['intents']}")

        if row["id"] == "Q24" or "HistoricalReplay" in row["intents"]:
            historical_n += 1
            if irl["intent"] == "HistoricalReplay" and (
                not row.get("as_of") or irl.get("as_of") == row.get("as_of")
            ):
                historical_ok += 1

        if row.get("concept_mode") is True:
            pollution_n += 1
            # Pollution = bound company entity on concept question
            if irl.get("primary") or (irl.get("entities") or []):
                # Allow only if gold says concept_mode False; here True means must be empty
                pollution += 1
                failures.append(f"{row['id']}: entity pollution {irl.get('primary')}")

        if row.get("not_question_type") and irl.get("question_type") in row["not_question_type"]:
            failures.append(
                f"{row['id']}: bad question_type {irl.get('question_type')}"
            )
            # Count as miss for accuracy too
            if ok:
                hits -= 1

    accuracy = hits / len(CIO_ROUTING_GOLD)
    hist_acc = historical_ok / max(historical_n, 1)
    poll_rate = pollution / max(pollution_n, 1)

    assert accuracy >= 0.98, f"intent accuracy {accuracy:.2%} failures={failures}"
    assert hist_acc == 1.0, f"historical routing {hist_acc} failures={failures}"
    assert poll_rate <= 0.01, f"entity pollution {poll_rate:.2%} failures={failures}"


def test_no_kf_mutation_in_irl_ast() -> None:
    root = ROOT / "intent_resolution"
    banned = ("run_daily_pipeline", "get_company", "package_for_governance")
    for path in root.rglob("*.py"):
        if "tests" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in banned
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                assert node.func.attr not in banned


# ---------------------------------------------------------------------------
# Sprint 3.4 — Intent Optimisation (RCI portfolio / allocation clusters)
# ---------------------------------------------------------------------------
PORTFOLIO_CLUSTER_CASES = [
    (
        "portfolio_decision",
        "Portfolio decision: overweight private banks vs PSU banks. What macro, industry, and company evidence must AGIB assemble before sizing the position?",
        "Portfolio",
    ),
    (
        "allocation",
        "Portfolio decision: defensive tilt into staples. What evidence before sector allocation?",
        "Portfolio",
    ),
    (
        "rebalancing",
        "Should we rebalance the portfolio away from high-beta cyclicals into a hike cycle?",
        "Portfolio",
    ),
    (
        "sector_allocation",
        "Portfolio decision: infrastructure beneficiaries of budget capex. Assemble evidence before sector allocation and position sizing.",
        "Portfolio",
    ),
    (
        "risk_review",
        "Construct a risk checklist for asset quality deterioration affecting HDFCBANK. What evidence would falsify complacency?",
        "Risk",
    ),
    (
        "watchlist",
        "Add exporters to the watchlist on INR weakness before any portfolio decision.",
        "Portfolio",
    ),
    (
        "investment_committee",
        "Imagine you are presenting Reliance Industries to an Investment Committee. Construct the institutional evidence package before valuation.",
        "CrossDomain",
    ),
    (
        "accounting_investigation",
        "How would you investigate revenue recognition aggressiveness at INFY? Which statements and notes matter most?",
        "Accounting",
    ),
    (
        "capital_allocation_not_portfolio",
        "How would you evaluate capital allocation quality at ASIANPAINT over the last five years?",
        "Analyse",
    ),
    (
        "pair_trade_stays_portfolio",
        "Portfolio decision: pair trade IT vs metals. What evidence before sizing the position?",
        "Portfolio",
    ),
]


@pytest.mark.parametrize("case_id,question,expected", PORTFOLIO_CLUSTER_CASES)
def test_sprint34_portfolio_intent_clusters(case_id: str, question: str, expected: str) -> None:
    irl = resolve_intent(question)
    assert irl["intent"] == expected, f"{case_id}: got {irl['intent']} scores={irl.get('intent_scores')}"
    assert irl.get("primary_intent") == expected
    assert irl.get("intent_why_won"), "confidence must explain why intent won"
    # Must not collapse portfolio clusters into Generic/Unknown
    assert irl["intent"] != "Unknown"


def test_sprint34_mixed_and_ambiguous_intent() -> None:
    mixed = resolve_intent(
        "Portfolio decision: quality premium vs value trap. What macro and risk evidence before rebalancing?"
    )
    assert mixed["intent"] == "Portfolio"
    assert mixed.get("primary_intent") == "Portfolio"
    assert mixed.get("intent_confidence", 0) >= 0.7
    amb = resolve_intent(
        "How would you investigate inventory days spike at TITAN? Which statements and notes matter most?"
    )
    assert amb["intent"] == "Accounting"
    assert amb.get("secondary_intent") in {"Analyse", "Documents", "Explain", "Portfolio", None}
    assert amb.get("intent_why_won")


INVESTMENT_ASSISTANT_ROUTING = [
    ("What is AGI’s view on Zen Technologies’ ₹295 crore defence order?", {"Analyse", "CorporateEvents"}),
    ("What is your view on Reliance?", {"Analyse"}),
    ("Give me a quick take on HDFC Bank", {"Analyse"}),
    ("What changed after Infosys earnings?", {"Earnings", "CorporateEvents"}),
    ("Is TCS expensive at its current valuation?", {"Valuation"}),
    ("What are the main risks to Zomato?", {"Risk"}),
    ("Compare BEL with HAL", {"Compare"}),
    ("Would you buy Asian Paints for a five-year portfolio?", {"Portfolio"}),
    ("What would change your view?", {"Analyse"}),
    ("Build the bull, base and bear case for Bajaj Finance", {"Analyse"}),
]


@pytest.mark.parametrize("question,expected", INVESTMENT_ASSISTANT_ROUTING)
def test_investment_assistant_routing(question: str, expected: set[str]) -> None:
    irl = resolve_intent(question)
    assert irl["intent"] in expected, (
        f"got {irl['intent']} expected {expected} scores={irl.get('intent_scores')}"
    )
    assert irl["intent"] != "Unknown"


NSE_OPERATING_SYSTEM_ROUTING = [
    ("What's going wrong with TCS?", "TCS", "CompanyOverview"),
    ("Why is it falling?", "TCS", "MarketMovement"),
    ("Is the valuation justified?", "TCS", "Valuation"),
    ("What changed after earnings?", "TCS", "Earnings"),
    ("Compare it with Infosys.", "TCS", "Compare"),
    ("Who has better cash conversion?", "TCS", "Compare"),
    ("Which IT company is cheapest relative to history?", None, "Screening"),
    ("Find banks where ROE is improving but valuation is below historical average.", None, "Screening"),
    ("Which NSE companies have promoter holding rising?", None, "Screening"),
    ("Show companies where earnings are improving but price hasn't reacted.", None, "Screening"),
    ("Which banking stocks have falling NIM but improving asset quality?", None, "Screening"),
    ("Find companies where FII ownership rose for 3 quarters.", None, "Screening"),
    ("What are the upcoming catalysts for Reliance?", "RELIANCE", "Catalyst"),
    ("How did AGI view this company six months ago?", "TCS", "HistoricalChange"),
]


@pytest.mark.parametrize("question,ticker_hint,expected", NSE_OPERATING_SYSTEM_ROUTING)
def test_nse_operating_system_routes_to_specific_workflow(
    question: str, ticker_hint: str | None, expected: str,
) -> None:
    irl = resolve_intent(question, ticker_hint=ticker_hint)
    assert irl["intent"] == expected, (
        f"got {irl['intent']} expected {expected} scores={irl.get('intent_scores')}"
    )
    workflow = (irl.get("evidence_requirements") or {}).get("research_workflow") or []
    assert len(workflow) >= 3
    assert (irl.get("evidence_requirements") or {}).get("evidence_types_required")
