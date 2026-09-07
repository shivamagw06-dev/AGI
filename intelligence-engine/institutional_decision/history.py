"""Decision history — versioned recommendation transitions (in-memory)."""

from __future__ import annotations

from typing import Any, Optional

from institutional_decision.models import DecisionHistoryEntry, InstitutionalDecision

_HISTORY: dict[str, list[DecisionHistoryEntry]] = {}


def reset_for_tests() -> None:
    _HISTORY.clear()


def record(decision: InstitutionalDecision) -> DecisionHistoryEntry:
    ticker = str(decision.ticker or "").strip().upper()
    series = _HISTORY.setdefault(ticker, [])
    previous = series[-1].decision.recommendation if series else ""
    if previous and previous != decision.recommendation:
        transition = f"{previous}->{decision.recommendation}"
    elif previous:
        transition = f"{previous}->(same)"
    else:
        transition = f"(init)->{decision.recommendation}"
    entry = DecisionHistoryEntry(
        decision=decision,
        previous_recommendation=previous,
        transition=transition,
    )
    series.append(entry)
    return entry


def latest(ticker: str) -> Optional[InstitutionalDecision]:
    series = _HISTORY.get(str(ticker or "").strip().upper()) or []
    return series[-1].decision if series else None


def history_for(ticker: str) -> list[dict[str, Any]]:
    series = _HISTORY.get(str(ticker or "").strip().upper()) or []
    return [e.to_dict() for e in series]


def metrics() -> dict[str, Any]:
    return {
        "tickers": sorted(_HISTORY.keys()),
        "entries": sum(len(v) for v in _HISTORY.values()),
    }
