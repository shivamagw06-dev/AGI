"""Phase 2A persistence through the existing generic sector registry."""
from __future__ import annotations
from typing import Any, Callable
from financials_valuation.persistence import persist_sector_certification, seed_sector_model
from technology_valuation.model import IT_SERVICES_MODEL, TECHNOLOGY_PARENT_SECTOR
from technology_valuation.saas_model import SOFTWARE_SAAS_MODEL
from technology_valuation.platform_model import PLATFORM_MODEL
from technology_valuation.consumer_model import CONSUMER_MODEL
from technology_valuation.semiconductor_model import SEMI_MODEL

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
