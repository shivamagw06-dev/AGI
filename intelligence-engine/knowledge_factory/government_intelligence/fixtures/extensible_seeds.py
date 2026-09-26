"""Phase 2+ extensible policy seeds — NOT required for Sprint 3 Phase 1 exit.

Architecture supports these domains without redesign. Not loaded into the
Phase 1 institutional pack by default (`include_extensible=False`).
"""

from __future__ import annotations

from typing import Any

# Placeholder rows documenting the extension contract. Populate in later sprints.
EXTENSIBLE_POLICY_SEEDS: list[dict[str, Any]] = []

EXTENSIBLE_DOMAIN_NOTES: dict[str, str] = {
    "mca": "Companies Act / corporate filings — extend after Phase 1 validation",
    "industry": "IRDAI, TRAI, power, mining, defence, railways, healthcare — per-regulator packs",
    "state": "State industrial policies, corridors, parks, incentives — multi-state framework",
}


def extensible_policy_seeds() -> list[dict[str, Any]]:
    return list(EXTENSIBLE_POLICY_SEEDS)
