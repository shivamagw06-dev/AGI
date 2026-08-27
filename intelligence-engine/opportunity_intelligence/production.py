"""P4.5 Opportunity Intelligence Engine — production façade."""

from __future__ import annotations

from typing import Any

from opportunity_intelligence.inputs import gather_inputs
from opportunity_intelligence.pack import build_opportunity_pack
from opportunity_intelligence.schema import (
    DIMENSION_WEIGHTS,
    ENGINE_CODE,
    ENGINE_NAME,
    IC10_UNIVERSE,
    MILESTONE,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    RESEARCH_PRIORITIES,
    VERSION,
    WATCHLIST_VIEWS,
    WORKSTREAM_ID,
)
from opportunity_intelligence.watchlist import build_watchlists, default_universe


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "engine": ENGINE_CODE,
        "engine_name": ENGINE_NAME,
        "version": VERSION,
        "workstream_id": WORKSTREAM_ID,
        "milestone": MILESTONE,
        "primary_question": "Where should institutional research effort be focused today, and why?",
        "dimension_weights": dict(DIMENSION_WEIGHTS),
        "research_priorities": list(RESEARCH_PRIORITIES),
        "watchlist_views": list(WATCHLIST_VIEWS),
        "ic10_universe": list(IC10_UNIVERSE),
        "consumes": [
            "company_memory",
            "knowledge_delta_engine",
            "investment_knowledge_graph",
            "institutional_scenario_intelligence",
            "hypothesis_engine",
            "institutional_confidence_calibration",
            "financial/ownership/valuation/corporate/sector intelligence via CompanyMemory",
        ],
        "never_queries_raw_apis": True,
        "issues_recommendations": False,
        "modifies_decision_engine": False,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "decision_engine_mode": "read_only_consumer_via_cid",
    }


def analyse(
    ticker: str,
    *,
    injected_memory: dict[str, Any] | None = None,
    injected_graph: dict[str, Any] | None = None,
    injected_scenarios: dict[str, Any] | None = None,
    injected_hypotheses: dict[str, Any] | None = None,
    injected_confidence: dict[str, Any] | None = None,
    compile_if_missing: bool = True,
    persist_memory: bool = False,
) -> dict[str, Any]:
    inputs = gather_inputs(
        ticker,
        injected_memory=injected_memory,
        injected_graph=injected_graph,
        injected_scenarios=injected_scenarios,
        injected_hypotheses=injected_hypotheses,
        injected_confidence=injected_confidence,
        compile_if_missing=compile_if_missing,
        persist_memory=persist_memory,
    )
    pack = build_opportunity_pack(ticker, inputs=inputs)
    return {
        **pack,
        "programme": PROGRAMME,
        "milestone": MILESTONE,
    }


def top(
    *,
    universe: list[str] | tuple[str, ...] | None = None,
    limit: int = 10,
    **kwargs: Any,
) -> dict[str, Any]:
    packs = _analyse_universe(universe, **kwargs)
    wl = build_watchlists(packs)
    rows = (wl.get("top") or [])[: max(1, min(int(limit), 50))]
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "view": "top_emerging",
        "n": len(rows),
        "rows": rows,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "issues_recommendations": False,
    }


def watchlist(
    *,
    universe: list[str] | tuple[str, ...] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    packs = _analyse_universe(universe, **kwargs)
    wl = build_watchlists(packs)
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        **wl,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "issues_recommendations": False,
    }


def catalysts(
    *,
    universe: list[str] | tuple[str, ...] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    packs = _analyse_universe(universe, **kwargs)
    rows = []
    for p in packs:
        if not p.get("ok"):
            continue
        for c in p.get("catalysts") or []:
            rows.append(
                {
                    "ticker": p.get("display") or p.get("entity"),
                    "entity": p.get("entity"),
                    **c,
                    "opportunity_score": p.get("score"),
                    "research_priority": p.get("research_priority"),
                }
            )
    imp = {"High": 0, "Medium": 1, "Low": 2}
    rows.sort(
        key=lambda r: (
            imp.get(r.get("importance") or "", 9),
            -(as_float_safe(r.get("confidence")) or 0),
            r.get("ticker") or "",
            r.get("name") or "",
        )
    )
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "n": len(rows),
        "catalysts": rows,
        "recommendation_policy": RECOMMENDATION_POLICY,
    }


def research_priority_board(
    *,
    universe: list[str] | tuple[str, ...] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    packs = _analyse_universe(universe, **kwargs)
    wl = build_watchlists(packs)
    by_priority: dict[str, list[dict[str, Any]]] = {p: [] for p in ("Critical", "High", "Medium", "Low", "Monitor")}
    for r in wl.get("research_priority") or []:
        key = r.get("research_priority") or "Monitor"
        by_priority.setdefault(key, []).append(r)
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "by_priority": by_priority,
        "ordered": wl.get("research_priority") or [],
        "recommendation_policy": RECOMMENDATION_POLICY,
        "issues_recommendations": False,
    }


def package_for_ask_agi(ticker: str, **kwargs: Any) -> dict[str, Any]:
    pack = analyse(ticker, persist_memory=False, **kwargs)
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "ticker": pack.get("entity"),
        "ok": pack.get("ok"),
        "score": pack.get("score"),
        "research_priority": pack.get("research_priority"),
        "why_now": pack.get("why_now"),
        "catalysts": (pack.get("catalysts") or [])[:5],
        "blockers": (pack.get("blockers") or [])[:5],
        "confidence": pack.get("confidence"),
        "recommendation_policy": RECOMMENDATION_POLICY,
    }


def ic10_smoke(**kwargs: Any) -> dict[str, Any]:
    kwargs.pop("persist_memory", None)
    packs = []
    rows = []
    for t in IC10_UNIVERSE:
        pack = analyse(t, persist_memory=False, **kwargs)
        packs.append(pack)
        rows.append(
            {
                "ticker": t,
                "entity": pack.get("entity"),
                "ok": pack.get("ok"),
                "score": pack.get("score"),
                "research_priority": pack.get("research_priority"),
                "why_now": (pack.get("why_now") or "")[:180],
                "catalyst_n": len(pack.get("catalysts") or []),
                "blocker_n": len(pack.get("blockers") or []),
                "issues_recommendations": pack.get("issues_recommendations"),
            }
        )
    wl = build_watchlists(packs)
    ok_n = sum(1 for r in rows if r.get("ok"))
    # Determinism check: re-run first ok ticker if possible
    det = None
    for p in packs:
        if p.get("ok"):
            p2 = analyse(p["entity"], persist_memory=False, **kwargs)
            det = {
                "ticker": p["entity"],
                "score_match": p.get("score") == p2.get("score"),
                "priority_match": p.get("research_priority") == p2.get("research_priority"),
                "why_now_match": p.get("why_now") == p2.get("why_now"),
            }
            break
    return {
        "universe": "IC-10",
        "n": len(rows),
        "ok_n": ok_n,
        "coverage_pct": round(100.0 * ok_n / max(1, len(rows)), 1),
        "rows": rows,
        "top": (wl.get("top") or [])[:5],
        "determinism": det,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "issues_recommendations": False,
    }


def _analyse_universe(
    universe: list[str] | tuple[str, ...] | None,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    tickers = list(universe) if universe else list(default_universe())
    return [analyse(t, **kwargs) for t in tickers]


def as_float_safe(v: Any) -> float | None:
    try:
        return float(v) if v is not None else None
    except (TypeError, ValueError):
        return None
