"""Soft consumption helpers — existing engines import these without redesign.

These functions are pure library adapters. Engine packages remain unchanged;
composition roots or future soft-wiring can call these helpers.
"""

from __future__ import annotations

from typing import Any

from models.registry import get_registry


def for_eve(payload: dict[str, Any]) -> dict[str, Any]:
    """EVE: accounting validation notes/red flags."""
    reg = get_registry()
    return {
        "consumer": "EVE",
        "accounting": reg.analyse("accounting", payload),
        "usage": "Attach accounting red flags / earnings quality to evidence review",
    }


def for_iie(payload: dict[str, Any]) -> dict[str, Any]:
    """IIE: thesis inputs from business/competition/capital/governance/industry."""
    reg = get_registry()
    return {
        "consumer": "IIE",
        "business": reg.analyse("business", payload),
        "competition": reg.analyse("competition", payload),
        "capital_allocation": reg.analyse("capital_allocation", payload),
        "governance": reg.analyse("governance", payload),
        "industry": reg.analyse("industry", payload),
    }


def for_fle(payload: dict[str, Any]) -> dict[str, Any]:
    """FLE: forecast assumption quality + industry/econ context."""
    reg = get_registry()
    return {
        "consumer": "FLE",
        "forecasting": reg.analyse("forecasting", payload),
        "economics": reg.analyse("economics", payload),
        "industry": reg.analyse("industry", payload),
    }


def for_mee(payload: dict[str, Any]) -> dict[str, Any]:
    """MEE: interpret events via macro/risk/economics."""
    reg = get_registry()
    return {
        "consumer": "MEE",
        "macro": reg.analyse("macro", payload),
        "risk": reg.analyse("risk", payload),
        "economics": reg.relationships("economics", payload),
    }


def for_ve(payload: dict[str, Any]) -> dict[str, Any]:
    """VE: methodology guidance + accounting quality (does not value)."""
    reg = get_registry()
    return {
        "consumer": "VE",
        "valuation_guidance": reg.analyse("valuation", payload),
        "accounting": reg.score("accounting", payload),
        "note": "FIML advises methodology; VE performs valuation",
    }


def for_cae(payload: dict[str, Any]) -> dict[str, Any]:
    """CAE: compact decision/industry/risk context slices."""
    reg = get_registry()
    return {
        "consumer": "CAE",
        "decision": reg.score("decision", payload),
        "industry": reg.analyse("industry", payload),
        "risk": reg.score("risk", payload),
    }


def for_irp(payload: dict[str, Any]) -> dict[str, Any]:
    """IRP: full decision profile for institutional reasoning."""
    reg = get_registry()
    return {
        "consumer": "IRP",
        "decision": reg.analyse("decision", payload),
        "explain": reg.explain("decision", payload),
    }


def for_ask_agi(payload: dict[str, Any]) -> dict[str, Any]:
    """Ask AGI: professional explanation bundle without engine redesign."""
    reg = get_registry()
    bundle = reg.analyse_bundle(payload)
    decision = (bundle.get("decision") or {}).get("outputs", {}).get("decision") or {}
    return {
        "consumer": "Ask AGI",
        "answer_policy": "institutional_domain_models",
        "narrative_hint": (bundle.get("decision") or {}).get("summary"),
        "decision": decision,
        "bundle_scores": {
            k: (v or {}).get("score")
            for k, v in (bundle.get("results") or {}).items()
            if isinstance(v, dict) and "score" in v
        },
        "bundle": bundle,
    }
