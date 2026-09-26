"""Compose full institutional macro intelligence pack."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from macro_intelligence_engine.confidence import pack_quality
from macro_intelligence_engine.dqiv import validate_pack, validate_section
from macro_intelligence_engine.evidence import load_bundle, load_company_context
from macro_intelligence_engine.models import DEFAULT_COUNTRY, ENGINE_CODE, ENGINE_LABEL, MODULES, VERSION
from macro_intelligence_engine.modules import MODULE_BUILDERS, company_exposure, confidence_module
from macro_intelligence_engine.persist import persist_macro_pack


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_module(
    name: str,
    *,
    country: str = DEFAULT_COUNTRY,
    symbol: Optional[str] = None,
    bundle: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    key = str(name or "").strip().lower().replace("-", "_")
    if key in {"sectorimpact", "sector"}:
        key = "sector_impact"
    if key in {"industryimpact", "industry"}:
        key = "industry_impact"
    if key in {"companyimpact", "company_impact", "exposure"}:
        key = "company_exposure"
    builder = MODULE_BUILDERS.get(key)
    if not builder and key != "company_exposure":
        return {"ok": False, "error": f"unknown_module:{name}", "engine": ENGINE_CODE}
    pack = bundle or load_bundle(country)
    if key == "company_exposure":
        company = load_company_context(symbol) if symbol else {}
        out = company_exposure(pack, company=company)
    else:
        out = builder(pack)  # type: ignore[misc]
    gate = validate_section(out)
    out["dqiv"] = gate
    out["country"] = pack.get("country") or country
    out["module"] = key
    out["engine"] = ENGINE_CODE
    out["version"] = VERSION
    out["generated_at"] = _now()
    if symbol:
        out["symbol"] = str(symbol).upper()
    if not gate["ok"]:
        out["ok"] = False
        out["status"] = "REJECT"
    return out


def build_macro_pack(country: str = DEFAULT_COUNTRY, *, symbol: Optional[str] = None) -> dict[str, Any]:
    ctry = (country or DEFAULT_COUNTRY).strip() or DEFAULT_COUNTRY
    bundle = load_bundle(ctry)
    modules: dict[str, Any] = {}
    confidences: dict[str, dict[str, Any]] = {}

    for name in MODULES:
        if name in {"confidence", "company_exposure"}:
            continue
        sec = build_module(name, country=ctry, bundle=bundle)
        modules[name] = sec
        confidences[name] = sec.get("confidence") or {}

    company = load_company_context(symbol) if symbol else {}
    modules["company_exposure"] = company_exposure(bundle, company=company)
    confidences["company_exposure"] = modules["company_exposure"].get("confidence") or {}

    quality = pack_quality(confidences, bundle.get("inputs_present") or {})
    modules["confidence"] = confidence_module(bundle, quality)

    executive = modules.get("executive") or {}
    scenarios = modules.get("scenarios") or {}
    regime_val = executive.get("regime") or (modules.get("regime") or {}).get("regime")
    cycle_val = executive.get("cycle") or (modules.get("cycle") or {}).get("cycle")
    if not isinstance(regime_val, str):
        from macro_intelligence_engine.indicators import regime_label

        regime_val = regime_label(regime_val) or "Recovery"
    if not isinstance(cycle_val, str):
        cycle_val = str(cycle_val or "Early Cycle")
    pack = {
        "ok": True,
        "country": ctry,
        "symbol": str(symbol).upper() if symbol else None,
        "engine": ENGINE_CODE,
        "label": ENGINE_LABEL,
        "version": VERSION,
        "generated_at": _now(),
        "executive_summary": executive.get("summary"),
        "regime": regime_val,
        "cycle": cycle_val,
        "modules": modules,
        "sections": modules,
        "macro_quality": quality,
        "probabilities": scenarios.get("probabilities"),
        "inputs_present": bundle.get("inputs_present"),
        "observed_series_count": bundle.get("observed_series_count"),
        "recommendation": None,
        "investment_rating": None,
        "target_price": None,
        "vendor_calls": False,
        "reads_from": [
            "institutional_warehouse",
            "continuous_macro_knowledge",
            "historical_macro_intelligence",
            "historical_macro_analogue_intelligence",
            "macroeconomic_forecast_intelligence",
            "macroeconomic_relationship_intelligence",
        ],
    }
    gate = validate_pack(pack)
    pack["dqiv"] = gate
    if not gate["ok"]:
        pack["ok"] = False
        pack["status"] = "REJECT"
    else:
        pack["status"] = "PASS"
        persist_macro_pack(pack)
    return pack
