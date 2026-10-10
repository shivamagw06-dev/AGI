"""Controlled Ask AGI adapter for confluence, memory, forecasts and validation.

This module retrieves only the datasets required by the detected question intent.
It never generates a forecast and never turns a model estimate into an observed fact.
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

SUPPORTED_INTENTS = (
    "current_research_state",
    "confluence_explanation",
    "thesis_change",
    "forecast",
    "forecast_history",
    "outcome_review",
    "reliability",
    "ranking_explanation",
    "pipeline_health",
)

_ROUTES = {
    "current_research_state": ("confluence",),
    "confluence_explanation": ("confluence",),
    "thesis_change": ("memory",),
    "forecast": ("forecast", "validation"),
    "forecast_history": ("forecast",),
    "outcome_review": ("forecast", "ledger"),
    "reliability": ("validation", "rank_ic"),
    "ranking_explanation": ("confluence", "rankings"),
    "pipeline_health": ("health",),
}

_PATTERNS = (
    ("pipeline_health", r"\b(pipeline|mission control|engine working|system health)\b"),
    (
        "outcome_review",
        r"\b(was agi right|was (?:it|the forecast) right|outcome|settled|performed)\b",
    ),
    ("reliability", r"\b(reliab|accuracy|calibrat|rank[ -]?ic|brier|hit rate)"),
    (
        "thesis_change",
        r"\b(what changed|thesis chang|strengthen|weaken|deteriorat|improv(?:ed|ing))\b",
    ),
    (
        "ranking_explanation",
        r"\b(why .*rank|ranked highly|ranking explanation|research priority)\b",
    ),
    ("forecast_history", r"\b(forecast history|past forecasts|previous forecasts)\b"),
    (
        "forecast",
        r"\b(forecast|expect(?:s|ed|ation)?|next (?:day|week)|probability|\d+\s*d(?:ay)?)\b",
    ),
    (
        "confluence_explanation",
        r"\b(confluence|signals agree|why .*classif|confirmation|contradiction)\b",
    ),
    (
        "current_research_state",
        r"\b(current (?:research )?(?:state|view)|research state|agi think)\b",
    ),
)


def detect_intent(question: str, explicit: str | None = None) -> str | None:
    if explicit in SUPPORTED_INTENTS:
        return explicit
    text = (question or "").lower()
    for intent, pattern in _PATTERNS:
        if re.search(pattern, text):
            return intent
    return None


def _horizon(question: str, requested: str | None) -> str:
    if requested:
        return str(requested).lower()
    match = re.search(
        r"\b(1d|5d|20d|1 day|5 days?|20 days?)\b", (question or "").lower()
    )
    return (
        match.group(1).replace(" ", "").replace("days", "d").replace("day", "d")
        if match
        else "5d"
    )


def _base_url() -> str:
    return (
        os.getenv("AGIB_API_BASE_URL")
        or os.getenv("NODE_API_BASE_URL")
        or "https://finance-news-backend-19i5.onrender.com"
    ).rstrip("/")


def _get_json(path: str, timeout: float = 3.0) -> dict[str, Any]:
    request = Request(
        f"{_base_url()}{path}",
        headers={
            "Accept": "application/json",
            "User-Agent": "AGI-Research-Intelligence/1.0",
        },
    )
    with urlopen(
        request, timeout=timeout
    ) as response:  # noqa: S310 - configured AGI backend
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, dict) else {"rows": payload}


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(
            timezone.utc
        )
    except (TypeError, ValueError):
        return None


def _age(value: Any, now: datetime) -> dict[str, Any]:
    parsed = _parse_time(value)
    if not parsed:
        return {"as_of": value, "age_seconds": None, "age_label": "unknown"}
    seconds = max(0, int((now - parsed).total_seconds()))
    if seconds < 3600:
        label = f"{max(1, seconds // 60)}m"
    elif seconds < 86400:
        label = f"{seconds // 3600}h"
    else:
        label = f"{seconds // 86400}d"
    return {"as_of": parsed.isoformat(), "age_seconds": seconds, "age_label": label}


def _rows(payload: dict[str, Any], *keys: str) -> list[dict[str, Any]]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [row for row in value if isinstance(row, dict)]
    return []


def _latest_time(payload: dict[str, Any], rows: list[dict[str, Any]]) -> Any:
    for key in ("generated_at", "as_of", "forecast_time", "observed_at", "created_at"):
        if payload.get(key):
            return payload[key]
    for row in rows[:1]:
        for key in ("as_of", "forecast_time", "observed_at", "created_at"):
            if row.get(key):
                return row[key]
    return None


def build_research_intelligence_package(
    question: str,
    *,
    entity: str | None = None,
    intent: str | None = None,
    horizon: str | None = None,
    fetcher: Callable[[str], dict[str, Any]] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Return a typed, minimal evidence package for one Ask AGI question."""
    selected = detect_intent(question, intent)
    symbol = str(entity or "").strip().upper() or None
    chosen_horizon = _horizon(question, horizon)
    if not selected:
        return {
            "enabled": False,
            "matched": False,
            "supported_intents": list(SUPPORTED_INTENTS),
        }
    if selected not in {"reliability", "pipeline_health"} and not symbol:
        return {
            "enabled": True,
            "matched": True,
            "intent": selected,
            "entity": None,
            "sections": {
                "DATA_QUALITY": {
                    "evidence_complete": False,
                    "missing_components": ["entity"],
                }
            },
            "answer_policy": "insufficient_entity_do_not_infer",
        }

    clock = now or datetime.now(timezone.utc)
    get = fetcher or _get_json
    endpoints: dict[str, str] = {
        "confluence": "/api/market/research-confluence?limit=100",
        "memory": f"/api/market/research-memory/{quote(symbol or '')}?limit=50",
        "forecast": f"/api/market/forecasts/{quote(symbol or '')}?limit=30",
        "ledger": f"/api/market/research-confluence/ledger?{urlencode({'symbol': symbol or '', 'limit': 100})}",
        "validation": f"/api/market/forecasts/validation?{urlencode({'horizon': chosen_horizon, 'limit': 5000})}",
        "rankings": f"/api/market/forecasts/rankings?{urlencode({'horizon': chosen_horizon, 'limit': 500})}",
        "rank_ic": f"/api/market/forecasts/rank-ic?{urlencode({'horizon': chosen_horizon, 'limit': 252})}",
        "health": "/api/market/research-pipeline/health",
    }
    data: dict[str, dict[str, Any]] = {}
    failures: list[dict[str, str]] = []
    called: list[str] = []
    for source in _ROUTES[selected]:
        path = endpoints[source]
        called.append(path)
        try:
            data[source] = get(path) or {}
        except Exception as exc:  # soft-fail: Ask AGI remains available
            failures.append({"source": source, "error": str(exc)[:180]})
            data[source] = {}

    sections: dict[str, Any] = {}
    evidence_rows = _rows(
        data.get("confluence", {}), "items", "opportunities", "rows", "signals"
    )
    if symbol:
        evidence_rows = [
            row
            for row in evidence_rows
            if str(row.get("symbol") or row.get("ticker") or "").upper() == symbol
        ]
    if "confluence" in data:
        sections["CURRENT_EVIDENCE"] = evidence_rows[0] if evidence_rows else {}

    forecast_rows = _rows(data.get("forecast", {}), "forecasts", "rows")
    horizon_rows = [
        row
        for row in forecast_rows
        if str(row.get("horizon") or "").lower() == chosen_horizon
    ]
    latest_forecast = (horizon_rows or forecast_rows)[:1]
    if "forecast" in data:
        sections["FORECAST"] = latest_forecast[0] if latest_forecast else {}
    if selected == "forecast_history":
        sections["FORECAST"] = {"horizon": chosen_horizon, "history": forecast_rows}

    ledger_rows = _rows(data.get("ledger", {}), "rows")
    outcomes = [
        row for row in forecast_rows if row.get("outcome") or row.get("outcomes")
    ]
    if "ledger" in data:
        sections["HISTORICAL_OUTCOME"] = {
            "forecast_outcomes": outcomes,
            "confluence_ledger": ledger_rows,
        }

    validation = data.get("validation", {})
    rank_ic = data.get("rank_ic", {})
    if "validation" in data or "rank_ic" in data:
        sections["EMPIRICAL_VALIDATION"] = {
            "horizon": chosen_horizon,
            **validation,
            "rank_ic": rank_ic,
        }

    memory = data.get("memory", {})
    if "memory" in data:
        sections["CURRENT_EVIDENCE"] = {
            "latest_state": memory.get("latest") or memory.get("current") or {},
            "thesis_changes": memory.get("changes") or [],
            "history": memory.get("history") or memory.get("states") or [],
        }

    rankings = _rows(data.get("rankings", {}), "rows")
    if "rankings" in data:
        match = next(
            (row for row in rankings if str(row.get("symbol") or "").upper() == symbol),
            None,
        )
        sections.setdefault("CURRENT_EVIDENCE", {})["ranking"] = match or {}

    if "health" in data:
        sections["CURRENT_EVIDENCE"] = data["health"]

    evidence_time = _latest_time(
        data.get("confluence", {}) or data.get("memory", {}), evidence_rows
    )
    forecast_time = _latest_time(data.get("forecast", {}), latest_forecast)
    required = {
        "fundamental": ("fundamental_score", "fundamental_quality"),
        "valuation": ("valuation_score", "valuation_attractiveness"),
        "eod_confirmation": ("eod_confirmation",),
        "live_confirmation": ("live_confirmation",),
        "catalyst": ("catalyst_score", "catalyst_relevance"),
    }
    current = (
        sections.get("CURRENT_EVIDENCE")
        if isinstance(sections.get("CURRENT_EVIDENCE"), dict)
        else {}
    )
    scores = current.get("scores") if isinstance(current.get("scores"), dict) else {}
    score_aliases = {
        "fundamental_score": scores.get("fundamental_score"),
        "valuation_score": scores.get("valuation_score"),
        "eod_confirmation": scores.get("eod_confirmation_score"),
        "live_confirmation": scores.get("live_confirmation_score"),
        "catalyst_score": scores.get("catalyst_relevance_score"),
    }
    missing = (
        [
            name
            for name, keys in required.items()
            if not any(
                current.get(key) is not None or score_aliases.get(key) is not None
                for key in keys
            )
        ]
        if selected
        in {"current_research_state", "confluence_explanation", "ranking_explanation"}
        else []
    )
    observations = (
        int(validation.get("observations") or 0) if isinstance(validation, dict) else 0
    )
    calibrated = (
        bool(validation.get("calibrated")) if isinstance(validation, dict) else False
    )
    sections["DATA_QUALITY"] = {
        "forecast_available": bool(latest_forecast),
        "forecast_empirically_calibrated": calibrated,
        "validation_sample_size": observations,
        "evidence_complete": not missing and not failures,
        "missing_components": missing,
        "evidence_age": _age(evidence_time, clock),
        "forecast_age": _age(forecast_time, clock),
        "retrieval_failures": failures,
    }
    sections["PROVENANCE"] = {
        "adapter": "research_intelligence_tool",
        "version": "1.0.0",
        "retrieved_at": clock.isoformat(),
        "sources": called,
        "research_only": True,
        "execution_enabled": False,
    }
    return {
        "enabled": True,
        "matched": True,
        "entity": symbol,
        "intent": selected,
        "horizon": chosen_horizon,
        "sections": sections,
        "answer_policy": "typed_evidence_forecasts_are_not_facts",
        "guidance": {
            "retrieve_only_for_intent": True,
            "state_insufficiency_explicitly": True,
            "include_freshness": True,
            "never_present_forecast_as_observed_fact": True,
        },
    }


def soft_slice_for_ask_agi(
    question: str, payload: dict[str, Any] | None = None
) -> dict[str, Any]:
    payload = payload or {}
    return build_research_intelligence_package(
        question,
        entity=payload.get("ticker") or payload.get("entity"),
        intent=payload.get("intent"),
        horizon=payload.get("horizon"),
    )
