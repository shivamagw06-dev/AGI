"""IPCI production facade."""

from __future__ import annotations

from typing import Any

from institutional_probability_confidence.engine import InstitutionalProbabilityConfidenceEngine
from institutional_probability_confidence.schema import (
    IPCI_VERSION,
    NO_IPCI_JUDGMENT,
    PRIMARY_QUESTION,
    PROGRAMME,
    PROGRAMME_SHORT,
)

_ENGINE = InstitutionalProbabilityConfidenceEngine()


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "programme_short": PROGRAMME_SHORT,
        "version": IPCI_VERSION,
        "primary_question": PRIMARY_QUESTION,
        "does_not": list(NO_IPCI_JUDGMENT),
        "providers_queried_always": [],
        "consumes": "ISI Scenario Reports (+ IFI bundles upstream)",
    }


def dashboard() -> dict[str, Any]:
    return _ENGINE.dashboard()


def probability_company(ticker: str, *, question: str | None = None) -> dict[str, Any]:
    return _ENGINE.probability_company(ticker, question=question)


def probability_sector(sector: str, *, question: str | None = None) -> dict[str, Any]:
    return _ENGINE.probability_sector(sector, question=question)


def confidence_company(ticker: str, *, question: str | None = None) -> dict[str, Any]:
    return _ENGINE.confidence_company(ticker, question=question)


def assessment(
    ticker: str | None = None,
    *,
    scope: str = "company",
    entity: str | None = None,
    question: str | None = None,
    scenario_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _ENGINE.assessment(
        scope=scope,
        entity=entity or ticker,
        question=question,
        scenario_report=scenario_report,
    )
