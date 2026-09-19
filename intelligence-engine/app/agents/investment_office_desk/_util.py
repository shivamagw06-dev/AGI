"""Shared helpers for Investment Office packaging agents."""

from __future__ import annotations

from typing import Any

from app.schemas.models import EvidenceItem, SourceType


def pack_dict(context: dict[str, Any]) -> dict[str, Any]:
    pack = context.get("investment_office_pack") or context.get("office_pack")
    if pack is None:
        return {}
    if hasattr(pack, "model_dump"):
        return pack.model_dump()
    return dict(pack) if isinstance(pack, dict) else {}


def evidence(claim: str, snippet: str | None = None, reliability: float = 0.75) -> EvidenceItem:
    return EvidenceItem(
        claim=claim,
        source_id="investment_office:pack",
        source_type=SourceType.INVESTMENT_OFFICE,
        snippet=(snippet or claim)[:280],
        reliability=reliability,
    )
