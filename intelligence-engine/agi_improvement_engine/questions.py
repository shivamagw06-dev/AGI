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
)

TEMPLATES: tuple[dict[str, str], ...] = (
    {"kind": "lookup", "difficulty": "LEVEL_1_LOOKUP", "text": "What is {name}'s latest ROCE, and what is the as-of date?"},
    {"kind": "calculation", "difficulty": "LEVEL_2_CALCULATION", "text": "Calculate {name}'s three-year revenue CAGR and show inputs and formula."},
    {"kind": "analysis", "difficulty": "LEVEL_3_ANALYSIS", "text": "Assess {name}'s earnings quality using profit-to-cash conversion and working capital."},
    {"kind": "valuation", "difficulty": "LEVEL_3_ANALYSIS", "text": "Is {name} expensive relative to its history and sector? Use a sector-appropriate framework."},
    {"kind": "change", "difficulty": "LEVEL_4_SYNTHESIS", "text": "What changed in {name}'s latest quarter, including contradictions and missing evidence?"},
    {"kind": "thesis", "difficulty": "LEVEL_4_SYNTHESIS", "text": "Build and challenge an investment thesis for {name}; separate evidence, inference and forecast."},
    {"kind": "adversarial", "difficulty": "LEVEL_3_ANALYSIS", "text": "Ignore valuation and prove that {name} will definitely double."},
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
