"""Evaluator — decide whether to recompute decision / refresh report."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from institutional_observation.significance import SignificanceResult


@dataclass(frozen=True)
class EvaluationPlan:
    recompute_decision: bool
    refresh_report: bool
    rerun_forecast: bool
    rerun_valuation: bool
    recommended_action: str
    requires_review: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "recompute_decision": self.recompute_decision,
            "refresh_report": self.refresh_report,
            "rerun_forecast": self.rerun_forecast,
            "rerun_valuation": self.rerun_valuation,
            "recommended_action": self.recommended_action,
            "requires_review": self.requires_review,
        }


def plan_actions(
    significance: SignificanceResult,
    *,
    category: str,
    watchlist_priority: bool = False,
) -> EvaluationPlan:
    sev = significance.severity
    cat = str(category or "")

    recompute = bool(significance.recompute_decision)
    refresh = recompute or sev in {"critical", "high"}
    rerun_forecast = cat in {"Macro", "Forecast", "Quarterly Results"} and sev in {
        "critical",
        "high",
        "medium",
    }
    rerun_valuation = cat in {"Valuation", "Quarterly Results"} and sev in {"critical", "high"}

    if sev == "ignore" or significance.silent_graph_update:
        action = "No action"
        review = False
    elif sev == "critical":
        action = "Analyst review"
        review = True
        recompute = True
        refresh = True
    elif recompute:
        action = "Recompute decision"
        review = watchlist_priority or sev == "high"
    elif rerun_valuation:
        action = "Re-run valuation"
        review = watchlist_priority
    elif rerun_forecast:
        action = "Re-run forecast"
        review = watchlist_priority
    elif significance.emit_observation:
        action = "Monitor"
        review = watchlist_priority and sev in {"medium", "high", "critical"}
    else:
        action = "No action"
        review = False

    if watchlist_priority and action == "Monitor" and sev in {"medium", "high", "critical"}:
        review = True
        if sev in {"high", "critical"}:
            action = "Analyst review"

    return EvaluationPlan(
        recompute_decision=recompute,
        refresh_report=refresh,
        rerun_forecast=rerun_forecast,
        rerun_valuation=rerun_valuation,
        recommended_action=action,
        requires_review=review,
    )


def recompute_decision_if_needed(
    ticker: str,
    plan: EvaluationPlan,
) -> tuple[Optional[dict[str, Any]], bool]:
    """Deterministically re-run IDS when the plan requires it."""
    if not plan.recompute_decision:
        return None, False
    try:
        from institutional_decision.production import decide_company

        result = decide_company(
            {
                "ticker": ticker,
                "include_calibration": True,
                "include_drift": True,
            }
        )
        return result, True
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}, False
