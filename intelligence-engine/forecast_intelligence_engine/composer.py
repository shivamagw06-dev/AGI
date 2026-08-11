"""Compose full institutional forecast pack for one company."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from forecast_intelligence_engine.confidence import forecast_quality
from forecast_intelligence_engine.dqiv import validate_pack, validate_section
from forecast_intelligence_engine.evidence import load_bundle
from forecast_intelligence_engine.models import ENGINE_CODE, ENGINE_LABEL, MODULES, VERSION
from forecast_intelligence_engine.modules import MODULE_BUILDERS, confidence_module
from forecast_intelligence_engine.persist import persist_forecast


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_module(symbol: str, name: str, *, bundle: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    ticker = str(symbol or "").strip().upper()
    key = str(name or "").strip().lower().replace("-", "_")
    if key in {"balance_sheet", "balancesheet"}:
        key = "balance_sheet"
    builder = MODULE_BUILDERS.get(key)
    if not builder:
        return {"ok": False, "error": f"unknown_module:{name}", "engine": ENGINE_CODE}
    pack = bundle or load_bundle(ticker)
    out = builder(pack)
    gate = validate_section(out)
    out["dqiv"] = gate
    out["symbol"] = ticker
    out["module"] = key
    out["engine"] = ENGINE_CODE
    out["version"] = VERSION
    out["generated_at"] = _now()
    if not gate["ok"]:
        out["ok"] = False
        out["status"] = "REJECT"
    return out


def build_forecast(symbol: str) -> dict[str, Any]:
    ticker = str(symbol or "").strip().upper()
    if not ticker:
        return {"ok": False, "error": "symbol_required", "engine": ENGINE_CODE}

    bundle = load_bundle(ticker)
    modules: dict[str, Any] = {}
    confidences: dict[str, dict[str, Any]] = {}

    for name in MODULES:
        if name in {"confidence", "history", "accuracy"}:
            continue
        sec = build_module(ticker, name, bundle=bundle)
        modules[name] = sec
        confidences[name] = sec.get("confidence") or {}

    quality = forecast_quality(confidences, bundle.get("inputs_present") or {})
    modules["confidence"] = confidence_module(bundle, quality)
    modules["history"] = build_module(ticker, "history", bundle=bundle)
    modules["accuracy"] = build_module(ticker, "accuracy", bundle=bundle)

    executive = modules.get("executive") or {}
    scenarios = modules.get("scenarios") or {}
    pack = {
        "ok": True,
        "symbol": ticker,
        "company_name": (bundle.get("master") or {}).get("company_name"),
        "sector": (bundle.get("master") or {}).get("sector"),
        "industry": (bundle.get("master") or {}).get("industry"),
        "engine": ENGINE_CODE,
        "label": ENGINE_LABEL,
        "version": VERSION,
        "generated_at": _now(),
        "executive_summary": executive.get("summary"),
        "modules": modules,
        "sections": modules,  # alias for RIE-shaped consumers
        "forecast_quality": quality,
        "probabilities": scenarios.get("probabilities"),
        "inputs_present": bundle.get("inputs_present"),
        "data_readiness": bundle.get("data_readiness"),
        "recommendation": None,
        "investment_rating": None,
        "target_price": None,
        "vendor_calls": False,
        "reads_from": [
            "institutional_warehouse",
            "unified_valuation_engine",
            "historical_valuation_intelligence",
            "valuation_attribution_engine",
            "valuation_policy",
            "research_intelligence_engine",
            "macro_intelligence_engine",
        ],
    }
    gate = validate_pack(pack)
    pack["dqiv"] = gate
    if not gate["ok"]:
        # Soft-pass when only waiting on statements — still return explainable rejection.
        pack["ok"] = False
        pack["status"] = "REJECT"
    else:
        pack["status"] = "PASS"
        persist_forecast(pack)
    return pack
