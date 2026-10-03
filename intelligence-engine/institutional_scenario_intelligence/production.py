"""ISI production facade."""

from __future__ import annotations

from typing import Any

from institutional_scenario_intelligence.engine import InstitutionalScenarioEngine
from institutional_scenario_intelligence.schema import (
    ISI_VERSION,
    NO_ISI_JUDGMENT,
    PRIMARY_QUESTION,
    PROGRAMME,
    PROGRAMME_SHORT,
)

_ENGINE = InstitutionalScenarioEngine()


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "programme_short": PROGRAMME_SHORT,
        "version": ISI_VERSION,
        "primary_question": PRIMARY_QUESTION,
        "does_not": list(NO_ISI_JUDGMENT),
        "providers_queried_always": [],
        "consumes": "IFI Forecast Bundles",
    }


def dashboard() -> dict[str, Any]:
    return _ENGINE.dashboard()


def company(ticker: str, *, question: str | None = None) -> dict[str, Any]:
    return _ENGINE.company_report(ticker, question=question)


def sector(sector_key: str, *, question: str | None = None) -> dict[str, Any]:
    return _ENGINE.sector_report(sector_key, question=question)


def market(*, question: str | None = None) -> dict[str, Any]:
    return _ENGINE.market_report(question=question)


def macro(*, question: str | None = None) -> dict[str, Any]:
    return _ENGINE.macro_report(question=question)


def report(
    *,
    scope: str,
    entity: str | None = None,
    question: str | None = None,
    forecast_bundle: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _ENGINE.report(
        scope=scope,
        entity=entity,
        question=question,
        forecast_bundle=forecast_bundle,
    )
