"""IUI production facade — soft surface for routes / Mission Control."""

from __future__ import annotations

from typing import Any

from universe_intelligence.dashboard import company_ici_card, universe_health
from universe_intelligence.membership import memberships_for_company, members_as_of, was_member
from universe_intelligence.pipeline import run_universe_intelligence_pipeline
from universe_intelligence.registry import get_universe, list_universes, universe_tree
from universe_intelligence.schema import FREEZE_LOCKS, IUI_VERSION, LAYER, PROGRAMME
from universe_intelligence.company_registry import get_company
from universe_intelligence.quality_gates import institutional_quality_gates
from universe_intelligence.coverage_levels import coverage_level_for
from universe_intelligence.ici import institutional_coverage_index


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "layer": LAYER,
        "version": IUI_VERSION,
        "architecture_status": "SOFT_UNIVERSE_REGISTRY",
        "not_a_reasoning_engine": True,
        "not_a_planner": True,
        "not_governance": True,
        "not_learning_system": True,
        "freeze_locks": FREEZE_LOCKS,
        "api_prefix": "/v1/universe-intelligence",
        "stack": [
            "Universe Registry",
            "Universe Membership Engine",
            "Company Registry",
            "Knowledge Factory (frozen)",
            "Evidence Factory",
            "Existing Institutional Reasoning (frozen)",
        ],
    }


def dashboard(**kwargs: Any) -> dict[str, Any]:
    return universe_health(**kwargs)


def run_pipeline(**kwargs: Any) -> dict[str, Any]:
    return run_universe_intelligence_pipeline(**kwargs)


def quality_gates_summary(universe_id: str = "NIFTY_500") -> dict[str, Any]:
    from universe_intelligence.registry import current_members

    members = current_members(universe_id)
    rows = [institutional_quality_gates(t) for t in members]
    ready = sum(1 for r in rows if r["institutional_ready"])
    return {
        "universe_id": universe_id.upper(),
        "n": len(members),
        "institutional_ready": ready,
        "institutional_ready_pct": round(100.0 * ready / (len(members) or 1), 2),
        "gate": "INSTITUTIONAL_UNIVERSE_INTELLIGENCE",
        "passed": ready == len(members) and len(members) > 0,
        "fabricated": False,
        "version": IUI_VERSION,
    }


__all__ = [
    "health",
    "dashboard",
    "run_pipeline",
    "quality_gates_summary",
    "get_universe",
    "list_universes",
    "universe_tree",
    "was_member",
    "members_as_of",
    "memberships_for_company",
    "get_company",
    "coverage_level_for",
    "institutional_coverage_index",
    "institutional_quality_gates",
    "company_ici_card",
]
