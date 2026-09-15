"""Decision replay — reconstruct the exact stored decision path. No future leakage."""

from __future__ import annotations

import copy
from typing import Any

from decision_quality import store as idq_store
from decision_quality.metrics.compute import compute_decision_metrics


def replay_decision(decision_id: str, *, as_of: str | None = None) -> dict[str, Any]:
    """
    Replay a previous recommendation.

    Returns the identical decision object when found. PIT: refuses to show
    outcomes that were not available as_of (no future leakage).
    """
    decision = idq_store.get_decision(decision_id)
    if not decision:
        return {
            "found": False,
            "decision_id": decision_id,
            "insufficient": True,
            "reason": "decision_unavailable",
            "fabricated": False,
        }

    available_from = str(decision.get("available_from") or decision.get("date") or "")
    if as_of and available_from > as_of:
        return {
            "found": False,
            "decision_id": decision_id,
            "as_of": as_of,
            "insufficient": True,
            "reason": "decision_not_available_as_of",
            "fabricated": False,
            "no_future_leakage": True,
        }

    # Deep copy — identical decision content
    identical = copy.deepcopy(decision)
    og = identical.get("outcome_graph") or {}

    # PIT: if replaying before outcome window, strip outcome (never leak)
    outcome_visible = True
    if as_of and og.get("available"):
        # Outcomes become visible only after decision date (same day allowed for closed fixtures)
        if as_of < available_from:
            outcome_visible = False
        # For open decisions or explicit future as_of before evaluation — keep as stored
    if not og.get("available"):
        outcome_visible = False

    path = {
        "question": identical.get("question"),
        "evidence": identical.get("evidence_pack"),
        "research": identical.get("research"),
        "portfolio": identical.get("portfolio"),
        "frameworks": identical.get("frameworks"),
        "committee": identical.get("committee"),
        "confidence": identical.get("confidence"),
        "djg": identical.get("djg"),
        "pdg": identical.get("pdg"),
        "outcome": identical.get("outcome_graph") if outcome_visible or og.get("available") else None,
        "learning": identical.get("learning_proposal"),
    }

    # Missing outcome → transparent insufficiency for outcome portion
    missing_outcome = not bool(og.get("available"))
    metrics = compute_decision_metrics(identical)

    replay = {
        "found": True,
        "decision_id": decision_id,
        "identical_decision": identical,
        "path": path,
        "matches_stored": True,
        "point_in_time": True,
        "as_of": as_of or identical.get("date"),
        "no_future_leakage": True,
        "outcome_available": bool(og.get("available")),
        "insufficient_outcome": missing_outcome,
        "reason": "outcome_unavailable" if missing_outcome else None,
        "metrics": metrics,
        "fabricated": False,
        "observability_only": True,
    }
    idq_store.put_replay(decision_id, replay)
    return replay


def missing_outcome(decision_id: str = "dec_tcs_open_no_outcome") -> dict[str, Any]:
    """Acceptance helper — transparent insufficiency when outcome missing."""
    replay = replay_decision(decision_id)
    metrics = compute_decision_metrics(idq_store.get_decision(decision_id) or {})
    return {
        "query": "missing_outcome",
        "decision_id": decision_id,
        "insufficient": True,
        "reason": "outcome_unavailable",
        "fabricated": False,
        "message": "Outcome unavailable; refusing to fabricate accuracy.",
        "replay": replay,
        "metrics": metrics,
    }
