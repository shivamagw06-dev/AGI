"""Notifier — structured institutional alerts (no LLM, no NL rewriting)."""

from __future__ import annotations

from typing import Any, List

from institutional_observation.observation import InstitutionalObservation

_ALERTS: list[dict[str, Any]] = []


def reset_for_tests() -> None:
    _ALERTS.clear()


def notify(observation: InstitutionalObservation) -> dict[str, Any]:
    """Enqueue a structured alert for Mission Control / watchlist queues."""
    if observation.silent or observation.severity == "ignore":
        return {"queued": False, "reason": "silent_or_ignore"}
    alert = {
        "alert_id": f"alert-{observation.observation_id}",
        "observation_id": observation.observation_id,
        "ticker": observation.ticker or observation.company,
        "severity": observation.severity,
        "category": observation.category,
        "summary": observation.summary,
        "recommended_action": observation.recommended_action,
        "requires_review": observation.requires_review,
        "watchlist_priority": observation.watchlist_priority,
        "decision_changed": observation.decision_changed,
        "timestamp": observation.timestamp,
        "llm": False,
    }
    _ALERTS.append(alert)
    # Cap memory
    if len(_ALERTS) > 500:
        del _ALERTS[: len(_ALERTS) - 500]
    return {"queued": True, "alert": alert}


def recent_alerts(*, critical_only: bool = False, limit: int = 50) -> List[dict[str, Any]]:
    rows = list(_ALERTS)
    if critical_only:
        rows = [a for a in rows if a.get("severity") in {"critical", "high"}]
    return list(reversed(rows[-limit:]))
