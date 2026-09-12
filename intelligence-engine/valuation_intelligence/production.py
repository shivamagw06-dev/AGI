"""P2.2 Valuation Intelligence — production façade."""

from __future__ import annotations

from typing import Any

from valuation_intelligence.pack import build_valuation_pack
from valuation_intelligence.schema import (
    ENGINE_CODE,
    ENGINE_NAME,
    FRESHNESS_SLA_DAYS,
    IC10_UNIVERSE,
    MILESTONE,
    PROGRAMME,
    RUNTIME_BUDGET_S,
    VERSION,
    WORKSTREAM_ID,
)
from valuation_intelligence.store import persist_pack

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
        "issues_recommendations": False,
        "modifies_decision_engine": False,
        "sources": [
            "earnings_intelligence",
            "ownership_intelligence",
            "live_market_context",
            "valuation_peer_registry",
            "peer_intelligence",
            "historical_depth",
            "yahoo_chart",
        ],
        "ic10_universe": list(IC10_UNIVERSE),
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
    max_peers: int = 5,
    include_secondary: bool = False,
    persist: bool = True,
    skip_earnings_fetch: bool = False,
    skip_peer_fetch: bool = False,
    injected_quote: dict[str, Any] | None = None,
    injected_earnings: dict[str, Any] | None = None,
    injected_peer_quotes: dict[str, Any] | None = None,
    injected_peer_fundamentals: dict[str, Any] | None = None,
    injected_history: dict[str, list[float]] | None = None,
) -> dict[str, Any]:
    pack = build_valuation_pack(
        ticker,
        force=force,
        max_peers=max_peers,
        include_secondary=include_secondary,
        skip_earnings_fetch=skip_earnings_fetch,
        skip_peer_fetch=skip_peer_fetch,
        injected_quote=injected_quote,
        injected_earnings=injected_earnings,
        injected_peer_quotes=injected_peer_quotes,
        injected_peer_fundamentals=injected_peer_fundamentals,
        injected_history=injected_history,
    )
    store_result = None
    if persist and pack.get("ok") and injected_quote is None and injected_earnings is None:
        try:
            store_result = persist_pack(pack)
        except Exception as exc:  # noqa: BLE001
            store_result = {"error": str(exc)[:160]}

    contract = build_engine_contract(ENGINE_CODE) if build_engine_contract else {"engine": ENGINE_CODE}
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
        "valuation_confidence": pack.get("valuation_confidence"),
        "evidence": pack.get("evidence") or [],
        "confidence": pack.get("confidence"),
        "freshness": pack.get("freshness") or {},
        "lineage": pack.get("lineage") or [],
        "coverage_pct": pack.get("coverage_pct"),
        "valuation_coverage_pct": pack.get("valuation_coverage_pct"),
        "valuation": pack.get("valuation"),
        "current": pack.get("current"),
        "peer_universe": pack.get("peer_universe"),
        "peer_snapshots": pack.get("peer_snapshots"),
        "relative": pack.get("relative"),
        "historical": pack.get("historical"),
        "quality": pack.get("quality"),
        "growth": pack.get("growth"),
        "narrative": pack.get("narrative"),
        "observations": pack.get("observations"),
        "stance": pack.get("stance"),
        "cid_summary": pack.get("cid_summary"),
        "recommendation_policy": pack.get("recommendation_policy"),
        "latency_ms": pack.get("latency_ms"),
        "peer_errors": pack.get("peer_errors"),
        "errors": pack.get("errors"),
        "store": store_result,
        "issues_recommendations": False,
        "modifies_decision_engine": False,
    }


def attach_to_cid(ticker: str, **kwargs: Any) -> dict[str, Any]:
    from valuation_intelligence.enrich import merge_valuation_into_dossier

    pack = analyse(ticker, persist=False, **kwargs)
    dossier = {"ticker": (ticker or "").upper(), "valuation": {}}
    if pack.get("ok"):
        dossier = merge_valuation_into_dossier(dossier, pack)
    return {"pack": pack, "dossier": dossier, "attached": bool(pack.get("ok"))}


def package_for_ask_agi(ticker: str, **kwargs: Any) -> dict[str, Any]:
    pack = analyse(ticker, persist=False, **kwargs)
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "ticker": pack.get("ticker"),
        "ok": pack.get("ok"),
        "valuation": pack.get("valuation"),
        "cid_summary": pack.get("cid_summary"),
        "observations": pack.get("observations"),
        "stance": pack.get("stance"),
        "confidence": pack.get("confidence"),
        "freshness": pack.get("freshness"),
        "coverage_pct": pack.get("coverage_pct"),
        "recommendation_policy": "observations_only_no_buy_sell",
    }


def ic10_smoke(**kwargs: Any) -> dict[str, Any]:
    kwargs.pop("persist", None)
    rows = []
    for t in IC10_UNIVERSE:
        pack = analyse(t, persist=False, **kwargs)
        rows.append(
            {
                "ticker": t,
                "ok": pack.get("ok"),
                "coverage_pct": pack.get("coverage_pct"),
                "pe": (pack.get("current") or {}).get("pe"),
                "peer_median_pe": ((pack.get("valuation") or {}).get("peers") or {}).get("median_pe"),
                "premium_pct": ((pack.get("relative") or {}).get("pe") or {}).get("premium_pct"),
                "stance": pack.get("stance"),
                "peers": (pack.get("peer_universe") or {}).get("primary_peers"),
                "observations": (pack.get("observations") or [])[:3],
            }
        )
    ok_n = sum(1 for r in rows if r.get("ok"))
    return {
        "universe": "IC-10",
        "n": len(rows),
        "ok_n": ok_n,
        "coverage_pct": round(100.0 * ok_n / max(1, len(rows)), 1),
        "rows": rows,
    }
