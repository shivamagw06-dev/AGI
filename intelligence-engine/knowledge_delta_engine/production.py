"""P3.1 Knowledge Delta Engine — production façade."""

from __future__ import annotations

from typing import Any

from knowledge_delta_engine.compile import incremental_compile
from knowledge_delta_engine.explain import explain_observation
from knowledge_delta_engine.ledger import load_ledger
from knowledge_delta_engine.schema import (
    DELTA_TYPES,
    ENGINE_CODE,
    ENGINE_NAME,
    MILESTONE,
    PROGRAMME,
    VERSION,
    WORKSTREAM_ID,
)
from knowledge_delta_engine.versioning import list_versions, load_current, load_version


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "engine": ENGINE_CODE,
        "engine_name": ENGINE_NAME,
        "version": VERSION,
        "workstream_id": WORKSTREAM_ID,
        "milestone": MILESTONE,
        "delta_types": list(DELTA_TYPES),
        "pipeline": [
            "load_prior_memory",
            "compile_candidate",
            "change_detector",
            "memory_delta",
            "version_persist",
            "event_ledger",
            "explainability",
        ],
        "modifies_decision_engine": False,
        "issues_recommendations": False,
        "never_overwrite_silently": True,
    }


def analyse(ticker: str, **kwargs: Any) -> dict[str, Any]:
    return incremental_compile(ticker, **kwargs)


def compile_incremental(ticker: str, **kwargs: Any) -> dict[str, Any]:
    return incremental_compile(ticker, **kwargs)


def versions(ticker: str) -> dict[str, Any]:
    from company_memory.resolve import resolve_ticker

    entity = resolve_ticker(ticker)
    return {
        "entity": entity,
        "current": load_current(entity),
        "versions": list_versions(entity),
    }


def version(ticker: str, ver: int) -> dict[str, Any]:
    from company_memory.resolve import resolve_ticker

    entity = resolve_ticker(ticker)
    row = load_version(entity, ver)
    return {"entity": entity, "version": ver, "found": row is not None, "memory": row}


def ledger(ticker: str) -> dict[str, Any]:
    from company_memory.resolve import resolve_ticker

    return load_ledger(resolve_ticker(ticker))


def explain(ticker: str, topic: str = "management_confidence") -> dict[str, Any]:
    from company_memory.resolve import resolve_ticker

    entity = resolve_ticker(ticker)
    mem = load_current(entity)
    if not mem:
        # Compile once if missing
        mem = incremental_compile(entity, persist=True)
    return explain_observation(mem, topic=topic)


def package_for_ask_agi(ticker: str, **kwargs: Any) -> dict[str, Any]:
    pack = incremental_compile(ticker, persist=kwargs.pop("persist", True), **kwargs)
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "ticker": pack.get("entity"),
        "ok": pack.get("ok"),
        "noop": pack.get("noop"),
        "memory_version": pack.get("memory_version"),
        "memory_delta": pack.get("memory_delta"),
        "delta_engine": pack.get("delta_engine"),
        "coverage": pack.get("coverage"),
        "recommendation_policy": "delta_memory_no_buy_sell",
    }
