"""Active governance specification registry — versioned like an API."""

from __future__ import annotations

from typing import Any

from governance_spec.schema import ACTIVE_SPEC, FROZEN, GOVERNANCE_SPEC_VERSION, PROGRAMME


def load_spec(version: str | None = None) -> dict[str, Any]:
    ver = (version or ACTIVE_SPEC or GOVERNANCE_SPEC_VERSION).strip().lstrip("v")
    if ver in {"1.0", "1", "1.0.0"}:
        from governance_spec.v1_0.rules import RULES, RULES_BY_ID, evaluate_rule, spec_board

        board = spec_board()
        return {
            "programme": PROGRAMME,
            "spec_version": GOVERNANCE_SPEC_VERSION,
            "frozen": FROZEN,
            "rules": board["rules"],
            "rules_by_id": RULES_BY_ID,
            "evaluate_rule": evaluate_rule,
            "n_rules": len(RULES),
            "board": board,
        }
    raise ValueError(f"unknown_governance_spec:{version}")


def list_specs() -> list[dict[str, Any]]:
    return [
        {
            "spec_version": "v1.0",
            "frozen": True,
            "active": ACTIVE_SPEC == "v1.0",
            "n_rules": 8,
            "status": "active_frozen",
        }
    ]
