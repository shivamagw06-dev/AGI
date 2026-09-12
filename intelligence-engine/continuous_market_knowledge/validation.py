"""Validate market drafts — universe membership, catalog, no live Ask path."""

from __future__ import annotations

from typing import Any

from continuous_market_knowledge.schema import MARKET_UNIVERSE, RawMarketDraft


def validate_draft(draft: RawMarketDraft) -> dict[str, Any]:
    errors: list[str] = []
    if draft.domain_key not in MARKET_UNIVERSE:
        errors.append("domain_not_in_universe")
    if not draft.catalog:
        errors.append("catalog_required")
    if draft.ask_triggered:
        errors.append("ask_triggered_forbidden")
    if draft.providers_queried:
        errors.append("providers_queried_must_be_empty")
    if not draft.label:
        errors.append("label_required")
    return {"ok": not errors, "errors": errors, "domain_key": draft.domain_key}
