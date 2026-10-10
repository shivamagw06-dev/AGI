"""Gold-standard regression suite — deterministic output stability."""

from __future__ import annotations

from typing import Any

from production_hardening.schema import GOLD_REGRESSION_UNIVERSE
from production_hardening import store as hstore
from production_hardening.util import fingerprint, now_iso, soft_call, timed


def capture_company_snapshot(ticker: str, *, company_pack: dict[str, Any] | None = None) -> dict[str, Any]:
    """Capture a stable, recommendation-free snapshot for regression."""
    pack = company_pack
    if not pack:
        pack = soft_call("collect", _collect, ticker)
    oie = pack.get("opportunity") if isinstance(pack.get("opportunity"), dict) else {}
    if not oie.get("ok"):
        oie = soft_call("oie", _oie, ticker, pack.get("memory") if isinstance(pack.get("memory"), dict) else None)

    mem = pack.get("memory") if isinstance(pack.get("memory"), dict) else {}
    graph = pack.get("knowledge_graph") if isinstance(pack.get("knowledge_graph"), dict) else {}
    kd = {}
    if isinstance(oie.get("opportunity"), dict):
        kd = oie["opportunity"].get("knowledge_delta") or {}
    if not kd:
        kd = pack.get("memory_delta") or mem.get("memory_delta") or {}

    # Stable fields only — exclude timestamps / latency
    stable = {
        "entity": oie.get("entity") or pack.get("entity") or ticker,
        "display": oie.get("display") or pack.get("display") or ticker,
        "opportunity_score": oie.get("score"),
        "research_priority": oie.get("research_priority"),
        "why_now": oie.get("why_now"),
        "blocker_codes": sorted(
            [b.get("code") for b in (oie.get("blockers") or []) if b.get("code")]
        ),
        "catalyst_names": sorted(
            [c.get("name") for c in (oie.get("catalysts") or []) if c.get("name")]
        ),
        "dimension_scores": {
            k: (v or {}).get("score")
            for k, v in sorted((oie.get("dimensions") or {}).items())
            if isinstance(v, dict)
        },
        "delta_status": kd.get("status"),
        "graph_peers": sorted(graph.get("peers") or []),
        "graph_themes": sorted(graph.get("themes") or []),
        "sector_key": graph.get("sector_key")
        or (mem.get("sector_history") or {}).get("sector_key"),
        "memory_version": mem.get("memory_version") or (oie.get("freshness") or {}).get("memory_version"),
        "issues_recommendations": False,
    }
    return {
        **stable,
        "fingerprint": fingerprint(stable),
        "ok": bool(oie.get("ok") or pack.get("ok")),
    }


def run_gold_regression(
    *,
    update_baseline: bool = False,
    universe: list[str] | tuple[str, ...] | None = None,
    injected_by_ticker: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    tickers = list(universe) if universe else list(GOLD_REGRESSION_UNIVERSE)
    baseline = hstore.load_gold()
    companies_base = dict(baseline.get("companies") or {})
    rows = []
    mismatches = []

    for t in tickers:
        inj = (injected_by_ticker or {}).get(t)
        snap, ms = timed(capture_company_snapshot, t, company_pack=inj)
        prev = companies_base.get(t) or companies_base.get(snap.get("entity") or "")
        match = None
        if prev and not update_baseline:
            match = prev.get("fingerprint") == snap.get("fingerprint")
            if match is False:
                mismatches.append(
                    {
                        "ticker": t,
                        "previous": prev.get("fingerprint"),
                        "current": snap.get("fingerprint"),
                        "prev_score": prev.get("opportunity_score"),
                        "curr_score": snap.get("opportunity_score"),
                        "prev_priority": prev.get("research_priority"),
                        "curr_priority": snap.get("research_priority"),
                    }
                )
        rows.append({**snap, "latency_ms": ms, "baseline_match": match})
        if update_baseline and snap.get("ok"):
            companies_base[t] = {
                "fingerprint": snap.get("fingerprint"),
                "opportunity_score": snap.get("opportunity_score"),
                "research_priority": snap.get("research_priority"),
                "entity": snap.get("entity"),
                "why_now": snap.get("why_now"),
                "captured_at": now_iso(),
            }

    write = None
    if update_baseline:
        write = hstore.save_gold({"version": 1, "companies": companies_base})

    passed = all(r.get("baseline_match") is not False for r in rows) if companies_base and not update_baseline else True
    # If no baseline yet, treat as informational
    has_baseline = bool(baseline.get("companies"))
    status = "pass" if (passed and has_baseline and not update_baseline) else (
        "baseline_updated" if update_baseline else ("no_baseline" if not has_baseline else "fail")
    )

    result = {
        "as_of": now_iso(),
        "universe": tickers,
        "n": len(rows),
        "ok_n": sum(1 for r in rows if r.get("ok")),
        "status": status,
        "passed": status == "pass" or status == "baseline_updated" or status == "no_baseline",
        "has_baseline": has_baseline,
        "mismatches": mismatches,
        "rows": rows,
        "baseline_write": write,
        "recommendation_policy": "hardening_diagnostics_only_no_buy_sell",
        "issues_recommendations": False,
    }
    hstore.append_history({"kind": "gold_regression", "status": status, "mismatches_n": len(mismatches)})
    return result


def _collect(ticker: str) -> dict[str, Any]:
    from investment_operations.collect import collect_company

    return collect_company(ticker, persist_memory=False, include_soft_reasoning=False)


def _oie(ticker: str, memory: dict[str, Any] | None) -> dict[str, Any]:
    from opportunity_intelligence.production import analyse

    if memory and memory.get("ok"):
        return analyse(ticker, injected_memory=memory, compile_if_missing=False, persist_memory=False)
    return analyse(ticker, persist_memory=False)
