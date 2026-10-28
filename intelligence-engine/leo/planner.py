"""Intent-aware Evidence Planner — decides what evidence is required."""

from __future__ import annotations

import re
from typing import Any

from leo.schema import INTENT_REQUIREMENTS


_BUY_SELL = re.compile(
    r"\b(buy|sell|hold|accumulate|reduce|overweight|underweight|invest|should i)\b",
    re.I,
)
_VALUATION = re.compile(r"\b(valuat|fair value|intrinsic|dcf|target price|worth|p/?e|p/?b)\b", re.I)
_MACRO = re.compile(r"\b(repo|inflation|gdp|rbi|fed|yield|liquidity|money supply|fiscal)\b", re.I)
_NEWS = re.compile(r"\b(news|announcement|filing|what happened|latest update)\b", re.I)
_SECTOR = re.compile(r"\b(sector|industry|banks?|it services|pharma|cement|steel|utilities)\b", re.I)


def detect_intent(query: str) -> dict[str, Any]:
    q = (query or "").strip()
    ql = q.lower()
    if _BUY_SELL.search(ql) or "recommend" in ql:
        intent = "investment_recommendation"
    elif _VALUATION.search(ql):
        intent = "valuation"
    elif _MACRO.search(ql) and not _BUY_SELL.search(ql):
        intent = "macro"
    elif _NEWS.search(ql):
        intent = "news"
    elif _SECTOR.search(ql) and not any(x in ql for x in ("hdfc", "infosys", "reliance", "buy")):
        intent = "sector"
    else:
        intent = "general_finance"
    return {
        "intent": intent,
        "is_finance": intent != "news" or True,
        "is_investment": intent == "investment_recommendation",
        "query": q,
    }


def detect_entity(query: str, ticker: str | None = None) -> dict[str, Any]:
    """Soft entity detection — prefer SIF, fall back to ticker/alias heuristics."""
    resolved = (ticker or "").upper() or None
    name = None
    sector_id = None
    try:
        from sif.detection import detect_sector

        det = detect_sector(query, ticker)
        resolved = det.get("ticker") or resolved
        sector_id = det.get("sector_id")
        name = det.get("company_name") or det.get("name")
    except Exception:
        pass

    if not resolved:
        # common aliases
        aliases = {
            "hdfc bank": "HDFCBANK",
            "idbi": "IDBI",
            "idbi bank": "IDBI",
            "idbi bank limited": "IDBI",
            "hdfc": "HDFCBANK",
            "infosys": "INFY",
            "reliance": "RELIANCE",
            "ultratech": "ULTRACEMCO",
            "power grid": "POWERGRID",
            "sun pharma": "SUNPHARMA",
            "tata steel": "TATASTEEL",
        }
        ql = (query or "").lower()
        for k, v in aliases.items():
            if k in ql:
                resolved = v
                break

    return {
        "ticker": resolved,
        "company": name or resolved,
        "sector_id": sector_id,
    }


def build_evidence_plan(query: str, *, ticker: str | None = None) -> dict[str, Any]:
    intent = detect_intent(query)
    entity = detect_entity(query, ticker)
    required = list(INTENT_REQUIREMENTS.get(intent["intent"], INTENT_REQUIREMENTS["general_finance"]))
    optional = ["earnings_transcript", "broker_consensus", "esg_report", "credit_rating"]
    if intent["intent"] == "macro":
        optional = ["news"]
    return {
        "query": (query or "").strip(),
        "intent": intent["intent"],
        "intent_meta": intent,
        "entity": entity,
        "company": entity.get("company"),
        "ticker": entity.get("ticker"),
        "sector_id": entity.get("sector_id"),
        "required_evidence": required,
        "optional_evidence": optional,
        "missing_evidence": list(required),  # filled after fetch
        "plan_version": "leo-plan-v1",
    }
