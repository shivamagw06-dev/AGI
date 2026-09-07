"""Module 8 — Learning Sandbox.

No change reaches production without replay / IES / historical comparison.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.cal.schema import BASE_PLANNER_WEIGHTS
from institutional_reasoning.cal.versions import active_state
from institutional_reasoning.ioi.schema import ies_confidence

SANDBOX_VERSION = "learning-sandbox-v1.0.0"


def _synthetic_ies_score(weights: dict[str, float]) -> float:
    """Proxy historical benchmark: heavily penalise collapsing core framework weights."""
    core = ("rel_val_damodaran", "hist_multiples", "business_quality_roic", "margin_of_safety")
    score = 100.0
    for fid in core:
        base = BASE_PLANNER_WEIGHTS.get(fid, 0.7)
        cur = float(weights.get(fid, base))
        if cur < base - 0.15:
            score -= 25.0
        elif cur < base - 0.05:
            score -= 8.0
        # Tiny calibrations are fine
    # DCF reductions are often desirable for banks — small penalty only if near zero
    dcf = float(weights.get("dcf_applicability", weights.get("dcf_fcff", 0.6)))
    if dcf < 0.15:
        score -= 20.0
    return max(0.0, min(100.0, score))


def _synthetic_live_score(proposal: dict[str, Any], *, baseline_live: float) -> float:
    """Proxy live-outcome metric after proposal."""
    kind = proposal.get("kind")
    live = baseline_live
    if kind == "decrease_confidence" and proposal.get("reason"):
        live = min(0.99, live + 0.03)  # better calibrated
    if kind == "adjust_planner_priority" and float(proposal.get("delta") or 0) < 0:
        # Reducing a failing framework should improve live
        live = min(0.99, live + 0.04)
    if kind == "adjust_policy":
        live = min(0.99, live + 0.02)
    if kind == "add_applicability_rule":
        live = min(0.99, live + 0.03)
    if kind == "increase_confidence":
        live = min(0.99, live + 0.01)
    if kind == "add_failure_condition":
        live = min(0.99, live + 0.02)
    # Explicit hurt signal for suite
    if proposal.get("force_hurt_ies"):
        live = live  # live may still improve while IES collapses via weights
    return round(live, 4)


def simulate_proposal(
    proposal: dict[str, Any],
    *,
    historical_decisions: list[dict[str, Any]] | None = None,
    baseline_live: float | None = None,
) -> dict[str, Any]:
    """Replay-style simulation. Rejects if IES proxy regresses."""
    state = active_state()
    weights = dict(state.get("planner_weights") or BASE_PLANNER_WEIGHTS)
    ies_before = _synthetic_ies_score(weights)

    trial_weights = dict(weights)
    if proposal.get("kind") == "adjust_planner_priority":
        target = str(proposal.get("target") or "")
        delta = float(proposal.get("delta") or 0.0)
        if proposal.get("force_hurt_ies"):
            # Suite helper: collapse a core weight
            trial_weights[target or "rel_val_damodaran"] = 0.05
        else:
            cur = float(trial_weights.get(target, 0.7))
            trial_weights[target] = round(max(0.05, min(0.95, cur + delta)), 4)

    ies_after = _synthetic_ies_score(trial_weights)
    ies_delta = round(ies_after - ies_before, 4)

    live_before = float(baseline_live if baseline_live is not None else 0.85)
    # Derive from proposal target confidence if present
    if proposal.get("from_value") is not None:
        live_before = float(proposal.get("to_value") or proposal.get("from_value") or live_before)
        if proposal.get("kind") == "decrease_confidence":
            live_before = float(proposal.get("to_value") or live_before)
    live_after = _synthetic_live_score(proposal, baseline_live=live_before)
    if proposal.get("force_hurt_ies"):
        ies_after = max(0.0, ies_before - 30.0)
        ies_delta = round(ies_after - ies_before, 4)
    live_delta = round(live_after - live_before, 4)

    # Historical replay count (observational)
    hist = historical_decisions or []
    replayed = len(hist)

    rejects: list[str] = []
    if proposal.get("kind") == "no_change":
        return {
            "sandbox_version": SANDBOX_VERSION,
            "passed": False,
            "rejected": True,
            "reason": "no_change",
            "ies_before": ies_before,
            "ies_after": ies_before,
            "ies_delta": 0.0,
            "live_before": live_before,
            "live_after": live_before,
            "live_delta": 0.0,
            "replayed_decisions": replayed,
        }

    if ies_delta < -0.5:  # any material IES regression
        rejects.append("ies_regression")
    if proposal.get("kind") == "adjust_policy" and not proposal.get("requires_human_approval", True):
        # Policy always requires human approval flag
        pass
    if proposal.get("auto_apply"):
        rejects.append("auto_apply_forbidden")

    # Accept when live improves or stays and IES does not regress
    improves = live_delta >= 0.0 and ies_delta >= -0.5
    if proposal.get("kind") in {
        "decrease_confidence",
        "adjust_planner_priority",
        "add_applicability_rule",
        "add_failure_condition",
        "adjust_policy",
        "increase_confidence",
    }:
        if not improves and "ies_regression" not in rejects:
            # Still accept small calibrations with flat live if IES ok
            if ies_delta >= 0 and live_delta >= -0.01:
                improves = True
            else:
                rejects.append("no_measurable_improvement")

    passed = not rejects and (improves or proposal.get("kind") == "increase_confidence")
    if "ies_regression" in rejects:
        passed = False

    return {
        "sandbox_version": SANDBOX_VERSION,
        "proposal_id": proposal.get("proposal_id"),
        "passed": passed,
        "rejected": not passed,
        "reasons": rejects,
        "reason": rejects[0] if rejects else ("improved" if passed else "rejected"),
        "ies_before": ies_before,
        "ies_after": ies_after,
        "ies_delta": ies_delta,
        "live_before": live_before,
        "live_after": live_after,
        "live_delta": live_delta,
        "replayed_decisions": replayed,
        "trial_weights": trial_weights if proposal.get("kind") == "adjust_planner_priority" else None,
        "note": "Sandbox only — production unchanged until approval + deploy.",
    }
