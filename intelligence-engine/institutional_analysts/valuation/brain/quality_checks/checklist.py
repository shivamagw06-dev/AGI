"""Valuation quality checklist."""

from __future__ import annotations

from typing import Any

CHECKS = (
    ("financial_statements_available", "Financial statements available"),
    ("market_value_available", "Market value available"),
    ("peer_comparison_completed", "Peer comparison completed"),
    ("historical_valuation_available", "Historical valuation available"),
    ("market_expectations_inferred", "Market expectations inferred"),
    ("margin_of_safety_discussed", "Margin of safety discussed"),
    ("risks_explained", "Risks explained"),
)


def run_checklist(evidence: dict[str, Any], frameworks: dict[str, Any]) -> dict[str, Any]:
    has_market = evidence.get("pe") is not None or evidence.get("forward_pe") is not None or evidence.get("pb") is not None
    has_finance = bool(evidence.get("narrative") or evidence.get("expected_return") is not None or has_market)
    checks = {
        "financial_statements_available": has_finance,
        "market_value_available": bool(has_market or evidence.get("margin_of_safety")),
        "peer_comparison_completed": bool((frameworks.get("peer_comparison") or {}).get("completed")),
        "historical_valuation_available": bool((frameworks.get("historical_valuation") or {}).get("completed")),
        "market_expectations_inferred": bool((frameworks.get("market_expectations") or {}).get("completed")),
        "margin_of_safety_discussed": bool((frameworks.get("margin_of_safety") or {}).get("completed")),
        "risks_explained": bool((frameworks.get("scenario_valuation") or {}).get("completed")),
    }
    failed = [label for key, label in CHECKS if not checks.get(key)]
    # Soft pass when core valuation file present
    if has_market and checks["market_expectations_inferred"] and checks["margin_of_safety_discussed"]:
        if len(failed) <= 2:
            failed = []
    incomplete = len(failed) > 0
    return {
        "passed": not incomplete,
        "incomplete": incomplete,
        "status": "Incomplete Valuation Assessment" if incomplete else "Complete",
        "checks": checks,
        "failed_items": failed,
        "issues": (["Incomplete Valuation Assessment", *[f"Failed check: {x}" for x in failed]] if incomplete else []),
        "explanation": ("Incomplete Valuation Assessment — missing: " + "; ".join(failed) + ".") if incomplete else None,
        "ready_for_committee": not incomplete,
    }
