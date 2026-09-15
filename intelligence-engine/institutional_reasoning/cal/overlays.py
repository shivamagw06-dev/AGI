"""Soft overlays — read approved CAL versions without rewriting frameworks.

Modules 2–6 surface as query helpers for planner/confidence/policy/applicability.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.cal.versions import active_state
from institutional_reasoning.ioi.schema import ies_confidence

OVERLAY_VERSION = "cal-overlays-v1.0.0"


def planner_weights() -> dict[str, Any]:
    state = active_state()
    return {
        "overlay_version": OVERLAY_VERSION,
        "planner_version": state.get("planner_version"),
        "weights": dict(state.get("planner_weights") or {}),
        "source_overwritten": False,
    }


def planner_priority(framework_id: str) -> float | None:
    weights = (active_state().get("planner_weights") or {})
    if framework_id in weights:
        return float(weights[framework_id])
    return None


def confidence_for(framework_id: str, *, regime: str | None = None) -> dict[str, Any]:
    state = active_state()
    live = (state.get("confidence") or {}).get(framework_id) or {}
    ies = ies_confidence(framework_id)
    value = float(live.get("value") or ies)
    return {
        "framework": framework_id,
        "ies": ies,
        "live": live.get("value"),
        "dynamic": value,
        "regime": live.get("regime") or regime,
        "sector_specific": live.get("sector"),
        "horizon": live.get("horizon"),
        "overlay_version": state.get("framework_overlay_version"),
        "source": "cal_overlay" if live else "ies_seed",
    }


def contextual_confidence(
    framework_id: str,
    *,
    sector: str | None = None,
    regime: str | None = None,
    horizon: str | None = None,
    market: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from institutional_reasoning.cal.contextual_confidence import (
        contextual_confidence as _contextual,
    )

    return _contextual(
        framework_id,
        sector=sector,
        regime=regime,
        horizon=horizon,
        market=market,
    )


def policy_overlay() -> dict[str, Any]:
    state = active_state()
    return {
        "overlay_version": OVERLAY_VERSION,
        "policy_version": state.get("policy_version"),
        "policy": dict(state.get("policy") or {}),
        "requires_human_approval_history": True,
        "source_overwritten": False,
    }


def applicability_rules(*, framework_id: str | None = None, regime: str | None = None) -> list[dict[str, Any]]:
    rules = list(active_state().get("applicability_rules") or [])
    out = []
    for r in rules:
        if framework_id and r.get("target") != framework_id:
            continue
        scope = r.get("scope") or {}
        if regime and scope.get("regime") and scope.get("regime") != regime:
            continue
        out.append(r)
    return out


def failure_conditions(*, target: str | None = None) -> list[dict[str, Any]]:
    rows = list(active_state().get("failure_conditions") or [])
    if target:
        rows = [r for r in rows if r.get("target") == target]
    return rows
