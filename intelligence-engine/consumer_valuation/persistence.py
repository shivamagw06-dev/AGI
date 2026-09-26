"""Persist Consumer curricula through the existing sector registry."""
from __future__ import annotations
from typing import Any, Callable
from financials_valuation.persistence import persist_sector_certification, seed_sector_model
from consumer_valuation.models import MODELS, PARENT_SECTOR

Transport=Callable[...,Any]


def seed_consumer_models(*, transport: Transport) -> dict[str,Any]:
    rows=[seed_sector_model(model,parent_sector=PARENT_SECTOR,transport=transport) for model in MODELS.values()]
    return {"ok":all(row.get("ok") for row in rows),"models":len(rows),"results":rows,"investment_certified_models":0}


def persist_consumer_certification(result: dict[str,Any], *, transport: Transport) -> dict[str,Any]:
    family=str(result.get("subsector") or "")
    if family not in MODELS: return {"ok":False,"status":"CLASSIFICATION_UNAVAILABLE"}
    return persist_sector_certification(result,model=MODELS[family],transport=transport)
