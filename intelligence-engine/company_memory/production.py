"""Company Memory Knowledge Compiler — production façade."""

from __future__ import annotations

from typing import Any

from company_memory.compile import compile_company_memory
from company_memory.persist import load_memory, persist_memory
from company_memory.schema import (
    ENGINE_CODE,
    ENGINE_NAME,
    EXTERNAL_SOURCES,
    IC10_UNIVERSE,
    MILESTONE,
    PROGRAMME,
    REFERENCE_ONLY,
    SOURCE_INTELLIGENCE_MAP,
    VERSION,
    WORKSTREAM_ID,
)


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "engine": ENGINE_CODE,
        "engine_name": ENGINE_NAME,
        "version": VERSION,
        "workstream_id": WORKSTREAM_ID,
        "milestone": MILESTONE,
        "role": "knowledge_compiler",
        "not_an_llm_trainer": True,
        "pipeline": [
            "ingest",
            "normalise",
            "compare",
            "derive",
            "persist",
            "version",
            "expose_cid",
        ],
        "source_intelligence_map": dict(SOURCE_INTELLIGENCE_MAP),
        "reference_only": list(REFERENCE_ONLY),
        "external_sources_catalog": dict(EXTERNAL_SOURCES),
        "ic10_universe": list(IC10_UNIVERSE),
        "modifies_decision_engine": False,
        "issues_recommendations": False,
    }


def compile(
    ticker: str,
    *,
    force: bool = False,
    persist: bool = True,
    skip_live: bool = False,
    allow_live_prices: bool = True,
    injected: dict[str, Any] | None = None,
    use_cache: bool = False,
) -> dict[str, Any]:
    if use_cache and injected is None and not force:
        cached = load_memory(ticker)
        if isinstance(cached, dict) and cached.get("ok"):
            return {
                **cached,
                "enabled": True,
                "from_cache": True,
                "workstream_id": WORKSTREAM_ID,
            }

    memory = compile_company_memory(
        ticker,
        force=force,
        skip_live=skip_live,
        allow_live_prices=allow_live_prices,
        injected=injected,
    )
    store = None
    if persist and memory.get("ok") and injected is None:
        store = persist_memory(memory)
    return {
        **memory,
        "enabled": True,
        "from_cache": False,
        "workstream_id": WORKSTREAM_ID,
        "store": store,
    }


def analyse(ticker: str, **kwargs: Any) -> dict[str, Any]:
    """Alias for compile — engine-standard name."""
    return compile(ticker, **kwargs)


def attach_to_cid(ticker: str, **kwargs: Any) -> dict[str, Any]:
    from company_memory.enrich import merge_memory_into_dossier

    memory = compile(ticker, persist=kwargs.pop("persist", False), **kwargs)
    dossier = {"ticker": memory.get("entity"), "identity": {"ticker": memory.get("entity")}}
    if memory.get("ok"):
        dossier = merge_memory_into_dossier(dossier, memory)
    return {"memory": memory, "dossier": dossier, "attached": bool(memory.get("ok"))}


def package_for_ask_agi(ticker: str, **kwargs: Any) -> dict[str, Any]:
    memory = compile(ticker, persist=False, **kwargs)
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "ticker": memory.get("entity"),
        "display": memory.get("display"),
        "ok": memory.get("ok"),
        "coverage": memory.get("coverage"),
        "memory": {
            "financial_history": memory.get("financial_history"),
            "ownership_history": memory.get("ownership_history"),
            "valuation_history": memory.get("valuation_history"),
            "price_intelligence": memory.get("price_intelligence"),
            "sector_history": {
                "sector_key": (memory.get("sector_history") or {}).get("sector_key"),
                "kpi_keys": (memory.get("sector_history") or {}).get("kpi_keys"),
            },
            "corporate_history": memory.get("corporate_history"),
            "event_timeline_n": (memory.get("event_timeline") or {}).get("n"),
            "risk_history": memory.get("risk_history"),
        },
        "confidence": memory.get("confidence"),
        "recommendation_policy": "memory_only_no_buy_sell",
    }


def ic10_compile(**kwargs: Any) -> dict[str, Any]:
    rows = []
    for t in IC10_UNIVERSE:
        m = compile(t, persist=kwargs.get("persist", False), **{k: v for k, v in kwargs.items() if k != "persist"})
        rows.append(
            {
                "display": m.get("display"),
                "entity": m.get("entity"),
                "ok": m.get("ok"),
                "coverage_pct": (m.get("coverage") or {}).get("coverage_pct"),
                "confidence": m.get("confidence"),
                "flags": (m.get("coverage") or {}).get("flags"),
                "sector": (m.get("sector_history") or {}).get("sector_key"),
                "return_5y": (m.get("price_intelligence") or {}).get("return_5y_pct"),
                "rev_cagr_5y": ((m.get("financial_history") or {}).get("revenue") or {}).get("cagr_5y"),
                "fii_trend": (((m.get("ownership_history") or {}).get("trends") or {}).get("fii") or {}).get("direction"),
                "events_n": (m.get("event_timeline") or {}).get("n"),
                "latency_ms": m.get("latency_ms"),
            }
        )
    ok_n = sum(1 for r in rows if r.get("ok"))
    return {
        "universe": "IC-10",
        "n": len(rows),
        "ok_n": ok_n,
        "coverage_pct": round(100.0 * ok_n / max(1, len(rows)), 1),
        "rows": rows,
        "version": VERSION,
    }
