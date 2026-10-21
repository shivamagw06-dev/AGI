"""Institutional Intelligence Stack — soft FIL→FDI→MII→EIL→PIL integration."""

from institutional_stack.production import (
    analyse,
    bootstrap_stack,
    company,
    dashboard,
    health,
    ingest,
    quality_gates,
    soft_slice_for_analyst,
    soft_slice_for_ask_agi,
    soft_slice_for_company_analysis,
    soft_slice_for_irs,
    soft_slice_for_mission_control,
)
from institutional_stack.schema import PIPELINE, PROGRAMME, STACK_VERSION

__all__ = [
    "PIPELINE",
    "PROGRAMME",
    "STACK_VERSION",
    "analyse",
    "bootstrap_stack",
    "company",
    "dashboard",
    "health",
    "ingest",
    "quality_gates",
    "soft_slice_for_analyst",
    "soft_slice_for_ask_agi",
    "soft_slice_for_company_analysis",
    "soft_slice_for_irs",
    "soft_slice_for_mission_control",
]
