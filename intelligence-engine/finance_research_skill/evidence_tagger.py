"""Deterministic financial evidence tags inspired by task-specific FinNLP.

No model, network, filesystem, telemetry, or external code is used. The tagger
operates only on minimized excerpts already admitted to Ask AGI's evidence pack.
"""

from __future__ import annotations

import re
from typing import Any

VERSION = "agi-financial-evidence-tagger-v1.0.0"

_DIMENSIONS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("revenue", ("revenue", "sales", "order book", "bookings", "demand")),
    ("profitability", ("margin", "profit", "ebitda", "earnings", "eps", "cost")),
    ("cash_flow", ("cash flow", "free cash", "working capital", "cash conversion")),
    ("balance_sheet", ("debt", "leverage", "liquidity", "capital adequacy", "npa")),
    ("valuation", ("valuation", "multiple", "p/e", "price to book", "discount", "premium")),
    ("capital_allocation", ("capex", "buyback", "dividend", "acquisition", "investment")),
    ("guidance", ("guidance", "outlook", "expects", "forecast", "target")),
    ("regulation", ("regulation", "policy", "tariff", "subsidy", "approval")),
    ("market_position", ("market share", "competition", "pricing power", "leadership")),
)

_POSITIVE = (
    "beat", "above expectations", "raised", "upgrade", "accelerat", "improv",
    "expand", "growth", "strong", "record", "benefit", "tailwind", "gain",
)
_NEGATIVE = (
    "miss", "below expectations", "cut guidance", "downgrade", "slowdown",
    "declin", "contract", "weak", "pressure", "headwind", "loss", "risk",
)
_HIGH_MAGNITUDE = ("material", "sharp", "significant", "substantial", "surge", "collapse")
_LOW_MAGNITUDE = ("slight", "modest", "marginal", "limited", "broadly stable")
_RISK = ("risk", "uncertain", "litigation", "default", "downgrade", "delay", "shortage")
_CATALYST = (
    "earnings", "results", "approval", "launch", "order win", "contract",
    "investor day", "buyback", "dividend", "policy", "rate cut", "merger",
)


def _hits(text: str, terms: tuple[str, ...]) -> list[str]:
    lower = text.lower()
    return [term for term in terms if term in lower]


def _direction(text: str) -> tuple[str, float]:
    positive = len(_hits(text, _POSITIVE))
    negative = len(_hits(text, _NEGATIVE))
    total = positive + negative
    if total == 0 or positive == negative:
        return "neutral", 0.5
    direction = "positive" if positive > negative else "negative"
    confidence = min(0.9, 0.55 + 0.08 * abs(positive - negative))
    return direction, round(confidence, 2)


def _horizon(text: str) -> str:
    lower = text.lower()
    if re.search(r"\b(intraday|today|this week|near[- ]term|next week)\b", lower):
        return "near_term"
    if re.search(r"\b(next quarter|coming quarter|1[-– ]?2 quarters?|fy\d{2})\b", lower):
        return "1_2_quarters"
    if re.search(r"\b(long[- ]term|multi[- ]year|structural|over the next years?)\b", lower):
        return "long_term"
    return "unspecified"


def _magnitude(text: str) -> str:
    if _hits(text, _HIGH_MAGNITUDE):
        return "high"
    if _hits(text, _LOW_MAGNITUDE):
        return "low"
    return "moderate" if _hits(text, _POSITIVE + _NEGATIVE) else "unknown"


def _relationships(text: str, entity: str | None) -> list[dict[str, str]]:
    subject = entity or "referenced_entity"
    relationships: list[dict[str, str]] = []
    patterns = (
        (r"\bbenefit(?:s|ed|ing)?\s+(?:from\s+)?([^.;]{3,80})", "benefits_from"),
        (r"\b(?:pressure|weigh)\w*\s+(?:on\s+)?([^.;]{3,80})", "pressures"),
        (r"\bdriv(?:e|es|en|ing)\s+([^.;]{3,80})", "drives"),
    )
    for pattern, relation in patterns:
        match = re.search(pattern, text, re.I)
        if match:
            relationships.append(
                {"subject": subject, "relation": relation, "object": match.group(1).strip()[:80]}
            )
    return relationships[:3]


def tag_evidence(
    *, evidence_id: str, text: str, entity: str | None = None, source: str | None = None
) -> dict[str, Any]:
    """Classify one approved excerpt without generating investment advice."""
    excerpt = str(text or "")[:2000]
    dimensions = [name for name, terms in _DIMENSIONS if _hits(excerpt, terms)]
    direction, confidence = _direction(excerpt)
    risks = _hits(excerpt, _RISK)
    catalysts = _hits(excerpt, _CATALYST)
    return {
        "evidence_id": str(evidence_id or "")[:160],
        "entity": str(entity).upper() if entity else None,
        "source": str(source or "")[:160] or None,
        "dimensions": dimensions,
        "direction": direction,
        "magnitude": _magnitude(excerpt),
        "horizon": _horizon(excerpt),
        "confidence": confidence,
        "guidance_direction": direction if "guidance" in dimensions else None,
        "risk_cues": risks,
        "catalyst_cues": catalysts,
        "relationships": _relationships(excerpt, entity),
        "model_version": VERSION,
        "method": "deterministic_financial_taxonomy",
        "recommendation_generated": False,
    }


def tag_documents(documents: list[dict[str, Any]], *, entity: str | None = None) -> list[dict[str, Any]]:
    tags: list[dict[str, Any]] = []
    for index, document in enumerate(documents[:20]):
        if not isinstance(document, dict):
            continue
        text = " ".join(
            str(document.get(key) or "") for key in ("title", "snippet", "summary")
        ).strip()
        if not text:
            continue
        tags.append(
            tag_evidence(
                evidence_id=str(document.get("document_id") or document.get("evidence_id") or f"evidence-{index}"),
                text=text,
                entity=entity,
                source=str(document.get("document_type") or document.get("source") or "research"),
            )
        )
    return tags
