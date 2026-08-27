"""Module 7 — Portfolio Committee.

Members: Research, Valuation, Risk, Macro, Exposure, Scenario, Portfolio.
Outputs Increase/Reduce/Hold/Exit/Watch/Replace/Hedge — not Buy/Sell.
"""

from __future__ import annotations

from typing import Any

COMMITTEE_VERSION = "portfolio-committee-v1.0.0"


def convene_portfolio_committee(
    *,
    sizing: dict[str, Any],
    policy_eval: dict[str, Any],
    risk: dict[str, Any],
    exposure: dict[str, Any],
    scenarios: dict[str, Any],
    research_record: dict[str, Any] | None = None,
    downside: dict[str, Any] | None = None,
    portfolio_evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    research_record = research_record or {}
    downside = downside or {}
    portfolio_evidence = portfolio_evidence or {}

    # Portfolio-typed questions run no valuation frameworks of their own; the
    # valuation member then votes on the validated evidence pack instead of
    # withholding as though no valuation work existed.
    ev_fields = portfolio_evidence.get("evidence_fields") or {}
    valuation_evidence = [
        k for k in ("current_pe", "historical_pe", "peer_pe", "sector_pe") if ev_fields.get(k) is not None
    ]
    framework_executed = any(
        f.get("status") == "executed" for f in (research_record.get("frameworks") or [])
    )
    members = {
        "research": {
            "stance": (research_record.get("committee") or {}).get("stance") or "Research",
            "vote": "support" if (research_record.get("committee") or {}).get("can_conclude") else "caution",
        },
        "valuation": {
            "stance": "valuation",
            "vote": "support" if (framework_executed or len(valuation_evidence) >= 3) else "withhold",
            "basis": "frameworks" if framework_executed else ("evidence_pack" if valuation_evidence else "none"),
            "evidence_fields": valuation_evidence,
        },
        "risk": {
            "stance": "risk_budget",
            "vote": "support" if float(risk.get("risk_budget_used") or 0) <= 1.0 else "reduce",
            "risk_contribution": risk.get("risk_contribution"),
        },
        "macro": {
            "stance": "macro_scenarios",
            "vote": "caution"
            if any(float(s.get("expected_return") or 0) <= -0.15 for s in (scenarios.get("shocks") or [])[:3])
            else "neutral",
        },
        "exposure": {
            "stance": "exposure_limits",
            "vote": "reject" if exposure.get("rejected") else "support",
            "breaches": exposure.get("breaches") or [],
        },
        "scenario": {
            "stance": "scenario_set",
            "vote": "support" if (scenarios.get("scenarios") or {}).get("base") else "withhold",
        },
        "portfolio": {
            "stance": "mandate_policy",
            "vote": "support" if policy_eval.get("allowed") else "reject",
            "replace_candidate": policy_eval.get("replace_candidate"),
        },
    }

    if sizing.get("withheld") or downside.get("withhold") or not downside.get("computable", True):
        action = "Withhold"
        can_recommend = False
        conclusion = "Portfolio recommendation withheld — required downside evidence missing."
    elif members["exposure"]["vote"] == "reject" and sizing.get("action") == "Increase":
        # Sector/country breach on increase → Reduce or Replace
        if policy_eval.get("replace_candidate"):
            action = "Replace"
            can_recommend = True
            rc = policy_eval["replace_candidate"]
            conclusion = (
                f"Replace/reduce {rc.get('symbol')} to fund a smaller {sizing.get('action')} within sector limits; "
                f"target weight {float(sizing.get('target_weight') or 0):.1%}."
            )
        else:
            action = "Reduce"
            can_recommend = True
            conclusion = "Exposure limit exceeded — reduce weight toward policy-compliant target."
    elif not policy_eval.get("allowed") and sizing.get("action") in {"Increase", "Hold"}:
        action = "Reduce" if float(sizing.get("current_weight") or 0) > float(sizing.get("target_weight") or 0) else "Watch"
        can_recommend = True
        conclusion = "Policy constraints prevent increase; " + (sizing.get("reason") or "hold/watch.")
    else:
        action = sizing.get("action") or "Watch"
        # Hedge when tail risk high but core thesis intact
        if float(risk.get("tail_risk") or 0) >= 0.35 and action in {"Increase", "Hold"}:
            action = "Hedge"
        can_recommend = action != "Withhold"
        conclusion = (
            f"{action} — target weight {float(sizing.get('target_weight') or 0):.1%} "
            f"(max {float(sizing.get('maximum_weight') or 0):.1%}, min {float(sizing.get('minimum_weight') or 0):.1%}). "
            f"{sizing.get('reason') or ''}"
        ).strip()

    votes = [m["vote"] for m in members.values()]
    return {
        "committee_version": COMMITTEE_VERSION,
        "members": members,
        "action": action,
        "can_recommend": can_recommend,
        "unsupported": False if can_recommend or action == "Withhold" else True,
        "conclusion": conclusion,
        "target_weight": sizing.get("target_weight"),
        "maximum_weight": sizing.get("maximum_weight"),
        "minimum_weight": sizing.get("minimum_weight"),
        "conviction": sizing.get("conviction"),
        "confidence": sizing.get("confidence"),
        "vote_summary": {
            "support": votes.count("support"),
            "reject": votes.count("reject"),
            "reduce": votes.count("reduce"),
            "caution": votes.count("caution") + votes.count("neutral") + votes.count("withhold"),
        },
        # Never emit Buy/Sell
        "forbidden_labels_avoided": ["Buy", "Sell", "Accumulate", "Strong Buy"],
    }
