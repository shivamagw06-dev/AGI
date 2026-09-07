"""Trigger Evaluation Engine — scenario impact without rewriting theses."""

from __future__ import annotations

from typing import Any

from catalyst_trigger_intelligence.schema import CTI_VERSION
from catalyst_trigger_intelligence.store import get_store
from catalyst_trigger_intelligence.triggers import build_company_triggers
from catalyst_trigger_intelligence import traces


def _normalize_observation(value: Any) -> str:
    return str(value or "").strip().lower()


def _condition_met(condition: str, observation: dict[str, Any]) -> bool | None:
    """Best-effort deterministic match. None = insufficient evidence (keep Watching)."""
    cond = _normalize_observation(condition)
    if not observation:
        return None

    # Explicit boolean / status from monitoring feed
    if "triggered" in observation:
        return bool(observation.get("triggered"))
    if observation.get("status") in {"triggered", "confirmed", "met"}:
        return True
    if observation.get("status") in {"not_met", "missed"}:
        return False

    # Metric dictionary: {"revenue_growth": 0.16, ...}
    metrics = observation.get("metrics") or observation
    if not isinstance(metrics, dict):
        return None

    # Simple patterns used in catalog
    if "revenue growth > 15%" in cond or "cc growth > 6%" in cond:
        g = metrics.get("revenue_growth") or metrics.get("cc_growth") or metrics.get("revenue_growth_pct")
        if g is None:
            return None
        try:
            g = float(g)
            if g > 1.5:  # allow percent points
                g = g / 100.0
            threshold = 0.15 if "15%" in cond else 0.06
            return g > threshold
        except (TypeError, ValueError):
            return None

    if "25bps" in cond or "25 bps" in cond or "rate cut" in cond or "rbi" in cond:
        cut = metrics.get("rate_cut_bps") or metrics.get("rbi_cut_bps")
        if cut is not None:
            try:
                return float(cut) >= 25
            except (TypeError, ValueError):
                return None

    if "credit cost > 0.8%" in cond:
        cc = metrics.get("credit_cost") or metrics.get("credit_cost_pct")
        if cc is None:
            return None
        try:
            cc = float(cc)
            if cc > 1.5:
                cc = cc / 100.0
            return cc > 0.008 if cc < 0.05 else cc > 0.8
        except (TypeError, ValueError):
            return None

    # Keyword confirmation from event text
    text = _normalize_observation(observation.get("event_text") or observation.get("headline"))
    if text and any(k in text for k in ("beat", "cut rates", "rate cut", "mega deal", "buyback")):
        if any(k in cond for k in ("growth", "deal", "buyback", "rate cut", "25bps")):
            return True
    return None


def _scenario_assessment(impact: str, current_scenario: str) -> dict[str, Any]:
    """Map impact code → IC-style assessment. Never auto-rewrites thesis."""
    mapping = {
        "strengthens_bull": {"bull": "Strengthened", "base": "Unchanged", "bear": "Weakened"},
        "weakens_bull": {"bull": "Weakened", "base": "Unchanged", "bear": "Unchanged"},
        "strengthens_base": {"bull": "Unchanged", "base": "Strengthened", "bear": "Unchanged"},
        "weakens_base": {"bull": "Unchanged", "base": "Weakened", "bear": "Unchanged"},
        "invalidates_base": {"bull": "Review", "base": "Invalidated", "bear": "Review"},
        "strengthens_bear": {"bull": "Weakened", "base": "Weakened", "bear": "Strengthened"},
        "weakens_bear": {"bull": "Unchanged", "base": "Unchanged", "bear": "Weakened"},
        "neutral": {"bull": "Unchanged", "base": "Unchanged", "bear": "Unchanged"},
    }
    states = mapping.get(impact, mapping["neutral"])
    return {
        "current_view": current_scenario,
        "scenario_states": states,
        "summary": states.get(current_scenario.split("_")[0] if "_" in current_scenario else current_scenario, "Unchanged"),
        "thesis_auto_updated": False,
        "governance_auto_updated": False,
        "recommended_action": (
            "Committee Review"
            if impact == "invalidates_base" or states.get("base") == "Invalidated"
            else ("Review" if any(v in {"Strengthened", "Weakened", "Invalidated"} for v in states.values()) else "Monitor")
        ),
        "note": "CTI updates scenario assessment only — Investment Office decides thesis changes.",
    }


def evaluate_trigger(
    trigger_id: str,
    *,
    observation: dict[str, Any] | None = None,
    confirm: bool = False,
    apply: bool = False,
) -> dict[str, Any]:
    span = traces.begin("trigger_evaluation", meta={"trigger_id": trigger_id})
    store = get_store()
    trigger = store.get(trigger_id)
    if not trigger:
        traces.end(span, ok=False)
        return {"found": False, "trigger_id": trigger_id}

    met = _condition_met(str(trigger.get("condition") or ""), observation or {})
    state = trigger.get("state") or "Watching"
    assessment = None

    if met is True:
        store.set_state(trigger_id, "Triggered", note="condition_met")
        state = "Triggered"
        if confirm:
            store.set_state(trigger_id, "Confirmed", note="ops_or_source_confirmed")
            state = "Confirmed"
        assessment = _scenario_assessment(str(trigger.get("impact") or "neutral"), str(trigger.get("current_institutional_view") or "base"))
        span2 = traces.begin("scenario_update", meta={"trigger_id": trigger_id, "impact": trigger.get("impact")})
        traces.end(span2, output={"scenario_impacts": assessment.get("scenario_states")})
        if apply:
            # Applied = assessment consumed by Monitoring/Investment Office — still no thesis rewrite
            store.set_state(trigger_id, "Applied", note="assessment_delivered_to_monitoring")
            state = "Applied"
    elif met is False:
        # Remain Watching; optional archive if permanently missed
        if observation and observation.get("archive_if_missed"):
            store.set_state(trigger_id, "Archived", note="condition_missed")
            state = "Archived"

    trigger = store.get(trigger_id) or trigger
    result = {
        "found": True,
        "trigger_id": trigger_id,
        "entity": trigger.get("entity"),
        "condition": trigger.get("condition"),
        "condition_met": met,
        "state": state,
        "impact": trigger.get("impact"),
        "scenario_assessment": assessment,
        "auto_rewrites_thesis": False,
        "cti_version": CTI_VERSION,
    }
    store.record_evaluation(result)
    traces.end(
        span,
        output={
            "triggered": 1 if met is True else 0,
            "scenario_impacts": (assessment or {}).get("scenario_states"),
        },
    )
    return result


def evaluate_company(
    ticker: str,
    *,
    observations: dict[str, dict[str, Any]] | None = None,
    auto_confirm: bool = False,
) -> dict[str, Any]:
    """Evaluate all watching triggers for a company against optional observation map.

    observations keys may be catalyst_id or trigger_id.
    """
    pack = build_company_triggers(ticker, persist=True)
    observations = observations or {}
    results = []
    for tr in pack.get("triggers") or []:
        obs = (
            observations.get(tr["trigger_id"])
            or observations.get(tr.get("catalyst_id") or "")
            or observations.get("default")
        )
        if obs is None:
            continue
        results.append(
            evaluate_trigger(
                tr["trigger_id"],
                observation=obs,
                confirm=auto_confirm,
                apply=auto_confirm,
            )
        )

    activated = [r for r in results if r.get("condition_met") is True]
    return {
        "ticker": (ticker or "").upper(),
        "current_scenario": pack.get("current_scenario"),
        "evaluated": len(results),
        "activated": len(activated),
        "results": results,
        "scenario_matrix": _matrix_from_results(activated),
        "auto_rewrites_thesis": False,
        "cti_version": CTI_VERSION,
    }


def _matrix_from_results(activated: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for r in activated:
        rows.append(
            {
                "trigger": r.get("condition"),
                "effect": (r.get("scenario_assessment") or {}).get("scenario_states"),
                "recommended_action": (r.get("scenario_assessment") or {}).get("recommended_action"),
            }
        )
    return rows


def trigger_matrix_report(ticker: str | None = None) -> dict[str, Any]:
    """IC-facing trigger matrix: Trigger → Effect."""
    store = get_store()
    if ticker:
        build_company_triggers(ticker, persist=True)
        rows = store.list_for_entity(ticker)
    else:
        rows = store.list_all()
    matrix = [
        {
            "trigger": f"{r.get('event')}: {r.get('condition')}",
            "entity": r.get("entity"),
            "priority": r.get("priority"),
            "state": r.get("state"),
            "effect": r.get("impact_label") or r.get("impact"),
            "affected_scenario": r.get("affected_scenario"),
        }
        for r in rows
    ]
    return {
        "ticker": (ticker or "").upper() or None,
        "matrix": matrix,
        "count": len(matrix),
        "rule": "Trigger activations update scenario assessments — not theses automatically.",
        "cti_version": CTI_VERSION,
    }
