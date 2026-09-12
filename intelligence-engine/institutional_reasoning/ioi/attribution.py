"""Module 4 — Framework Attribution.

Never say "recommendation wrong." Attribute which framework / evidence /
assumption / scenario / policy was correct or wrong.
"""

from __future__ import annotations

from typing import Any

ATTRIBUTION_VERSION = "framework-attribution-v1.0.0"


def _f(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _verdict(ok: bool) -> str:
    return "Correct" if ok else "Wrong"


def attribute_outcome(
    lifecycle: dict[str, Any],
    market: dict[str, Any],
    evaluation: dict[str, Any],
    *,
    force_wrong: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Attribute success/failure to specific reasoning components.

    force_wrong: suite helper to pin known failure modes (e.g. {"macro": True}).
    """
    force_wrong = force_wrong or {}
    frameworks = lifecycle.get("frameworks") or []
    actual = _f(evaluation.get("actual_return"))
    expected = _f(evaluation.get("expected_return"))
    err = _f(evaluation.get("abs_return_error"))
    downside_err = _f(evaluation.get("downside_error"))
    scenario_acc = _f(evaluation.get("scenario_accuracy"), 0.7)
    alpha = _f(evaluation.get("alpha") or market.get("alpha"))
    sector_ret = _f(market.get("sector_return"))
    bench = _f(market.get("benchmark_return"))

    # Valuation frameworks: correct if return error small relative to thesis
    valuation_ok = err <= 0.08
    # Business quality: correct if absolute loss not catastrophic when quality was supporting
    bq_ok = actual > -0.20
    # Macro: wrong if sector/benchmark diverge sharply from expected direction
    macro_ok = True
    if expected >= 0 and sector_ret < -0.05 and actual < 0:
        macro_ok = False
    if expected >= 0 and bench - actual >= 0.12:
        macro_ok = False
    # Scenario: based on scenario accuracy
    scenario_ok = scenario_acc >= 0.55
    # Policy: wrong if concentration/risk contributed to oversized loss
    risk = lifecycle.get("risk") or {}
    policy = lifecycle.get("policy") or {}
    policy_ok = True
    if downside_err >= 0.10 and _f(risk.get("risk_contribution")) >= 0.12:
        policy_ok = False
    if policy.get("violates_concentration") and actual < -0.10:
        policy_ok = False
    # Sizing: wrong if large weight + large negative alpha
    weight = _f(lifecycle.get("position_weight"))
    sizing_ok = not (weight >= 0.05 and alpha <= -0.10)

    if force_wrong.get("macro"):
        macro_ok = False
    if force_wrong.get("scenario"):
        scenario_ok = False
    if force_wrong.get("valuation"):
        valuation_ok = False
    if force_wrong.get("sizing") or force_wrong.get("policy"):
        sizing_ok = False
        if force_wrong.get("policy"):
            policy_ok = False
    if force_wrong.get("business_quality"):
        bq_ok = False

    components: list[dict[str, Any]] = []

    # Per executed / insufficient framework
    for fw in frameworks:
        fid = str(fw.get("framework_id") or "")
        name = str(fw.get("name") or fid)
        status = fw.get("status")
        if "rel_val" in fid or "hist_multiples" in fid or "margin_of_safety" in fid or "peer" in fid:
            ok = valuation_ok
            kind = "valuation"
        elif "business_quality" in fid or "roic" in fid:
            ok = bq_ok
            kind = "business_quality"
        elif "accounting" in fid:
            ok = actual > -0.25
            kind = "accounting"
        elif "dcf" in fid:
            # DCF applicability correctness is about method choice, not return
            ok = status in {"executed", "not_applicable"}
            kind = "method"
        else:
            ok = valuation_ok
            kind = "other"
        components.append(
            {
                "component": fid or name,
                "label": name,
                "kind": kind,
                "verdict": _verdict(ok),
                "framework_status": status,
            }
        )

    # Timing: wrong if entry near local high and large negative alpha
    entry_timing = lifecycle.get("entry_timing") or {}
    timing_ok = True
    if entry_timing.get("near_high") and alpha <= -0.08:
        timing_ok = False
    if force_wrong.get("timing"):
        timing_ok = False

    # Execution: wrong if slippage / partial fill drove gap vs thesis
    execution = lifecycle.get("execution") or {}
    execution_ok = True
    if _f(execution.get("slippage_bps")) >= 40 and err >= 0.05:
        execution_ok = False
    if execution.get("partial_fill") and abs(actual - expected) >= 0.06:
        execution_ok = False
    if force_wrong.get("execution"):
        execution_ok = False

    # Framework channel aggregate (distinct from per-framework rows)
    framework_ok = valuation_ok and bq_ok
    if force_wrong.get("framework"):
        framework_ok = False

    # Always attribute macro / scenario / policy / sizing / evidence / timing / execution
    components.extend(
        [
            {
                "component": "macro",
                "label": "Macro",
                "kind": "macro",
                "verdict": _verdict(macro_ok),
            },
            {
                "component": "scenario",
                "label": "Scenario",
                "kind": "scenario",
                "verdict": _verdict(scenario_ok),
            },
            {
                "component": "policy",
                "label": "Policy",
                "kind": "policy",
                "verdict": _verdict(policy_ok),
            },
            {
                "component": "sizing",
                "label": "Position Sizing",
                "kind": "sizing",
                "verdict": _verdict(sizing_ok),
            },
            {
                "component": "evidence",
                "label": "Evidence Coverage",
                "kind": "evidence",
                "verdict": _verdict(bool(lifecycle.get("research_djg"))),
            },
            {
                "component": "framework",
                "label": "Framework Channel",
                "kind": "framework",
                "verdict": _verdict(framework_ok),
            },
            {
                "component": "timing",
                "label": "Entry Timing",
                "kind": "timing",
                "verdict": _verdict(timing_ok),
            },
            {
                "component": "execution",
                "label": "Execution Quality",
                "kind": "execution",
                "verdict": _verdict(execution_ok),
            },
        ]
    )

    wrong = [c for c in components if c["verdict"] == "Wrong"]
    correct = [c for c in components if c["verdict"] == "Correct"]

    # Primary attribution — prefer non-valuation when valuation is correct
    primary = None
    if wrong:
        # Prefer macro/scenario/sizing/policy/timing/execution over valuation if mixed
        priority = {
            "macro": 0,
            "scenario": 1,
            "timing": 2,
            "execution": 3,
            "sizing": 4,
            "policy": 5,
            "framework": 6,
            "business_quality": 7,
            "valuation": 8,
            "evidence": 9,
        }
        wrong_sorted = sorted(wrong, key=lambda c: priority.get(c["kind"], 9))
        primary = wrong_sorted[0]
    elif err > 0.05:
        # Error exists but no component marked wrong — still attribute (never unattributed)
        primary = {
            "component": "assumption",
            "label": "Return Assumption",
            "kind": "assumption",
            "verdict": "Wrong",
            "note": "Residual forecast error attributed to return assumption",
        }
        wrong.append(primary)
        # Update components list
        components.append(primary)

    failure = err > 0.08 or (evaluation.get("grade") in {"D", "F"}) or alpha <= -0.10
    unattributed = bool(failure and not wrong)

    channels = {
        "evidence": _verdict(bool(lifecycle.get("research_djg"))),
        "framework": _verdict(framework_ok),
        "macro": _verdict(macro_ok),
        "scenario": _verdict(scenario_ok),
        "sizing": _verdict(sizing_ok),
        "timing": _verdict(timing_ok),
        "execution": _verdict(execution_ok),
        "policy": _verdict(policy_ok),
        "valuation": _verdict(valuation_ok),
    }

    return {
        "attribution_version": ATTRIBUTION_VERSION,
        "components": components,
        "correct": [c["component"] for c in correct],
        "wrong": [c["component"] for c in wrong],
        "primary_failure": primary,
        "channels": channels,
        "summary": {
            c["label"]: c["verdict"]
            for c in components
            if c["kind"]
            in {
                "valuation",
                "business_quality",
                "macro",
                "scenario",
                "policy",
                "sizing",
                "evidence",
                "framework",
                "timing",
                "execution",
                "assumption",
            }
        },
        "failure": failure,
        "unattributed": unattributed,
        "attributed": not unattributed,
    }
