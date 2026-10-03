"""Merge CompanyMemory into CID — reusable evidence, not rediscovered facts."""

from __future__ import annotations

from typing import Any


def merge_memory_into_dossier(dossier: dict[str, Any], memory: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(dossier, dict) or not isinstance(memory, dict) or not memory.get("ok"):
        return dossier
    out = dict(dossier)

    out["company_memory"] = {
        "enabled": True,
        "ok": True,
        "engine": memory.get("engine"),
        "version": memory.get("version"),
        "memory_version": memory.get("memory_version"),
        "entity": memory.get("entity"),
        "display": memory.get("display"),
        "coverage": memory.get("coverage"),
        "confidence": memory.get("confidence"),
        "compiled_at": memory.get("compiled_at"),
        "recommendation_policy": memory.get("recommendation_policy"),
        "noop": memory.get("noop"),
        "incremental": memory.get("incremental"),
        "memory_delta": memory.get("memory_delta"),
        "delta_engine": memory.get("delta_engine"),
    }

    # Structured sections for retrieval / Decision Engine consumers
    out["memory"] = {
        "business_model": memory.get("business_model"),
        "competitive_position": memory.get("competitive_position"),
        "financial_history": memory.get("financial_history"),
        "ownership_history": memory.get("ownership_history"),
        "valuation_history": memory.get("valuation_history"),
        "corporate_history": memory.get("corporate_history"),
        "risk_history": memory.get("risk_history"),
        "sector_history": memory.get("sector_history"),
        "event_timeline": {
            "n": (memory.get("event_timeline") or {}).get("n"),
            "events": ((memory.get("event_timeline") or {}).get("events") or [])[-40:],
            "by_year": (memory.get("event_timeline") or {}).get("by_year"),
        },
        "price_intelligence": memory.get("price_intelligence"),
        "latest_evidence": memory.get("latest_evidence"),
        "lineage": memory.get("lineage"),
    }

    # Soft-fill historical helpers used by analysis layers
    pi = memory.get("price_intelligence") or {}
    if pi.get("available"):
        hist_prices = dict(out.get("historical_prices") or {})
        hist_prices.setdefault("return_5y_pct", pi.get("return_5y_pct"))
        hist_prices.setdefault("return_10y_pct", pi.get("return_10y_pct"))
        hist_prices.setdefault("max_drawdown_pct", (pi.get("drawdown") or {}).get("max_drawdown_pct"))
        hist_prices.setdefault("source", "company_memory")
        out["historical_prices"] = hist_prices

    vh = memory.get("valuation_history") or {}
    bands = vh.get("historical_bands") or {}
    if bands.get("pe") and isinstance(out.get("valuation"), dict):
        val = dict(out["valuation"])
        if val.get("historical_pe") is None:
            val["historical_pe"] = (bands["pe"] or {}).get("median")
        if val.get("pe_range") is None:
            val["pe_range"] = bands.get("pe")
        out["valuation"] = val

    oh = memory.get("ownership_history") or {}
    if oh.get("available") and isinstance(out.get("ownership"), dict):
        own = dict(out["ownership"])
        own.setdefault("trends", oh.get("trends"))
        own.setdefault("memory_observations", oh.get("observations"))
        out["ownership"] = own

    evidence = list(out.get("evidence") or [])
    evidence.append(
        {
            "evidence_type": "company_memory",
            "source_id": memory.get("engine"),
            "ticker": memory.get("entity"),
            "payload": {
                "coverage": memory.get("coverage"),
                "financial_cagr_5y": ((memory.get("financial_history") or {}).get("revenue") or {}).get("cagr_5y"),
                "ownership_trends": (oh.get("trends") or {}),
                "event_n": (memory.get("event_timeline") or {}).get("n"),
            },
            "confidence": memory.get("confidence"),
            "as_of": memory.get("compiled_at"),
        }
    )
    out["evidence"] = evidence[-200:]
    return out
