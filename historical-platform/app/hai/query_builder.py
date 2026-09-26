"""Analogue Query Builder — current knowledge → structured analogue search."""

from __future__ import annotations

import re
from typing import Any

from app.contracts.models import AnalogueQuery, AnalogueScope


_SLOWDOWN = re.compile(r"slowdown|margin compression|deal slowdown|weak demand|air[- ]?pocket", re.I)
_RATE = re.compile(r"rate cut|easing|rbi cycle|monetary easing", re.I)
_VALUATION = re.compile(r"valuation|high pe|expensive|18x|22x", re.I)
_COVID = re.compile(r"covid|pandemic|2020", re.I)


def detect_situation(question: str | None, *, explicit: str | None = None) -> str | None:
    if explicit:
        return explicit
    if not question:
        return None
    if _SLOWDOWN.search(question):
        return "slowdown"
    if _RATE.search(question):
        return "rate_cut"
    if _VALUATION.search(question):
        return "valuation"
    if _COVID.search(question):
        return "covid_shock"
    return None


def build_company_query(
    symbol: str,
    *,
    features: dict[str, float],
    question: str | None = None,
    as_of_period: str | None = None,
    situation: str | None = None,
    top_k: int = 5,
) -> AnalogueQuery:
    sit = detect_situation(question, explicit=situation)
    return AnalogueQuery(
        scope=AnalogueScope.COMPANY,
        entity_key=symbol.upper(),
        question=question,
        as_of_period=as_of_period,
        situation=sit,
        features=features,
        top_k=top_k,
    )


def build_sector_query(
    sector: str,
    *,
    features: dict[str, float] | None = None,
    question: str | None = None,
    situation: str | None = None,
    top_k: int = 5,
) -> AnalogueQuery:
    sit = detect_situation(question, explicit=situation) or "sector_cycle"
    # Default IT weak-demand / strong-USD / margin-pressure profile when unspecified
    feats = features or {
        "demand_stress": 0.8,
        "fx_sensitivity": 0.7,
        "margin_pressure": 0.75,
        "cycle_phase": 0.6,
    }
    return AnalogueQuery(
        scope=AnalogueScope.SECTOR,
        entity_key=sector.lower().replace(" ", "_"),
        question=question,
        situation=sit,
        features=feats,
        top_k=top_k,
    )


def build_macro_query(
    *,
    features: dict[str, float] | None = None,
    question: str | None = None,
    situation: str | None = None,
    top_k: int = 5,
) -> AnalogueQuery:
    sit = detect_situation(question, explicit=situation) or "rate_cut"
    feats = features or {
        "policy_stance": -1.0 if sit == "rate_cut" else 0.0,  # easing
        "inflation_direction": -0.7,  # falling
        "growth_direction": -0.4,  # slowing
    }
    return AnalogueQuery(
        scope=AnalogueScope.MACRO,
        entity_key="india",
        question=question,
        situation=sit,
        features=feats,
        top_k=top_k,
    )


def build_market_query(
    *,
    features: dict[str, float] | None = None,
    question: str | None = None,
    situation: str | None = None,
    top_k: int = 5,
) -> AnalogueQuery:
    sit = detect_situation(question, explicit=situation) or "risk_on"
    feats = features or {
        "valuation_regime": 0.8,  # high PE
        "volatility": 0.2,  # low VIX
        "liquidity": 0.85,
        "risk_appetite": 0.75,
    }
    return AnalogueQuery(
        scope=AnalogueScope.MARKET,
        entity_key="nifty",
        question=question,
        situation=sit,
        features=feats,
        top_k=top_k,
    )


def features_from_financial_row(
    row: dict[str, Any],
    *,
    prev: dict[str, Any] | None = None,
    sector_alignment: float = 1.0,
) -> dict[str, float]:
    rev = _num(row.get("revenue") or (row.get("knowledge") or {}).get("revenue"))
    ni = _num(
        row.get("net_income")
        or (row.get("knowledge") or {}).get("net_income")
        or (row.get("knowledge") or {}).get("pat")
    )
    pe = _num(row.get("pe") or (row.get("knowledge") or {}).get("pe"))
    margins = (row.get("knowledge") or {}).get("margins") or row.get("margins") or {}
    pat_margin = _num(margins.get("pat_margin"))
    if pat_margin is None and rev and ni:
        pat_margin = float(ni) / float(rev)
    growth = None
    if prev is not None:
        prev_rev = _num(prev.get("revenue") or (prev.get("knowledge") or {}).get("revenue"))
        if prev_rev and rev and prev_rev != 0:
            growth = round((float(rev) - float(prev_rev)) / float(prev_rev) * 100.0, 2)
    out: dict[str, float] = {"sector_alignment": sector_alignment}
    if growth is not None:
        out["revenue_growth"] = growth
    if pat_margin is not None:
        out["pat_margin"] = float(pat_margin)
    if pe is not None:
        out["pe"] = float(pe)
    return out


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
