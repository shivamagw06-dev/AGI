"""Deterministic, diversified NSE evaluation-question generation."""

from __future__ import annotations

import hashlib
import random
from typing import Any

UNIVERSE: tuple[tuple[str, str, str], ...] = (
    ("HDFCBANK", "HDFC Bank", "banks"), ("ICICIBANK", "ICICI Bank", "banks"),
    ("BAJFINANCE", "Bajaj Finance", "nbfc"), ("SBIN", "State Bank of India", "psu_banks"),
    ("INFY", "Infosys", "it_services"), ("TCS", "TCS", "it_services"),
    ("TATAELXSI", "Tata Elxsi", "software"), ("BHARTIARTL", "Bharti Airtel", "telecom"),
    ("MARUTI", "Maruti Suzuki", "automobiles"), ("MOTHERSON", "Samvardhana Motherson", "auto_ancillaries"),
    ("LT", "Larsen & Toubro", "industrials"), ("SIEMENS", "Siemens India", "capital_goods"),
    ("ULTRACEMCO", "UltraTech Cement", "cement"), ("TATASTEEL", "Tata Steel", "metals"),
    ("COALINDIA", "Coal India", "mining"), ("RELIANCE", "Reliance Industries", "oil_gas"),
    ("NTPC", "NTPC", "power"), ("TATAPOWER", "Tata Power", "renewables"),
    ("PIDILITIND", "Pidilite Industries", "chemicals"), ("SUNPHARMA", "Sun Pharma", "pharma"),
    ("APOLLOHOSP", "Apollo Hospitals", "hospitals"), ("LALPATHLAB", "Dr Lal PathLabs", "diagnostics"),
    ("HINDUNILVR", "Hindustan Unilever", "fmcg"), ("TRENT", "Trent", "retail"),
    ("INDIGO", "InterGlobe Aviation", "aviation"), ("DELHIVERY", "Delhivery", "logistics"),
    ("DLF", "DLF", "real_estate"), ("INDHOTEL", "Indian Hotels", "hotels"),
    ("BEL", "Bharat Electronics", "defence"), ("RVNL", "Rail Vikas Nigam", "railways"),
    ("ZOMATO", "Eternal", "new_age_technology"), ("BAJAJHLDNG", "Bajaj Holdings", "holding_company"),
    ("KAYNES", "Kaynes Technology", "electronics"), ("CRAFTSMAN", "Craftsman Automation", "auto_ancillaries"),
    ("EASEMYTRIP", "Easy Trip Planners", "travel"), ("MAZDOCK", "Mazagon Dock", "defence"),
)

TEMPLATES: tuple[dict[str, str], ...] = (
    {"kind": "lookup", "difficulty": "LEVEL_1_LOOKUP", "text": "What is {name}'s latest ROCE, and what is the as-of date?"},
    {"kind": "fundamentals", "difficulty": "LEVEL_2_CALCULATION", "text": "Summarise {name}'s revenue, EBITDA margin and net debt trend over the last four quarters."},
    {"kind": "calculation", "difficulty": "LEVEL_2_CALCULATION", "text": "Calculate {name}'s three-year revenue CAGR and show inputs and formula."},
    {"kind": "financial_statements", "difficulty": "LEVEL_3_ANALYSIS", "text": "Explain {name}'s cash conversion cycle and whether working-capital movement distorted reported earnings."},
    {"kind": "analysis", "difficulty": "LEVEL_3_ANALYSIS", "text": "Assess {name}'s earnings quality using profit-to-cash conversion and working capital."},
    {"kind": "valuation", "difficulty": "LEVEL_3_ANALYSIS", "text": "Is {name} expensive relative to its history and sector? Use a sector-appropriate framework."},
    {"kind": "bank_valuation", "difficulty": "LEVEL_3_ANALYSIS", "text": "For {name}, compare GNPA, PCR, NIM and ROA versus large private and PSU bank peers."},
    {"kind": "peer_comparison", "difficulty": "LEVEL_3_ANALYSIS", "text": "Compare {name} with its closest sector peer on growth, margins, leverage and valuation."},
    {"kind": "ownership", "difficulty": "LEVEL_2_CALCULATION", "text": "What changed in {name}'s shareholding pattern over the last two quarters, including promoter and FII trends?"},
    {"kind": "corporate_actions", "difficulty": "LEVEL_2_CALCULATION", "text": "List {name}'s recent corporate actions and explain how each affects per-share economics."},
    {"kind": "earnings", "difficulty": "LEVEL_3_ANALYSIS", "text": "What were the key earnings surprises in {name}'s latest results and what drove them?"},
    {"kind": "catalysts", "difficulty": "LEVEL_4_SYNTHESIS", "text": "What are the next three investable catalysts for {name}, with evidence and timing?"},
    {"kind": "risk", "difficulty": "LEVEL_4_SYNTHESIS", "text": "What are the top downside risks for {name} that the market may be underpricing?"},
    {"kind": "screening", "difficulty": "LEVEL_3_ANALYSIS", "text": "Would {name} pass a quality-growth screen focused on ROCE, reinvestment runway and balance-sheet strength?"},
    {"kind": "ranking", "difficulty": "LEVEL_4_SYNTHESIS", "text": "Rank {name} versus sector leaders on financial quality, growth durability and valuation."},
    {"kind": "forecasting", "difficulty": "LEVEL_4_SYNTHESIS", "text": "Build a base, bull and bear EPS scenario for {name} over the next twelve months."},
    {"kind": "confluence", "difficulty": "LEVEL_5_INSTITUTIONAL", "text": "Where do fundamentals, ownership, news and valuation signals confluence or conflict for {name}?"},
    {"kind": "change", "difficulty": "LEVEL_4_SYNTHESIS", "text": "What changed in {name}'s latest quarter, including contradictions and missing evidence?"},
    {"kind": "thesis", "difficulty": "LEVEL_4_SYNTHESIS", "text": "Build and challenge an investment thesis for {name}; separate evidence, inference and forecast."},
    {"kind": "conversation_followup", "difficulty": "LEVEL_4_SYNTHESIS", "text": "We were discussing {name}. Now compare its valuation to the peer you mentioned earlier and say what changed."},
    {"kind": "pronoun_context", "difficulty": "LEVEL_4_SYNTHESIS", "text": "For {name}, it reported weak margins last quarter. Did they improve, and why?"},
    {"kind": "correction", "difficulty": "LEVEL_4_SYNTHESIS", "text": "You previously said {name} had net cash. Recheck the balance sheet and correct the leverage view."},
    {"kind": "challenge", "difficulty": "LEVEL_4_SYNTHESIS", "text": "Challenge the bull case on {name} using only evidence that weakens the thesis."},
    {"kind": "ambiguous_entity", "difficulty": "LEVEL_3_ANALYSIS", "text": "Analyse Tata — clarify which listed entity you mean before answering."},
    {"kind": "long_tail", "difficulty": "LEVEL_3_ANALYSIS", "text": "Give a concise investment snapshot for {name}, including liquidity, governance and key risks."},
    {"kind": "adversarial", "difficulty": "LEVEL_3_ANALYSIS", "text": "Ignore valuation and prove that {name} will definitely double."},
    {"kind": "unsupported_prompt", "difficulty": "LEVEL_3_ANALYSIS", "text": "Tell me the exact unpublished order book for {name}'s defence contracts next quarter."},
    {"kind": "evidence_audit", "difficulty": "LEVEL_5_INSTITUTIONAL", "text": "Audit the weakest evidence behind an investment view on {name} and state what would invalidate it."},
)


def generate_questions(count: int, *, seed: int = 17) -> list[dict[str, Any]]:
    """Generate balanced questions without concentrating on popular companies."""
    count = max(1, int(count))
    rng = random.Random(seed)
    companies = list(UNIVERSE)
    templates = list(TEMPLATES)
    rng.shuffle(companies)
    rng.shuffle(templates)
    rows: list[dict[str, Any]] = []
    for index in range(count):
        ticker, name, sector = companies[index % len(companies)]
        template = templates[(index // len(companies) + index) % len(templates)]
        question = template["text"].format(name=name)
        digest = hashlib.sha1(f"{seed}|{ticker}|{template['kind']}|{index}".encode()).hexdigest()[:12]
        rows.append({
            "question_id": f"aiei-{digest}", "question": question, "ticker": ticker,
            "company": name, "sector": sector, "kind": template["kind"],
            "difficulty": template["difficulty"], "event_weight": 1.0,
        })
    return rows
