"""Module 9 — Versioned Learning.

Nothing overwritten. Every accepted change becomes a new version.
"""

from __future__ import annotations

import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from institutional_reasoning.cal.schema import BASE_PLANNER_WEIGHTS, BASE_POLICY, CAL_VERSION

VERSIONS_VERSION = "versioned-learning-v1.0.0"

_VERSIONS: list[dict[str, Any]] = []
_ACTIVE: dict[str, Any] = {
    "planner_weights": dict(BASE_PLANNER_WEIGHTS),
    "policy": dict(BASE_POLICY),
    "confidence": {},
    "applicability_rules": [],
    "failure_conditions": [],
    "planner_version": "planner-v1.0.0",
    "policy_version": "policy-v1.0.0",
    "framework_overlay_version": "framework-overlay-v1.0.0",
}


def reset_versions() -> None:
    _VERSIONS.clear()
    _ACTIVE.clear()
    _ACTIVE.update(
        {
            "planner_weights": dict(BASE_PLANNER_WEIGHTS),
            "policy": dict(BASE_POLICY),
            "confidence": {},
            "applicability_rules": [],
            "failure_conditions": [],
            "planner_version": "planner-v1.0.0",
            "policy_version": "policy-v1.0.0",
            "framework_overlay_version": "framework-overlay-v1.0.0",
        }
    )


def _bump(ver: str) -> str:
    # planner-v1.0.0 → planner-v1.0.1 / minor bump on last segment
    try:
        prefix, num = ver.rsplit("-v", 1)
        parts = [int(x) for x in num.split(".")]
        parts[-1] += 1
        return f"{prefix}-v{'.'.join(str(p) for p in parts)}"
    except Exception:
        return f"{ver}+1"


def active_state() -> dict[str, Any]:
    return deepcopy(_ACTIVE)


def list_versions() -> list[dict[str, Any]]:
    return deepcopy(_VERSIONS)


def deploy_approved(proposal: dict[str, Any], simulation: dict[str, Any]) -> dict[str, Any]:
    """Apply an approved proposal into a new versioned overlay (never rewrite source frameworks)."""
    kind = proposal.get("kind")
    before = active_state()
    after = deepcopy(before)

    if kind == "adjust_planner_priority":
        target = str(proposal.get("target") or "")
        delta = float(proposal.get("delta") or -0.04)
        cur = float(after["planner_weights"].get(target, 0.70))
        after["planner_weights"][target] = round(max(0.05, min(0.95, cur + delta)), 4)
        after["planner_version"] = _bump(str(after["planner_version"]))
    elif kind in {"increase_confidence", "decrease_confidence"}:
        target = str(proposal.get("target") or "")
        after["confidence"][target] = {
            "value": float(proposal.get("to_value") or proposal.get("from_value") or 0.9),
            "from_value": proposal.get("from_value"),
            "regime": proposal.get("regime"),
        }
        after["framework_overlay_version"] = _bump(str(after["framework_overlay_version"]))
    elif kind == "adjust_policy":
        target = str(proposal.get("target") or "max_stock_weight")
        after["policy"][target] = float(proposal.get("to_value") or after["policy"].get(target, 0.08))
        after["policy_version"] = _bump(str(after["policy_version"]))
    elif kind == "add_applicability_rule":
        after["applicability_rules"].append(
            {
                "target": proposal.get("target"),
                "rule": proposal.get("rule"),
                "scope": proposal.get("scope") or {},
                "reason": proposal.get("reason"),
            }
        )
        after["framework_overlay_version"] = _bump(str(after["framework_overlay_version"]))
    elif kind == "add_failure_condition":
        after["failure_conditions"].append(
            {
                "target": proposal.get("target"),
                "condition": proposal.get("condition"),
                "reason": proposal.get("reason"),
                "regime": proposal.get("regime"),
            }
        )
    elif kind == "no_change":
        return {
            "deployed": False,
            "reason": "no_change",
            "versions_version": VERSIONS_VERSION,
        }

    version_id = f"ver_{uuid.uuid4().hex[:12]}"
    entry = {
        "version_id": version_id,
        "versions_version": VERSIONS_VERSION,
        "cal_version": CAL_VERSION,
        "proposal_id": proposal.get("proposal_id"),
        "kind": kind,
        "created_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "before": before,
        "after": after,
        "simulation": {
            "passed": simulation.get("passed"),
            "ies_delta": simulation.get("ies_delta"),
            "live_delta": simulation.get("live_delta"),
        },
        "reversible": True,
        "source_overwritten": False,
    }
    _VERSIONS.append(entry)
    _ACTIVE.clear()
    _ACTIVE.update(after)
    return {
        "deployed": True,
        "version_id": version_id,
        "planner_version": after.get("planner_version"),
        "policy_version": after.get("policy_version"),
        "framework_overlay_version": after.get("framework_overlay_version"),
        "entry": entry,
        "source_overwritten": False,
    }
