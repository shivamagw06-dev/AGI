"""Persist CompanyMemory as versioned HD object + optional series snapshot."""

from __future__ import annotations

from typing import Any

from company_memory.schema import VERSION


def persist_memory(memory: dict[str, Any]) -> dict[str, Any]:
    entity = str(memory.get("entity") or "").upper()
    if not entity or not memory.get("ok"):
        return {"written": False, "entity": entity, "skipped": True}
    written_object = False
    written_series = False
    try:
        from knowledge_factory.historical_depth import store as hd_store
        from knowledge_factory.historical_depth.schema import pit_record

        hd_store.put_object("company_memory", entity, memory)
        written_object = True
        as_of = (memory.get("compiled_at") or "")[:10] or "latest"
        pit = pit_record(
            entity=entity,
            kind="company_memory_snapshot",
            period=as_of,
            period_end=as_of,
            available_from=as_of,
            payload={
                "version": VERSION,
                "coverage_pct": (memory.get("coverage") or {}).get("coverage_pct"),
                "confidence": memory.get("confidence"),
                "financial_cagr_5y": ((memory.get("financial_history") or {}).get("revenue") or {}).get("cagr_5y"),
                "ownership_fii_trend": (((memory.get("ownership_history") or {}).get("trends") or {}).get("fii") or {}).get(
                    "direction"
                ),
                "pe": (((memory.get("valuation_history") or {}).get("current") or {}).get("pe")),
                "max_drawdown_pct": (((memory.get("price_intelligence") or {}).get("drawdown") or {}).get("max_drawdown_pct")),
            },
            source="company_memory_compiler",
            confidence=float(memory.get("confidence") or 0.8),
        )
        hd_store.put_series("company_memory", entity, [pit])
        written_series = True
    except Exception as exc:  # noqa: BLE001
        return {
            "written": False,
            "entity": entity,
            "error": str(exc)[:160],
            "object": written_object,
            "series": written_series,
        }
    return {
        "written": True,
        "entity": entity,
        "object": written_object,
        "series": written_series,
        "version": VERSION,
    }


def load_memory(ticker: str) -> dict[str, Any] | None:
    try:
        from knowledge_factory.historical_depth import store as hd_store
        from company_memory.resolve import resolve_ticker

        return hd_store.get_object("company_memory", resolve_ticker(ticker))
    except Exception:
        return None
