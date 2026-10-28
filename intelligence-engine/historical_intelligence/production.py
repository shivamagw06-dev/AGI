"""Production surface for the Historical Intelligence Engine."""

from __future__ import annotations

from typing import Any, Optional

from historical_intelligence import comparison, composer, coverage, events, intent, trend, valuation

ENGINE = composer.ENGINE
VERSION = composer.VERSION


def health() -> dict[str, Any]:
    from institutional_warehouse import db

    info = db.info()
    counts = info.get("row_counts") or {}
    history_rows = sum(
        int(counts.get(tab) or 0)
        for tab in ("daily_market_history", "historical_valuation", "financials_annual",
                    "financials_quarterly", "historical_ratios", "corporate_actions")
    )
    return {
        "ok": True,
        "engine": ENGINE,
        "version": VERSION,
        "status": "ok" if history_rows else "empty",
        "reads_from": "institutional_warehouse",
        "historical_rows_available": history_rows,
        "modules": ["trend", "valuation", "events", "comparison", "explainability"],
        "deferred_modules": composer.DEFERRED,
        "metrics": sorted(_metrics()),
    }


def _metrics() -> list[str]:
    from institutional_warehouse import history

    return list(history.SERIES)


def ask(question: str, *, symbol: Optional[str] = None,
        peers: Optional[list[str]] = None) -> dict[str, Any]:
    return composer.answer(question, symbol=symbol, peers=peers)


def plan(question: str, *, symbol: Optional[str] = None) -> dict[str, Any]:
    return composer.plan(question, symbol=symbol)


def detect(question: str) -> dict[str, Any]:
    return {"ok": True, "question": question, **intent.classify(question or "")}


def company(symbol: str, **kwargs: Any) -> dict[str, Any]:
    return composer.company_history(symbol, **kwargs)


def metric_coverage(symbol: str, metric: str) -> dict[str, Any]:
    return coverage.metric_coverage(symbol, metric)


def company_coverage(symbol: str, **kwargs: Any) -> dict[str, Any]:
    return coverage.company_coverage(symbol, **kwargs)


def dataset_coverage(symbol: str) -> dict[str, Any]:
    return coverage.dataset_coverage(symbol)


def trend_analysis(symbol: str, metric: str, **kwargs: Any) -> dict[str, Any]:
    return trend.analyse(symbol, metric, **kwargs)


def valuation_analysis(symbol: str, metric: str = "pe", **kwargs: Any) -> dict[str, Any]:
    return valuation.analyse(symbol, metric, **kwargs)


def valuation_bands(symbol: str, metric: str = "pe") -> dict[str, Any]:
    return valuation.bands(symbol, metric)


def event_timeline(symbol: str, **kwargs: Any) -> dict[str, Any]:
    return events.timeline(symbol, **kwargs)


def compare(symbols: list[str], metric: str = "price") -> dict[str, Any]:
    return comparison.compare(symbols, metric)


def against_sector(symbol: str, metric: str = "pe") -> dict[str, Any]:
    return comparison.against_sector(symbol, metric)
