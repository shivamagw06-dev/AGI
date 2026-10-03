"""P2.1 Financial Statements & Earnings Intelligence — production façade."""

from __future__ import annotations

from typing import Any

from earnings_intelligence.pack import build_financial_pack
from earnings_intelligence.schema import (
    DEFAULT_ANNUAL_XBRL,
    DEFAULT_QUARTERLY_XBRL,
    ENGINE_CODE,
    ENGINE_NAME,
    FRESHNESS_SLA_DAYS,
    MILESTONE,
    PROGRAMME,
    RUNTIME_BUDGET_S,
    VERSION,
    WORKSTREAM_ID,
)
from earnings_intelligence.store import persist_pack

try:
    from phase2_investment_intelligence.contract import build_engine_contract
except Exception:  # pragma: no cover
    build_engine_contract = None  # type: ignore


def health() -> dict[str, Any]:
    contract = build_engine_contract(ENGINE_CODE) if build_engine_contract else {}
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "engine": ENGINE_CODE,
        "engine_name": ENGINE_NAME,
        "version": VERSION,
        "workstream_id": WORKSTREAM_ID,
        "milestone": MILESTONE,
        "contract": contract,
        "runtime_budget_s": RUNTIME_BUDGET_S,
        "freshness_sla_days": FRESHNESS_SLA_DAYS,
        "extends_intelligence": True,
        "replaces_baseline": False,
        "sources": ["nse_integrated", "nse_corporates_financial_results", "nse_indas_xbrl"],
        "implementation_pr_checklist": [
            "What intelligence did we add?",
            "What measurable metric improved?",
            "What metric stayed unchanged?",
            "Did IAT still pass?",
            "Did UNKNOWN drift remain zero?",
        ],
    }


def analyse(
    ticker: str,
    *,
    force: bool = False,
    quarterly_xbrl: int = DEFAULT_QUARTERLY_XBRL,
    annual_xbrl: int = DEFAULT_ANNUAL_XBRL,
    persist: bool = True,
    skip_xbrl: bool = False,
    injected_integrated: list[dict[str, Any]] | None = None,
    injected_quarterly: list[dict[str, Any]] | None = None,
    injected_annual: list[dict[str, Any]] | None = None,
    injected_xbrl_by_url: dict[str, bytes | str] | None = None,
) -> dict[str, Any]:
    pack = build_financial_pack(
        ticker,
        force=force,
        quarterly_xbrl=quarterly_xbrl,
        annual_xbrl=annual_xbrl,
        skip_xbrl=skip_xbrl,
        injected_integrated=injected_integrated,
        injected_quarterly=injected_quarterly,
        injected_annual=injected_annual,
        injected_xbrl_by_url=injected_xbrl_by_url,
    )
    store_result = None
    if persist and pack.get("ok") and injected_quarterly is None and injected_integrated is None:
        try:
            store_result = persist_pack(pack)
        except Exception as exc:  # noqa: BLE001
            store_result = {"error": str(exc)[:160]}

    contract = build_engine_contract(ENGINE_CODE) if build_engine_contract else {"engine": ENGINE_CODE}
    intel = pack.get("intelligence") or {}
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "engine_name": ENGINE_NAME,
        "version": VERSION,
        "workstream_id": WORKSTREAM_ID,
        "milestone": MILESTONE,
        "contract": contract,
        "ticker": pack.get("ticker"),
        "ok": pack.get("ok"),
        "score": pack.get("score"),
        "forecast_confidence": intel.get("forecast_confidence"),
        "evidence": pack.get("evidence") or [],
        "confidence": pack.get("confidence"),
        "freshness": pack.get("freshness") or {},
        "lineage": pack.get("lineage") or [],
        "coverage_pct": pack.get("coverage_pct"),
        "financial_coverage_pct": pack.get("financial_coverage_pct"),
        "latest_quarter": pack.get("latest_quarter"),
        "latest_annual": pack.get("latest_annual"),
        "quarter_history": pack.get("quarter_history"),
        "annual_history": pack.get("annual_history"),
        "historical_quarters_indexed": pack.get("historical_quarters_indexed"),
        "historical_annuals_indexed": pack.get("historical_annuals_indexed"),
        "ttm": pack.get("ttm"),
        "ttm_available": pack.get("ttm_available"),
        "segment_data": pack.get("segment_data"),
        "segments": pack.get("segments"),
        "cash_flow_available": pack.get("cash_flow_available"),
        "balance_sheet_available": pack.get("balance_sheet_available"),
        "income_available": pack.get("income_available"),
        "historical_quarters_parsed": pack.get("historical_quarters_parsed"),
        "historical_annuals_parsed": pack.get("historical_annuals_parsed"),
        "metrics": pack.get("metrics"),
        "intelligence": intel,
        "cid_summary": pack.get("cid_summary"),
        "source": pack.get("source"),
        "store": store_result,
        "degraded": not pack.get("ok"),
        "degraded_reason": (pack.get("errors") or [None])[0] if not pack.get("ok") else None,
        "failure_mode": {
            "strategy": "degrade_gracefully",
            "block_unrelated_engines": False,
            "fabricated": False,
        },
        "fabricated": False,
        "baseline_compatible": True,
        "missing": pack.get("missing"),
        "generated_at": pack.get("generated_at"),
        "latency_ms": pack.get("latency_ms"),
        "errors": pack.get("errors") or [],
    }


def package_for_ask_agi(
    query: str = "",
    *,
    ticker: str | None = None,
    force: bool = False,
    quarterly_xbrl: int = 4,
    annual_xbrl: int = 2,
    **_: Any,
) -> dict[str, Any]:
    t = (ticker or "").upper().strip() or None
    if not t:
        return {
            "enabled": True,
            "engine": ENGINE_CODE,
            "skipped": True,
            "reason": "no_ticker",
            "failure_mode": {
                "strategy": "degrade_gracefully",
                "block_unrelated_engines": False,
                "fabricated": False,
            },
            "baseline_compatible": True,
            "fabricated": False,
        }
    return analyse(
        t,
        force=force,
        quarterly_xbrl=quarterly_xbrl,
        annual_xbrl=annual_xbrl,
        persist=False,
    )


def attach_to_cid(ticker: str, dossier: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
    from earnings_intelligence.enrich import merge_financials_into_dossier

    pack = analyse(ticker, persist=False, **kwargs)
    base = dossier if isinstance(dossier, dict) else {"ticker": ticker.upper()}
    merged = merge_financials_into_dossier(base, pack if pack.get("ok") else {})
    return {"dossier": merged, "pack": pack, "attached": bool(pack.get("ok"))}
