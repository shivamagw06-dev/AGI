"""Phase 2A persistence through the existing generic sector registry."""
from __future__ import annotations
from typing import Any, Callable
from financials_valuation.persistence import persist_sector_certification, seed_sector_model
from technology_valuation.model import IT_SERVICES_MODEL, TECHNOLOGY_PARENT_SECTOR
from technology_valuation.saas_model import SOFTWARE_SAAS_MODEL
from technology_valuation.platform_model import PLATFORM_MODEL
from technology_valuation.consumer_model import CONSUMER_MODEL
from technology_valuation.semiconductor_model import SEMI_MODEL
from technology_valuation.telecom_model import TELECOM_MODEL
from technology_valuation.tower_model import TOWER_MODEL
from technology_valuation.specialized_model import SPECIALIZED_MODELS

Transport=Callable[...,Any]


def seed_it_services_model(*, transport: Transport) -> dict[str,Any]:
    return seed_sector_model(IT_SERVICES_MODEL,parent_sector=TECHNOLOGY_PARENT_SECTOR,transport=transport)


def persist_it_services_certification(result: dict[str,Any], *, transport: Transport) -> dict[str,Any]:
    return persist_sector_certification(result,model=IT_SERVICES_MODEL,transport=transport)


def seed_software_saas_model(*,transport:Transport)->dict[str,Any]:
    return seed_sector_model(SOFTWARE_SAAS_MODEL,parent_sector=TECHNOLOGY_PARENT_SECTOR,transport=transport)


def persist_software_saas_certification(result:dict[str,Any],*,transport:Transport)->dict[str,Any]:
    return persist_sector_certification(result,model=SOFTWARE_SAAS_MODEL,transport=transport)

def seed_platform_model(*,transport:Transport)->dict[str,Any]:
    return seed_sector_model(PLATFORM_MODEL,parent_sector=TECHNOLOGY_PARENT_SECTOR,transport=transport)

def persist_platform_certification(result:dict[str,Any],*,transport:Transport)->dict[str,Any]:
    return persist_sector_certification(result,model=PLATFORM_MODEL,transport=transport)

def seed_consumer_model(*,transport:Transport)->dict[str,Any]:
    return seed_sector_model(CONSUMER_MODEL,parent_sector=TECHNOLOGY_PARENT_SECTOR,transport=transport)

def persist_consumer_certification(result:dict[str,Any],*,transport:Transport)->dict[str,Any]:
    return persist_sector_certification(result,model=CONSUMER_MODEL,transport=transport)

def seed_semiconductor_model(*,transport:Transport)->dict[str,Any]:
    return seed_sector_model(SEMI_MODEL,parent_sector=TECHNOLOGY_PARENT_SECTOR,transport=transport)

def persist_semiconductor_certification(result:dict[str,Any],*,transport:Transport)->dict[str,Any]:
    return persist_sector_certification(result,model=SEMI_MODEL,transport=transport)

def seed_telecom_model(*,transport:Transport)->dict[str,Any]:
    return seed_sector_model(TELECOM_MODEL,parent_sector=TECHNOLOGY_PARENT_SECTOR,transport=transport)

def persist_telecom_certification(result:dict[str,Any],*,transport:Transport)->dict[str,Any]:
    return persist_sector_certification(result,model=TELECOM_MODEL,transport=transport)

def seed_tower_model(*,transport:Transport)->dict[str,Any]:
    return seed_sector_model(TOWER_MODEL,parent_sector=TECHNOLOGY_PARENT_SECTOR,transport=transport)

def persist_tower_certification(result:dict[str,Any],*,transport:Transport)->dict[str,Any]:
    return persist_sector_certification(result,model=TOWER_MODEL,transport=transport)

def seed_specialized_models(*,transport:Transport)->dict[str,Any]:
    rows=[seed_sector_model(model,parent_sector=TECHNOLOGY_PARENT_SECTOR,transport=transport) for model in SPECIALIZED_MODELS.values()]
    return {"ok":all(row.get("ok") for row in rows),"models":len(rows),"results":rows,"certified_models":0,"execution_eligible_models":0}

def persist_specialized_certification(result:dict[str,Any],*,transport:Transport)->dict[str,Any]:
    model=SPECIALIZED_MODELS[result["subsector"]]
    return persist_sector_certification(result,model=model,transport=transport)
