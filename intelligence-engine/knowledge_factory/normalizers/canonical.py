"""Normalizers — company / sector / macro canonical shapes."""

from __future__ import annotations

from typing import Any

from knowledge_factory.fixtures.seed import sector_map


def normalize_company(dataset: dict[str, Any]) -> dict[str, Any]:
    e = str(dataset.get("entity") or "").upper()
    payload = dict(dataset.get("payload") or {})
    return {
        "entity": e,
        "sector": sector_map().get(e, "unknown"),
        "primitives": payload.get("primitives") or {},
        "prices": payload.get("prices") or [],
        "market_cap": payload.get("market_cap"),
        "shares_outstanding": payload.get("shares_outstanding"),
        "source": dataset.get("source"),
        "timestamp": dataset.get("timestamp"),
    }


def normalize_sector(companies: list[dict[str, Any]], sector: str) -> dict[str, Any]:
    members = [c for c in companies if c.get("sector") == sector]
    return {"sector": sector, "members": [c.get("entity") for c in members], "n": len(members)}


def normalize_macro(parts: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    sources = []
    for p in parts:
        payload = p.get("payload") or {}
        merged.update({k: v for k, v in payload.items() if v is not None})
        sources.append(p.get("source"))
    return {"series": merged, "sources": sources}
