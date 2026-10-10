"""API surface for Macro Intelligence Engine (Phase 9.0)."""

from __future__ import annotations

from typing import Any, Optional

from macro_intelligence_engine.composer import build_macro_pack, build_module
from macro_intelligence_engine.models import DEFAULT_COUNTRY, ENGINE_CODE, ENGINE_LABEL, MODULES, VERSION
from macro_intelligence_engine import runtime as mie_runtime
from macro_intelligence_engine.snapshot import read as read_snapshot


def health() -> dict[str, Any]:
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "label": ENGINE_LABEL,
        "version": VERSION,
        "role": "institutional_macro_intelligence",
        "vendor_calls": False,
        "ui_calculations": False,
        "recommendation_language": False,
        "gdp_point_predictions": False,
        "modules": list(MODULES),
        "reads_from": [
            "institutional_warehouse",
            "continuous_macro_knowledge",
            "historical_macro_intelligence",
            "historical_macro_analogue_intelligence",
            "macroeconomic_forecast_intelligence",
            "macroeconomic_relationship_intelligence",
        ],
        "endpoints": [
            "/v1/mie/health",
            "/v1/mie/dashboard",
            "/v1/mie/regime",
            "/v1/mie/economy",
            "/v1/mie/inflation",
            "/v1/mie/rates",
            "/v1/mie/liquidity",
            "/v1/mie/currency",
            "/v1/mie/commodities",
            "/v1/mie/bonds",
            "/v1/mie/fiscal",
            "/v1/mie/external",
            "/v1/mie/sector-impact",
            "/v1/mie/industry-impact",
            "/v1/mie/company-impact/{symbol}",
            "/v1/mie/forecast",
            "/v1/mie/scenarios",
            "/v1/mie/relationships",
            "/v1/mie/risks",
            "/v1/mie/runtime/status",
            "/v1/mie/runtime/board",
        ],
        "note": (
            "Canonical Phase 9.0 prefix is /v1/mie/* . "
            "Legacy sprint surfaces remain under /v1/macro/* (CMKP/HMIP/MRI/HMAI/MFI)."
        ),
    }


def _safe_call(fn, *args, **kwargs) -> dict[str, Any]:
    """Never raise to FastAPI — return structured JSON errors instead of bare 500s."""
    try:
        out = fn(*args, **kwargs)
        return out if isinstance(out, dict) else {"ok": True, "value": out, "engine": ENGINE_CODE}
    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc)[:320],
            "engine": ENGINE_CODE,
            "version": VERSION,
            "recommendation": None,
        }


def dashboard(country: str = DEFAULT_COUNTRY) -> dict[str, Any]:
    pack = _safe_call(build_macro_pack, country)
    if pack.get("ok") is False and pack.get("error") and not pack.get("modules"):
        return pack
    return {
        "ok": pack.get("ok"),
        "country": pack.get("country"),
        "regime": pack.get("regime") if isinstance(pack.get("regime"), str) else None,
        "cycle": pack.get("cycle") if isinstance(pack.get("cycle"), str) else None,
        "executive_summary": pack.get("executive_summary"),
        "macro_quality": pack.get("macro_quality"),
        "probabilities": pack.get("probabilities"),
        "modules": {
            "dashboard": (pack.get("modules") or {}).get("dashboard"),
            "executive": (pack.get("modules") or {}).get("executive"),
            "sector_impact": (pack.get("modules") or {}).get("sector_impact"),
            "risks": (pack.get("modules") or {}).get("risks"),
            "confidence": (pack.get("modules") or {}).get("confidence"),
        },
        "dqiv": pack.get("dqiv"),
        "engine": ENGINE_CODE,
        "version": VERSION,
        "generated_at": pack.get("generated_at"),
        "error": pack.get("error"),
    }


def pack(country: str = DEFAULT_COUNTRY, *, symbol: Optional[str] = None) -> dict[str, Any]:
    return _safe_call(build_macro_pack, country, symbol=symbol)


def snapshot(country: str = "Global") -> dict[str, Any]:
    """Fast, persisted Global Markets payload. Never composes on a web request."""
    return read_snapshot(country)


def module(name: str, *, country: str = DEFAULT_COUNTRY, symbol: Optional[str] = None) -> dict[str, Any]:
    return _safe_call(build_module, name, country=country, symbol=symbol)


def regime(country: str = DEFAULT_COUNTRY) -> dict[str, Any]:
    return build_module("regime", country=country)


def economy(country: str = DEFAULT_COUNTRY) -> dict[str, Any]:
    return build_module("economy", country=country)


def inflation(country: str = DEFAULT_COUNTRY) -> dict[str, Any]:
    return build_module("inflation", country=country)


def rates(country: str = DEFAULT_COUNTRY) -> dict[str, Any]:
    return build_module("rates", country=country)


def liquidity(country: str = DEFAULT_COUNTRY) -> dict[str, Any]:
    return build_module("liquidity", country=country)


def currency(country: str = DEFAULT_COUNTRY) -> dict[str, Any]:
    return build_module("currency", country=country)


def commodities(country: str = DEFAULT_COUNTRY) -> dict[str, Any]:
    return build_module("commodities", country=country)


def bonds(country: str = DEFAULT_COUNTRY) -> dict[str, Any]:
    return build_module("bonds", country=country)


def fiscal(country: str = DEFAULT_COUNTRY) -> dict[str, Any]:
    return build_module("fiscal", country=country)


def external(country: str = DEFAULT_COUNTRY) -> dict[str, Any]:
    return build_module("external", country=country)


def sector_impact(country: str = DEFAULT_COUNTRY) -> dict[str, Any]:
    return build_module("sector_impact", country=country)


def industry_impact(country: str = DEFAULT_COUNTRY) -> dict[str, Any]:
    return build_module("industry_impact", country=country)


def company_impact(symbol: str, *, country: str = DEFAULT_COUNTRY) -> dict[str, Any]:
    return build_module("company_exposure", country=country, symbol=symbol)


def forecast(country: str = DEFAULT_COUNTRY) -> dict[str, Any]:
    return build_module("forecast", country=country)


def scenarios(country: str = DEFAULT_COUNTRY) -> dict[str, Any]:
    return build_module("scenarios", country=country)


def relationships(country: str = DEFAULT_COUNTRY) -> dict[str, Any]:
    return build_module("relationships", country=country)


def risks(country: str = DEFAULT_COUNTRY) -> dict[str, Any]:
    return build_module("risks", country=country)


def ask_slice(question: str, *, symbol: Optional[str] = None, country: str = DEFAULT_COUNTRY) -> dict[str, Any]:
    q = (question or "").lower()
    if any(w in q for w in ("sector", "which sectors", "benefit")):
        name = "sector_impact"
    elif any(w in q for w in ("industry",)):
        name = "industry_impact"
    elif any(w in q for w in ("company", "oil impact", "paint", "sensitivity", "exposure")) and symbol:
        name = "company_exposure"
    elif any(w in q for w in ("bull", "bear", "scenario")):
        name = "scenarios"
    elif any(w in q for w in ("forecast", "outlook")):
        name = "forecast"
    elif any(w in q for w in ("liquidity",)):
        name = "liquidity"
    elif any(w in q for w in ("inflation",)):
        name = "inflation"
    elif any(w in q for w in ("interest rate", "rates", "repo", "banks")):
        name = "rates" if "bank" not in q else "sector_impact"
    elif any(w in q for w in ("cycle", "economic cycle")):
        name = "cycle"
    elif any(w in q for w in ("regime", "macro environment", "what is happening")):
        name = "regime"
    elif any(w in q for w in ("risk",)):
        name = "risks"
    elif any(w in q for w in ("relationship", "why are", "how does")):
        name = "relationships"
    elif any(w in q for w in ("changed", "why has the macro")):
        name = "attribution"
    else:
        # Full executive via pack
        pack_out = build_macro_pack(country, symbol=symbol)
        exec_sec = (pack_out.get("modules") or {}).get("executive") or {}
        return {
            "ok": pack_out.get("ok"),
            "country": country,
            "symbol": symbol,
            "module": "executive",
            "summary": exec_sec.get("summary") or pack_out.get("executive_summary"),
            "findings": exec_sec.get("findings") or [],
            "confidence": exec_sec.get("confidence"),
            "explainability": exec_sec.get("explainability"),
            "regime": pack_out.get("regime"),
            "probabilities": pack_out.get("probabilities"),
            "recommendation": None,
            "engine": ENGINE_CODE,
            "version": VERSION,
        }
    sec = build_module(name, country=country, symbol=symbol)
    return {
        "ok": sec.get("ok"),
        "country": country,
        "symbol": symbol,
        "module": name,
        "summary": sec.get("summary"),
        "findings": sec.get("findings") or [],
        "confidence": sec.get("confidence"),
        "explainability": sec.get("explainability"),
        "recommendation": None,
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def runtime_status() -> dict[str, Any]:
    return mie_runtime.status()


def runtime_board() -> dict[str, Any]:
    return mie_runtime.board()


def runtime_start() -> dict[str, Any]:
    return mie_runtime.start()


def runtime_stop() -> dict[str, Any]:
    return mie_runtime.stop()


def runtime_resume() -> dict[str, Any]:
    return mie_runtime.resume()


def runtime_run(*, mode: str = "daily", batch: int = 1) -> dict[str, Any]:
    return mie_runtime.process_batch(batch=batch, mode=mode)
