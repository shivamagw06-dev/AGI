"""Entity Intelligence production facade."""

from __future__ import annotations

from typing import Any, Optional

from entity_intelligence.resolve import assert_no_forbidden_bind, resolve
from entity_intelligence.schema import (
    CONTRACT_STATES,
    EI_VERSION,
    PROGRAMME,
    SPEC,
    STATE_CLARIFICATION_REQUIRED,
    STATE_UNSUPPORTED_ENTITY,
    STATE_VERIFIED_ENTITY,
)


def health() -> dict[str, Any]:
    return {
        "ok": True,
        "module": "entity_intelligence",
        "programme": PROGRAMME,
        "version": EI_VERSION,
        "spec": SPEC,
        "contract_states": list(CONTRACT_STATES),
        "law": "Never answer for the wrong entity. Never substitute.",
    }


def analyse(question: str) -> dict[str, Any]:
    return resolve(question)


def soft_slice_for_ask_agi(question: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Ask soft-slice — contract decision for the gateway."""
    contract = resolve(question)
    return {
        "found": True,
        "entity_intelligence": contract,
        "version": EI_VERSION,
        "allow_planner": bool(contract.get("allow_planner")),
        "state": contract.get("state"),
        "ticker": contract.get("ticker"),
        "summary": contract.get("summary"),
    }


def gate_allows_kul(contract: dict[str, Any]) -> bool:
    return bool(contract.get("allow_planner")) and contract.get("state") in {
        STATE_VERIFIED_ENTITY,
        "verified_concept",
        "verified_industry",
        "verified_macro",
    }


def should_short_circuit(contract: dict[str, Any]) -> bool:
    if not contract:
        return False
    # Pedagogy-only unsupported globals (Costco moat, Visa vs Mastercard) may
    # allow the planner with no CapIQ ticker — never short-circuit those.
    if contract.get("allow_planner"):
        return False
    if contract.get("state") in {STATE_CLARIFICATION_REQUIRED, STATE_UNSUPPORTED_ENTITY}:
        return True
    # Verified private / insufficient coverage with planner blocked
    if contract.get("state") == STATE_VERIFIED_ENTITY and not contract.get("allow_planner"):
        return True
    return False


def validate_bound_ticker(contract: dict[str, Any], ticker: Optional[str]) -> bool:
    return assert_no_forbidden_bind(contract, ticker)


__all__ = [
    "analyse",
    "gate_allows_kul",
    "health",
    "should_short_circuit",
    "soft_slice_for_ask_agi",
    "validate_bound_ticker",
]
