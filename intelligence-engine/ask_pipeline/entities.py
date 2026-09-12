"""S03 — Multi-entity resolution (soft wrap over existing resolve_entities)."""

from __future__ import annotations

import re
from typing import Any

from ask_pipeline.schema import ENTITY_TYPES

_TICKER = re.compile(r"\b([A-Z]{2,12})\b")
_KNOWN = {
    "INFY": "Infosys",
    "TCS": "Tata Consultancy Services",
    "RELIANCE": "Reliance Industries",
    "HDFCBANK": "HDFC Bank",
    "WIPRO": "Wipro",
}


def resolve_ask_entities(
    question: str,
    *,
    ticker_hint: str | None = None,
    entity_resolution_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    entities: list[dict[str, Any]] = []
    primary: dict[str, Any] | None = None

    try:
        from institutional_reasoning.evidence_contracts import resolve_entities

        base = resolve_entities(
            question,
            ticker_hint=ticker_hint,
            entity_resolution_pack=entity_resolution_pack,
        )
        primary = base.get("primary") or None
        if primary and primary.get("entity_id"):
            entities.append(
                {
                    "type": "company",
                    "id": primary.get("entity_id"),
                    "name": primary.get("entity_name") or primary.get("entity_id"),
                    "confidence": primary.get("confidence"),
                    "source": "evidence_contracts.resolve_entities",
                }
            )
        for extra in base.get("candidates") or base.get("entities") or []:
            if not isinstance(extra, dict):
                continue
            eid = extra.get("entity_id") or extra.get("id")
            if not eid:
                continue
            if any(e.get("id") == eid for e in entities):
                continue
            entities.append(
                {
                    "type": "company",
                    "id": str(eid).upper(),
                    "name": extra.get("entity_name") or eid,
                    "confidence": extra.get("confidence"),
                    "source": "evidence_contracts.candidates",
                }
            )
    except Exception as exc:
        base = {"error": str(exc)[:160]}

    ql = str(question or "")
    # Soft multi-company from known map / uppercase tokens
    for tok, name in _KNOWN.items():
        if tok in ql.upper() or name.lower() in ql.lower():
            if not any(e.get("id") == tok for e in entities):
                entities.append(
                    {
                        "type": "company",
                        "id": tok,
                        "name": name,
                        "confidence": 0.8,
                        "source": "ask_pipeline.known_map",
                    }
                )

    if ticker_hint and not any(e.get("id") == str(ticker_hint).upper() for e in entities):
        entities.insert(
            0,
            {
                "type": "company",
                "id": str(ticker_hint).upper(),
                "name": str(ticker_hint).upper(),
                "confidence": 0.75,
                "source": "ticker_hint",
            },
        )

    # Soft type tags from language (no fabrication of ids)
    soft_tags = []
    low = ql.lower()
    if any(k in low for k in ("sector", "industry", "value chain")):
        soft_tags.append({"type": "industry", "id": None, "name": None, "soft": True})
    if any(k in low for k in ("rbi", "sebi", "gst", "budget", "pli", "policy")):
        soft_tags.append({"type": "government_policy", "id": None, "name": None, "soft": True})
    if any(k in low for k in ("inflation", "gdp", "macro", "interest rate")):
        soft_tags.append({"type": "macro_variable", "id": None, "name": None, "soft": True})
    if any(k in low for k in ("alternative data", "card spend", "satellite")):
        soft_tags.append({"type": "alternative_dataset", "id": None, "name": None, "soft": True})
    if "portfolio" in low:
        soft_tags.append({"type": "portfolio", "id": "BOOK", "name": "BOOK", "soft": True})
    if "universe" in low or "nifty" in low:
        soft_tags.append({"type": "universe", "id": "NIFTY_500", "name": "NIFTY_500", "soft": True})

    if not primary and entities:
        primary = {
            "entity_id": entities[0].get("id"),
            "entity_name": entities[0].get("name"),
            "entity_type": "company",
            "confidence": entities[0].get("confidence"),
        }

    return {
        "primary": primary,
        "entities": entities,
        "soft_tags": soft_tags,
        "entity_types_supported": list(ENTITY_TYPES),
        "count": len(entities),
        "base": base if isinstance(base, dict) else {},
    }
