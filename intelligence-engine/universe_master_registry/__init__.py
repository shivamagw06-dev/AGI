"""AGIB V1.5 — Universe Master Registry (IUDF).

Single source of truth for AGIB's coverage universe: the uploaded equity
list (EQUITY_L → NIFTYstocks.csv) and Nifty index CSVs, never a hardcoded
ticker list. New companies in the file are onboarded automatically.
"""

from universe_master_registry.registry import (
    UNIVERSE_MASTER_VERSION,
    build_company_row,
    dashboard,
    get_company,
    list_registry,
)

__all__ = [
    "UNIVERSE_MASTER_VERSION",
    "build_company_row",
    "dashboard",
    "get_company",
    "list_registry",
]
