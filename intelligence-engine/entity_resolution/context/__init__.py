"""Conversation context resolution — prior entity disambiguates follow-ups."""

from __future__ import annotations

from typing import Any

from entity_resolution.entity_registry import get_entity


def apply_context(
    candidates: list[dict[str, Any]],
    *,
    prior_entity_id: str | None = None,
    prior_sector: str | None = None,
) -> list[dict[str, Any]]:
    """Boost candidates aligned with prior conversation entity/sector."""
    if not candidates:
        return candidates
    prior = get_entity(prior_entity_id) if prior_entity_id else None
    out: list[dict[str, Any]] = []
    for c in candidates:
        ent = c.get("entity") or {}
        boost = 0.0
        if prior:
            # Same sector / peer family preferred (ICICI after HDFC Bank → Bank not Lombard)
            if prior.get("sector") and ent.get("sector") == prior.get("sector"):
                boost += 0.12
            if prior.get("industry") and ent.get("industry") == prior.get("industry"):
                boost += 0.08
            if ent.get("id") in (prior.get("peers") or []):
                boost += 0.05
        if prior_sector and ent.get("sector") == prior_sector:
            boost += 0.06
        nc = dict(c)
        nc["confidence"] = round(min(0.999, float(c.get("confidence") or 0) + boost), 4)
        nc["context_boost"] = boost
        out.append(nc)
    out.sort(key=lambda x: (-float(x.get("confidence") or 0), str((x.get("entity") or {}).get("id"))))
    return out


def prior_from_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    body = payload or {}
    return {
        "prior_entity_id": body.get("prior_entity_id") or body.get("context_entity_id"),
        "prior_sector": body.get("prior_sector"),
        "conversation": body.get("conversation") or body.get("history") or [],
    }
