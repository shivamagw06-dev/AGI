"""Phase 2 capability milestones and implementation PR checklist."""

from __future__ import annotations

from typing import Any

# Capability-delivery milestones (preferred over generic "Phase 2")
MILESTONES: tuple[dict[str, Any], ...] = (
    {
        "id": "phase_2_1",
        "name": "Phase 2.1: Market & Ownership Intelligence",
        "workstreams": ["P2.6", "P2.3"],
        "sprints": [
            {
                "id": "sprint_1",
                "workstream": "P2.6",
                "title": "Live Market Context",
                "goal": "Make every recommendation market-aware.",
                "deliverables": [
                    "live_quote_provider_abstraction",
                    "price_freshness",
                    "liquidity",
                    "relative_strength",
                    "distance_to_intrinsic_value",
                    "market_context_api",
                ],
                "expected_lift": [
                    "better_valuation_freshness",
                    "lower_stale_price_failures",
                    "no_governance_changes",
                ],
            },
            {
                "id": "sprint_2",
                "workstream": "P2.3",
                "title": "Ownership Intelligence",
                "goal": (
                    "Eliminate recommendation deferrals caused by missing ownership "
                    "evidence where reliable data is available."
                ),
                "deliverables": [
                    "shareholding_ingestion",
                    "fii_dii_history",
                    "promoter_history",
                    "insider_activity",
                    "ownership_confidence",
                    "ownership_freshness",
                ],
                "expected_lift": [
                    "higher_institutional_readiness",
                    "higher_evidence_coverage",
                    "fewer_watchlist_outcomes_from_missing_ownership",
                ],
            },
        ],
        "exit_gate": ["evaluation_lab_full_run", "institutional_acceptance_test"],
        "status": "in_progress",
    },
    {
        "id": "phase_2_2",
        "name": "Phase 2.2: Earnings & Valuation Intelligence",
        "workstreams": ["P2.1", "P2.2"],
        "sprints": [
            {
                "id": "sprint_3",
                "workstream": "P2.1",
                "title": "Earnings Intelligence",
                "goal": "Add forward-looking earnings analysis to the investment thesis.",
            },
            {
                "id": "sprint_4",
                "workstream": "P2.2",
                "title": "Valuation Intelligence",
                "goal": "Deepen intrinsic value with sector-appropriate models.",
            },
        ],
        "exit_gate": ["evaluation_lab_full_run", "institutional_acceptance_test"],
        "status": "planned",
    },
    {
        "id": "phase_2_3",
        "name": "Phase 2.3: Sector & Catalyst Intelligence",
        "workstreams": ["P2.5", "P2.4"],
        "sprints": [
            {
                "id": "sprint_5",
                "workstream": "P2.5",
                "title": "Sector Playbooks",
                "goal": "Make analysis sector-specific and consistent.",
            },
            {
                "id": "sprint_6",
                "workstream": "P2.4",
                "title": "Catalyst Intelligence",
                "goal": "Explain what could change the thesis.",
            },
        ],
        "exit_gate": ["evaluation_lab_full_run", "institutional_acceptance_test"],
        "status": "planned",
    },
)

# Every implementation PR must answer these before merge.
IMPLEMENTATION_PR_CHECKLIST = (
    "What intelligence did we add?",
    "What measurable metric improved?",
    "What metric stayed unchanged?",
    "Did IAT still pass?",
    "Did UNKNOWN drift remain zero?",
)


def milestones_board() -> dict[str, Any]:
    return {
        "milestones": list(MILESTONES),
        "n": len(MILESTONES),
        "active": "phase_2_1",
        "implementation_pr_checklist": list(IMPLEMENTATION_PR_CHECKLIST),
        "rule": (
            "If the five checklist answers are not clear, the implementation is not ready to merge."
        ),
        "note": (
            "Architectural design is complete. Highest-value work is implementing each "
            "intelligence engine, measuring impact, and proving improvement vs Baseline v1.0."
        ),
    }
