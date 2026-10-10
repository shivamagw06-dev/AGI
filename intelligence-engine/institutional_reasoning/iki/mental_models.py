"""Module 4 — Mental Models.

Author philosophies as executable decision policies — not prose.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.iki.applicability import infer_sector

MENTAL_MODELS_VERSION = "mental-models-v1.0.0"


def _num(pack: dict[str, Any], *keys: str) -> float | None:
    for k in keys:
        v = pack.get(k)
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, dict) and v.get("value") is not None:
            try:
                return float(v["value"])
            except Exception:
                pass
    validated = pack.get("validated") if isinstance(pack.get("validated"), dict) else {}
    for k in keys:
        node = validated.get(k)
        if isinstance(node, dict) and node.get("value") is not None:
            try:
                return float(node["value"])
            except Exception:
                pass
    return None


def evaluate_buffett(entity_id: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    """IF ROIC>20 AND stable margins THEN increase quality; ELSE reject speculative growth."""
    sector = infer_sector(entity_id)
    ev = evidence or {}
    roic = _num(ev, "roic")
    margins = _num(ev, "margins", "operating_margin")
    rules_fired: list[str] = []
    quality_delta = 0
    stance = "neutral"

    if sector in {"consumer_internet", "pre_profit_growth"}:
        rules_fired.append("REJECT: speculative / pre-moat consumer internet")
        stance = "rejects"
        return {
            "author": "Buffett",
            "model": "wonderful_business",
            "stance": stance,
            "quality_delta": -20,
            "rules_fired": rules_fired,
            "entity_id": entity_id,
            "mental_models_version": MENTAL_MODELS_VERSION,
        }

    if roic is not None and roic > 20:
        rules_fired.append("IF ROIC > 20% THEN increase quality score")
        quality_delta += 15
    if margins is not None and margins > 15:
        rules_fired.append("IF stable/high margins THEN increase quality score")
        quality_delta += 10
    if quality_delta >= 20:
        stance = "supports"
        rules_fired.append("THEN wonderful-business screen passes")
    elif quality_delta > 0:
        stance = "conditional"
    else:
        stance = "insufficient_evidence"
        rules_fired.append("Missing ROIC/margins for Buffett screen")

    return {
        "author": "Buffett",
        "model": "wonderful_business",
        "stance": stance,
        "quality_delta": quality_delta,
        "rules_fired": rules_fired,
        "roic": roic,
        "margins": margins,
        "entity_id": entity_id,
        "mental_models_version": MENTAL_MODELS_VERSION,
    }


def evaluate_graham(entity_id: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    sector = infer_sector(entity_id)
    ev = evidence or {}
    cur = _num(ev, "current_pe")
    hist = _num(ev, "historical_pe")
    rules: list[str] = []
    if sector in {"consumer_internet", "pre_profit_growth"}:
        return {
            "author": "Graham",
            "model": "margin_of_safety",
            "stance": "rejects",
            "rules_fired": ["REJECT: speculative growth without asset/earnings floor"],
            "entity_id": entity_id,
            "mental_models_version": MENTAL_MODELS_VERSION,
        }
    if cur and hist and cur > 0:
        mos = (hist / cur - 1) * 100
        if mos >= 20:
            rules.append("IF MoS >= 20% THEN support")
            stance = "supports"
        elif mos < 0:
            rules.append("IF price above historical multiple THEN reject / wait")
            stance = "rejects"
        else:
            rules.append("Thin margin of safety — conditional")
            stance = "conditional"
        return {
            "author": "Graham",
            "model": "margin_of_safety",
            "stance": stance,
            "mos_pct": round(mos, 2),
            "rules_fired": rules,
            "entity_id": entity_id,
            "mental_models_version": MENTAL_MODELS_VERSION,
        }
    return {
        "author": "Graham",
        "model": "margin_of_safety",
        "stance": "insufficient_evidence",
        "rules_fired": ["Missing PE history for MoS"],
        "entity_id": entity_id,
        "mental_models_version": MENTAL_MODELS_VERSION,
    }


def evaluate_damodaran(entity_id: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    sector = infer_sector(entity_id)
    ev = evidence or {}
    cur = _num(ev, "current_pe")
    peer = _num(ev, "peer_pe")
    rules: list[str] = []
    if sector in {"bank", "insurance", "nbfc"}:
        return {
            "author": "Damodaran",
            "model": "growth_dcf_relative",
            "stance": "rejects_dcf",
            "rules_fired": [
                "IF financial institution THEN do not use operating DCF as primary",
                "Prefer relative / residual income for banks",
            ],
            "entity_id": entity_id,
            "mental_models_version": MENTAL_MODELS_VERSION,
        }
    stance = "supports"
    if sector == "consumer_internet":
        rules.append("Growth story — relative valuation / growth DCF dominate")
        stance = "supports_growth"
    if cur and peer:
        prem = (cur / peer - 1) * 100
        rules.append(f"Relative PE premium/discount vs peers: {prem:+.1f}%")
    else:
        rules.append("Relative inputs incomplete — confidence reduced")
        stance = "conditional"
    return {
        "author": "Damodaran",
        "model": "growth_dcf_relative",
        "stance": stance,
        "rules_fired": rules,
        "entity_id": entity_id,
        "mental_models_version": MENTAL_MODELS_VERSION,
    }


def evaluate_authors(entity_id: str, evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "entity_id": entity_id,
        "authors": {
            "Buffett": evaluate_buffett(entity_id, evidence),
            "Graham": evaluate_graham(entity_id, evidence),
            "Damodaran": evaluate_damodaran(entity_id, evidence),
        },
        "mental_models_version": MENTAL_MODELS_VERSION,
    }
