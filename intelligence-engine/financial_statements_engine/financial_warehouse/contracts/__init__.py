"""Versioned Data Contract Layer — sole consumer interface to the warehouse."""

from financial_statements_engine.financial_warehouse.contracts.layer import (
    CONTRACT_REGISTRY,
    fetch_contract,
    list_contracts,
)

__all__ = ["list_contracts", "fetch_contract", "CONTRACT_REGISTRY"]
