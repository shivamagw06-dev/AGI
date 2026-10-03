"""API surface for Research Intelligence Engine (Phase 8.4)."""

from __future__ import annotations

from typing import Any, Optional

from research_intelligence_engine.composer import build_dossier, build_section
from research_intelligence_engine.models import ENGINE_CODE, ENGINE_LABEL, SECTIONS, VERSION


def health() -> dict[str, Any]:
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "label": ENGINE_LABEL,
        "version": VERSION,
        "role": "institutional_research_dossier_consumer",
        "vendor_calls": False,
        "ui_calculations": False,
        "recommendation_language": False,
        "sections": list(SECTIONS),
        "reads_from": [
            "institutional_warehouse",
            "uve",
            "hvie",
            "varie",
            "vpae",
            "ownership_intelligence",
        ],
        "endpoints": [
            "/v1/research/health",
            "/v1/research/company/{symbol}",
            "/v1/research/business/{symbol}",
            "/v1/research/financial-quality/{symbol}",
            "/v1/research/growth/{symbol}",
            "/v1/research/profitability/{symbol}",
            "/v1/research/capital-allocation/{symbol}",
            "/v1/research/valuation/{symbol}",
            "/v1/research/ownership/{symbol}",
            "/v1/research/risk/{symbol}",
            "/v1/research/catalysts/{symbol}",
            "/v1/research/monitoring/{symbol}",
            "/v1/research/timeline/{symbol}",
            "/v1/research/confidence/{symbol}",
            "/v1/research/coverage",
            "/v1/research/dashboard",
        ],
    }


def company(symbol: str) -> dict[str, Any]:
    return build_dossier(symbol)


def section(symbol: str, name: str) -> dict[str, Any]:
    return build_section(symbol, name)


def business(symbol: str) -> dict[str, Any]:
    return build_section(symbol, "business")


def financial_quality(symbol: str) -> dict[str, Any]:
    return build_section(symbol, "financial_quality")


def growth(symbol: str) -> dict[str, Any]:
    return build_section(symbol, "growth")


def profitability(symbol: str) -> dict[str, Any]:
    return build_section(symbol, "profitability")


def capital_allocation(symbol: str) -> dict[str, Any]:
    return build_section(symbol, "capital_allocation")


def valuation(symbol: str) -> dict[str, Any]:
    return build_section(symbol, "valuation")


def ownership(symbol: str) -> dict[str, Any]:
    return build_section(symbol, "ownership")


def risk(symbol: str) -> dict[str, Any]:
    return build_section(symbol, "risk")


def catalysts(symbol: str) -> dict[str, Any]:
    return build_section(symbol, "catalysts")


def monitoring(symbol: str) -> dict[str, Any]:
    return build_section(symbol, "monitoring")


def timeline(symbol: str) -> dict[str, Any]:
    return build_section(symbol, "timeline")


def confidence(symbol: str) -> dict[str, Any]:
    dossier = build_dossier(symbol)
    return {
        "ok": dossier.get("ok"),
        "symbol": dossier.get("symbol"),
        "research_quality": dossier.get("research_quality"),
        "section": (dossier.get("sections") or {}).get("confidence"),
        "engine": ENGINE_CODE,
        "version": VERSION,
    }


def coverage(*, limit: int = 200) -> dict[str, Any]:
    """Coverage from persisted dossier summaries when available."""
    rows: list[dict[str, Any]] = []
    try:
        from institutional_warehouse import store

        page = store.fetch("rie_company_dossier", limit=min(max(int(limit), 1), 2000), sort="as_of", order="desc")
        rows = page.get("rows") or []
    except Exception:
        rows = []
    # Deduplicate latest per symbol
    latest: dict[str, dict[str, Any]] = {}
    for r in rows:
        sym = str(r.get("symbol") or "").upper()
        if sym and sym not in latest:
            latest[sym] = r
    dist = {"High": 0, "Medium": 0, "Low": 0}
    for r in latest.values():
        c = str(r.get("research_confidence") or "Low")
        if c in dist:
            dist[c] += 1
    try:
        from institutional_warehouse import store

        universe = int(store.fetch("company_master", limit=1).get("total") or 0)
    except Exception:
        universe = 0
    n = len(latest)
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "universe": universe,
        "companies_analyzed": n,
        "coverage_pct": round(100.0 * n / universe, 1) if universe else 0.0,
        "confidence_distribution": dist,
        "rows": list(latest.values())[: max(1, min(int(limit), 500))],
    }


def dashboard() -> dict[str, Any]:
    cov = coverage(limit=500)
    return {
        "ok": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "label": ENGINE_LABEL,
        "coverage": cov,
        "runtime": {"status": "on_demand", "mode": "incremental_consumer"},
        "notes": [
            "RIE is a consumer of warehouse + UVE/HVIE/VARIE/VPAE.",
            "No vendor calls. No BUY/SELL language.",
        ],
    }


def ask_slice(question: str, *, symbol: Optional[str] = None) -> dict[str, Any]:
    """Soft slice for Ask/KUL — returns dossier facts, never recommendations."""
    ticker = str(symbol or "").strip().upper()
    if not ticker:
        return {"ok": False, "empty": True, "error": "symbol_required"}
    q = (question or "").lower()
    section_hint = None
    mapping = [
        (("risk", "risks"), "risk"),
        (("monitor", "watch"), "monitoring"),
        (("catalyst", "upcoming"), "catalysts"),
        (("ownership", "promoter", "fii", "dii"), "ownership"),
        (("growth", "cagr"), "growth"),
        (("roe", "margin", "profit"), "profitability"),
        (("capital", "buyback", "dividend", "capex"), "capital_allocation"),
        (("valuat", "premium", "rerat", "regime"), "valuation"),
        (("business", "model"), "business"),
        (("quality", "cash flow", "balance sheet"), "financial_quality"),
        (("timeline", "history of events"), "timeline"),
        (("research note", "complete research", "summarize", "explain"), "executive"),
    ]
    for keys, name in mapping:
        if any(k in q for k in keys):
            section_hint = name
            break
    if section_hint and section_hint != "executive":
        sec = build_section(ticker, section_hint)
        return {
            "ok": bool(sec.get("ok")),
            "symbol": ticker,
            "section": section_hint,
            "summary": sec.get("summary"),
            "findings": sec.get("findings"),
            "confidence": sec.get("confidence"),
            "explainability": sec.get("explainability"),
            "evidence": sec.get("evidence"),
            "engine": ENGINE_CODE,
            "version": VERSION,
        }
    dossier = build_dossier(ticker)
    return {
        "ok": bool(dossier.get("ok")),
        "symbol": ticker,
        "section": "company",
        "summary": dossier.get("executive_summary"),
        "research_quality": dossier.get("research_quality"),
        "sections_present": list((dossier.get("sections") or {}).keys()),
        "confidence": (dossier.get("research_quality") or {}).get("research_confidence"),
        "engine": ENGINE_CODE,
        "version": VERSION,
        "recommendation": None,
    }
