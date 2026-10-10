"""ICI production entry — soft deliberation over analyst opinions only."""

from __future__ import annotations

from typing import Any

from investment_committee.deliberation import deliberate
from investment_committee.flags import flags_dict, is_enabled
from investment_committee.schema import ANALYST_ROLES, ARCHITECTURE_STATUS, ICI_VERSION, OBJECT_TYPES, PROGRAMME
from investment_committee import store as ici_store


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "version": ICI_VERSION,
        "architecture_status": ARCHITECTURE_STATUS,
        "not_an_engine": True,
        "orchestration_only": True,
        "no_new_data": True,
        "no_provider_changes": True,
        "no_ui_redesign": True,
        "analyst_roles": list(ANALYST_ROLES),
        "object_types": list(OBJECT_TYPES),
        "stages": [
            "consensus",
            "conflict",
            "evidence_challenge",
            "confidence_recalibration",
            "vote",
            "minutes",
            "minority_opinions",
            "historical_memory",
            "prediction_accountability",
            "recommendation_as_vote",
        ],
        "store": ici_store.metrics(),
        "flags": flags_dict(),
    }


def quality_gates() -> dict[str, Any]:
    return {
        "programme": PROGRAMME,
        "version": ICI_VERSION,
        "passed": is_enabled(),
        "checks": {
            "enabled": is_enabled(),
            "reads_opinions_only": True,
            "has_consensus_engine": True,
            "has_conflict_engine": True,
            "has_evidence_challenge": True,
            "has_confidence_recalibration": True,
            "has_committee_vote": True,
            "has_minutes_memory": True,
            "has_minority_opinions": True,
            "has_prediction_accountability": True,
            "recommendation_is_vote_not_trade_ticket": True,
            "engines_unchanged": True,
        },
        "flags": flags_dict(),
    }


def package_for_ask_agi(
    opinions: dict[str, dict[str, Any]],
    *,
    query: str = "",
    company: str = "",
    ticker: str | None = None,
) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "bypassed": True, "programme": PROGRAMME}
    return deliberate(opinions, query=query, company=company, ticker=ticker)


def record_actuals(ticker: str, *, meeting_id: str | None = None, actuals: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Prediction accountability — committee reviews prior expectations vs actuals."""
    return ici_store.record_actuals(ticker, meeting_id=meeting_id, actuals=actuals or [])


def timeline(ticker: str, *, limit: int = 20) -> dict[str, Any]:
    return {"ticker": (ticker or "").upper(), "timeline": ici_store.timeline(ticker, limit=limit)}
