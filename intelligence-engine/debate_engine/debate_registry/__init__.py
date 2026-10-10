"""Debate registry — normalise ITCE thesis and optional analyst positions."""

from __future__ import annotations

from typing import Any


def _safe_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def extract_thesis(payload: dict[str, Any]) -> dict[str, Any]:
    itce = _safe_dict(payload.get("thesis_engine"))
    nested = _safe_dict(itce.get("thesis_engine"))
    body = nested or itce
    thesis = _safe_dict(
        body.get("thesis")
        or body.get("institutional_investment_thesis")
        or payload.get("thesis")
    )
    # Ask AGI soft slice itself is already the compact thesis.
    if not thesis and body.get("core_thesis"):
        thesis = body
    return thesis


def extract_analyst_opinions(payload: dict[str, Any]) -> list[dict[str, Any]]:
    opinions = payload.get("analyst_opinions") or payload.get("positions") or []
    return [x for x in _safe_list(opinions) if isinstance(x, dict)]


def register_debate(debate: dict[str, Any]) -> dict[str, Any]:
    return {
        "position_count": len(_safe_list(debate.get("analyst_positions"))),
        "agreement_count": len(_safe_list((debate.get("agreement") or {}).get("common_conclusions"))),
        "disagreement_count": len(_safe_list((debate.get("disagreement") or {}).get("conflicts"))),
        "evidence_conflict_count": len(_safe_list(debate.get("evidence_conflicts"))),
        "assumption_conflict_count": len(_safe_list(debate.get("assumption_conflicts"))),
        "minority_count": len(_safe_list(debate.get("minority_report"))),
        "state": (debate.get("consensus") or {}).get("state"),
    }
